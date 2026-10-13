"""
Classifier module: classifies Telegram messages into air-raid alert starts
and ends, assigning canonical geographic regions according to strict project rules.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from pipeline.constants import (
    CANONICAL_REGIONS,
    OBLAST_ALIASES,
    KYIV_CITY_PATTERNS,
    OUT_OF_SCOPE_LOCATIONS,
    KNOWN_CITIES,
)


def detect_status(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detects status: 'alert', 'end', 'unrelated', or None (ambiguous).
    Returns (status, reason_if_any).
    """
    lower = text.lower()

    # 1. Check for false alarm retraction / apology / mistake
    if re.search(r"(?:помилка\s+щодо\s+тривоги|приносимо\s+(?:свої\s+)?вибачення|тривоги\s+в\s+області\s+немає)", lower):
        return None, "false_alarm_apology_or_cancellation"

    # 2. Check for unrelated informational / curfew / app ads / media explosion reports
    if re.search(r"комендантськ[аоіиуе]\s+годин[аиіу]", lower):
        return "unrelated", "curfew_announcement"

    if re.search(r"(?:застосунок|додаток|канал створено|мапа тривог станом на|планові вибухові роботи)", lower):
        return "unrelated", "informational_or_admin"

    if re.search(r"(?:змі повідомляють про вибухи|чутно вибухи|повідомляють про вибухи|роботу дрг)", lower):
        # Explosions report without alert announcement
        if not re.search(r"(?:повітряна\s+тривога|відбій\s+тривоги|оголошено\s+тривогу|всі\s+в\s+укриття)", lower):
            return "unrelated", "explosion_or_media_report"

    # 3. Check for ongoing reminder (NOT a new alert start!)
    if re.search(r"(?:тривога\s+(?:ще\s+)?триває|небезпека\s+триває|загроза\s+обстрілу\s+триває|все ще актуально)", lower):
        return "unrelated", "ongoing_alert_reminder"

    # 4. Check for tactical threats without air alert (artillery, drone, KAB shelling)
    if re.search(r"загроз[аи]\s+(?:артилерійського\s+обстрілу|артобстрілу|застосування\s+(?:каб|бпла|ракет)|обстрілу)", lower):
        if not re.search(r"(?:повітрян[ау]\s+тривог[ау]|оголошено\s+повітряну\s+тривогу)", lower):
            return "unrelated", "tactical_threat_not_air_alert"

    if re.search(r"відбій\s+загрози\s+(?:артобстрілу|обстрілу|застосування\s+бпла)", lower):
        if not re.search(r"відбій\s+(?:повітряної\s+)?тривоги", lower):
            return "unrelated", "tactical_threat_end"

    # 5. Check for ALL-CLEAR / END
    # Variants: Відбій тривоги, Відбій повітряної тривоги, Відбій тревоги, Відбій червоної тривоги, Відбій (in alert context)
    is_end = False
    if re.search(r"відбій\s+(?:повітряної\s+)?тр[еи]воги", lower):
        is_end = True
    elif re.search(r"відбій\s+(?:червоної|жовтої)\s+тривоги", lower):
        is_end = True
    elif re.search(r"тривога\s+відбій", lower):
        is_end = True
    elif re.search(r"(?:^|[^\w])відбій(?:[^\w]|$)", lower) and ("🟢" in text or "київ" in lower or "києв" in lower or "обл" in lower or "тривог" in lower or any(c in lower for c in KNOWN_CITIES)):
        is_end = True

    if is_end:
        return "end", None

    # 6. Check for ALERT START
    is_alert = False
    if re.search(r"повітрян[ауоі]\s+тривог[ауоі]", lower):
        is_alert = True
    elif re.search(r"оголошен[оа]\s+повітрян[ауоі]\s+тривог[ауоі]", lower):
        is_alert = True
    elif re.search(r"тр[еи]вог[ау]\s*[-–—]\s*усі\s+в\s+укриття", lower):
        is_alert = True
    elif re.search(r"(?:червоний|жовтий)\s+рівень\s+тривоги", lower) and ("прямуйте" in lower or "укриття" in lower or "🚨" in text or "🟡" in text or "🔴" in text):
        is_alert = True
    elif re.search(r"🚨.*тр[еи]вог[ау]", lower):
        is_alert = True
    elif re.search(r"(?:^|[^\w])тр[еи]вог[ау]!?(?:[^\w]|$)", lower) and ("укриття" in lower or "авіа" in lower or "київ" in lower or "києв" in lower or "обл" in lower or any(c in lower for c in KNOWN_CITIES)):
        is_alert = True

    if is_alert:
        return "alert", None

    # Unrecognized / Ambiguous
    if "тривог" in lower or "загроз" in lower:
        return None, "ambiguous_alert_status"

    return "unrelated", "no_alert_keywords"


def detect_geography(text: str) -> List[Dict[str, Any]]:
    """
    Detects geographic entities in text.
    Returns list of findings:
    [{
        'region': canonical_region_or_raw,
        'is_target_entity': bool,
        'granularity': 'oblast' | 'kyiv_city' | 'city' | 'district' | 'out_of_scope' | 'unknown',
        'raw_match': str
    }]
    """
    lower = text.lower()
    results = []

    # 1. Check for districts and communities (район, громада)
    # e.g., "Ніжинський район (Чернігівська обл.)" or "Шосткинський район"
    district_matches = re.findall(
        r"([\w'-]+ський\s+район|[\w'-]+цький\s+район|[\w'-]+зький\s+район|[\w'-]+ська\s+громада|[\w'-]+ської\s+громади)",
        lower
    )
    if district_matches:
        for d in set(district_matches):
            results.append({
                "region": d,
                "is_target_entity": False,
                "granularity": "district",
                "raw_match": d
            })

    # 2. Check Kyiv City vs Kyivska Oblast
    # Kyivska oblast patterns
    is_kyivska_oblast = False
    for p in OBLAST_ALIASES["Kyivska oblast"]:
        if re.search(p, lower):
            is_kyivska_oblast = True
            break

    # Kyiv city patterns
    is_kyiv_city = False
    if not re.search(r"київськ(?:ий|ого)\s+(?:район|район[уі])", lower):
        for p in KYIV_CITY_PATTERNS:
            if re.search(p, lower):
                is_kyiv_city = True
                break

    if is_kyivska_oblast and not is_kyiv_city:
        results.append({
            "region": "Kyivska oblast",
            "is_target_entity": True,
            "granularity": "oblast",
            "raw_match": "Київська область"
        })
    elif is_kyiv_city and not is_kyivska_oblast:
        results.append({
            "region": "Kyiv",
            "is_target_entity": True,
            "granularity": "kyiv_city",
            "raw_match": "Київ"
        })
    elif is_kyiv_city and is_kyivska_oblast:
        results.append({
            "region": "Kyiv",
            "is_target_entity": True,
            "granularity": "kyiv_city",
            "raw_match": "Київ"
        })
        results.append({
            "region": "Kyivska oblast",
            "is_target_entity": True,
            "granularity": "oblast",
            "raw_match": "Київська область"
        })

    # 3. Check the remaining 23 Oblasts
    for canonical_name, patterns in OBLAST_ALIASES.items():
        if canonical_name == "Kyivska oblast":
            continue
        for p in patterns:
            m = re.search(p, lower)
            if m:
                results.append({
                    "region": canonical_name,
                    "is_target_entity": True,
                    "granularity": "oblast",
                    "raw_match": m.group(0)
                })
                break

    # 4. Check Known Cities (non-Kyiv)
    found_cities = []
    for city in KNOWN_CITIES:
        # Check whole word match
        city_regex = r"(?:^|[^\w])" + re.escape(city) + r"(?:[^\w]|$)"
        if re.search(city_regex, lower):
            # If the city name appears inside the oblast name (e.g. 'житомирська'), don't duplicate
            if re.search(re.escape(city) + r"ськ", lower):
                continue
            found_cities.append(city)

    for c in found_cities:
        results.append({
            "region": c,
            "is_target_entity": False,
            "granularity": "city",
            "raw_match": c
        })

    # 5. Check for out of scope geography (Crimea, Sevastopol)
    # Only if not just a flight trajectory mention like "з напрямку Севастополя"
    for pattern in OUT_OF_SCOPE_LOCATIONS:
        m = re.search(pattern, lower)
        if m:
            if not re.search(r"(?:з|зі|напрямк[уом])\s+севастопол", lower):
                results.append({
                    "region": m.group(0),
                    "is_target_entity": False,
                    "granularity": "out_of_scope",
                    "raw_match": m.group(0)
                })

    return results


def classify_message(record: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Classifies a raw message record into one or more structured event records.
    Returns a list of dicts for draft_alerts.csv:
    [{
        'region': canonical_region_or_other,
        'status': 'alert' | 'end' | 'unrelated' | 'ambiguous',
        'time': record['timestamp'],
        'message_id': record['message_id'],
        'source_file': record['source_file'],
        'raw_text': record['raw_text'],
        'classification_method': 'deterministic_rules',
        'review_required': bool,
        'review_reason': str
    }]
    """
    text = record["raw_text"]
    timestamp = record["timestamp"]
    mid = record["message_id"]
    source_file = record["source_file"]

    status, status_reason = detect_status(text)
    geo_findings = detect_geography(text)

    # If status is unrelated
    if status == "unrelated":
        return [{
            "region": "None",
            "status": "unrelated",
            "time": timestamp,
            "message_id": mid,
            "source_file": source_file,
            "raw_text": text,
            "classification_method": "deterministic_rules",
            "review_required": False,
            "review_reason": status_reason or "unrelated_message"
        }]

    # If status is ambiguous / None
    if status is None:
        return [{
            "region": "None",
            "status": "ambiguous",
            "time": timestamp,
            "message_id": mid,
            "source_file": source_file,
            "raw_text": text,
            "classification_method": "deterministic_rules",
            "review_required": True,
            "review_reason": status_reason or "ambiguous_alert_status"
        }]

    # Here status is either 'alert' or 'end'. Now analyze geography:
    # Check for out-of-scope locations (Crimea, Sevastopol)
    out_of_scope = [g for g in geo_findings if g["granularity"] == "out_of_scope"]
    if out_of_scope:
        return [{
            "region": out_of_scope[0]["raw_match"],
            "status": status,
            "time": timestamp,
            "message_id": mid,
            "source_file": source_file,
            "raw_text": text,
            "classification_method": "deterministic_rules",
            "review_required": True,
            "review_reason": f"out_of_scope_geography: {out_of_scope[0]['raw_match']}"
        }]

    # Check for district-level events
    districts = [g for g in geo_findings if g["granularity"] == "district"]
    if districts:
        return [{
            "region": districts[0]["raw_match"],
            "status": status,
            "time": timestamp,
            "message_id": mid,
            "source_file": source_file,
            "raw_text": text,
            "classification_method": "deterministic_rules",
            "review_required": True,
            "review_reason": f"district_level_event: {districts[0]['raw_match']}"
        }]

    # Check for city-level events
    cities = [g for g in geo_findings if g["granularity"] == "city"]
    if cities:
        return [{
            "region": cities[0]["raw_match"],
            "status": status,
            "time": timestamp,
            "message_id": mid,
            "source_file": source_file,
            "raw_text": text,
            "classification_method": "deterministic_rules",
            "review_required": True,
            "review_reason": f"city_level_event: {cities[0]['raw_match']}"
        }]

    # Check for target entities (oblasts or Kyiv city)
    target_regions = [g for g in geo_findings if g["is_target_entity"] and g["region"] in CANONICAL_REGIONS]

    if not target_regions:
        return [{
            "region": "Unknown",
            "status": status,
            "time": timestamp,
            "message_id": mid,
            "source_file": source_file,
            "raw_text": text,
            "classification_method": "deterministic_rules",
            "review_required": True,
            "review_reason": "unresolved_geography"
        }]

    unique_regions = []
    seen = set()
    for g in target_regions:
        r = g["region"]
        if r not in seen:
            seen.add(r)
            unique_regions.append(r)

    events = []
    for reg in unique_regions:
        events.append({
            "region": reg,
            "status": status,
            "time": timestamp,
            "message_id": mid,
            "source_file": source_file,
            "raw_text": text,
            "classification_method": "deterministic_rules",
            "review_required": False,
            "review_reason": ""
        })

    return events

