"""
Pairer module: pairs air-raid alert start and end events into intervals (alerts.csv)
and records all pairing anomalies and boundary issues in pairing_issues.csv.
"""

from datetime import datetime
from typing import Dict, List, Tuple, Any
from collections import defaultdict


def parse_dt(ts_str: str) -> datetime:
    """Parses ISO timestamp string YYYY-MM-DD HH:MM:SS."""
    return datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S")


def pair_events(
    events: List[Dict[str, Any]],
    max_duration_hours: float = 24.0
) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
    """
    Pairs chronological events independently by region.
    Returns (intervals, issues).

    intervals: list of dicts with keys: ['region', 'started_at', 'ended_at']
    issues: list of dicts with keys: ['issue_type', 'region', 'timestamp', 'message_id', 'details']
    """
    # Sort all events chronologically
    sorted_events = sorted(events, key=lambda x: x["time"])

    # Group by region
    events_by_region = defaultdict(list)
    for ev in sorted_events:
        events_by_region[ev["region"]].append(ev)

    intervals = []
    issues = []

    for region, reg_events in events_by_region.items():
        open_alert = None

        for ev in reg_events:
            status = ev["status"]
            ts_str = ev["time"]
            mid = ev.get("message_id", "")

            if status == "alert":
                if open_alert is not None:
                    # Repeated alert while already open
                    issues.append({
                        "issue_type": "repeated_alert",
                        "region": region,
                        "timestamp": ts_str,
                        "message_id": mid,
                        "details": f"Alert received while interval already open from {open_alert['time']} (mid: {open_alert.get('message_id', '')})"
                    })
                    # Do not replace open_alert, keep the original start
                else:
                    open_alert = ev

            elif status == "end":
                if open_alert is None:
                    # Orphan end without preceding alert
                    issues.append({
                        "issue_type": "orphan_end",
                        "region": region,
                        "timestamp": ts_str,
                        "message_id": mid,
                        "details": "End event received with no active open alert"
                    })
                else:
                    start_dt = parse_dt(open_alert["time"])
                    end_dt = parse_dt(ts_str)

                    if end_dt < start_dt:
                        issues.append({
                            "issue_type": "negative_duration",
                            "region": region,
                            "timestamp": ts_str,
                            "message_id": mid,
                            "details": f"End time {ts_str} earlier than start time {open_alert['time']}"
                        })
                    else:
                        duration_hours = (end_dt - start_dt).total_seconds() / 3600.0
                        if duration_hours > max_duration_hours:
                            issues.append({
                                "issue_type": "excessive_duration",
                                "region": region,
                                "timestamp": ts_str,
                                "message_id": mid,
                                "details": f"Interval duration {duration_hours:.1f}h exceeds {max_duration_hours}h threshold (start: {open_alert['time']})"
                            })

                        intervals.append({
                            "region": region,
                            "started_at": open_alert["time"],
                            "ended_at": ts_str,
                        })

                    open_alert = None

        # At export boundary, check for unresolved open alert
        if open_alert is not None:
            issues.append({
                "issue_type": "unresolved_start",
                "region": region,
                "timestamp": open_alert["time"],
                "message_id": open_alert.get("message_id", ""),
                "details": f"Alert started at {open_alert['time']} has no matching end event by end of export"
            })

    # Sort final intervals chronologically by started_at, then region
    intervals.sort(key=lambda x: (x["started_at"], x["region"]))
    return intervals, issues

