"""
Extractor module: parses Telegram HTML export files incrementally
and produces structured extracted messages.
"""

import os
import re
import html
from typing import Dict, List, Optional, Tuple
import lxml.html


def parse_timestamp(
    title: Optional[str],
    date_text: Optional[str],
    last_date: Optional[str] = None,
    last_tz: str = "UTC+02:00"
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Parses timestamp from title or inner text.
    Returns (iso_formatted_timestamp, date_part, tz_offset).
    Format in title: 'DD.MM.YYYY HH:MM:SS UTC+02:00'
    Normalized output: 'YYYY-MM-DD HH:MM:SS'
    """
    if title:
        # Full format: DD.MM.YYYY HH:MM:SS UTC+XX:XX
        m = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}:\d{2}:\d{2})\s+(UTC[+-]\d{2}:\d{2})$", title.strip())
        if m:
            day, month, year, time_part, tz = m.groups()
            iso_ts = f"{year}-{month}-{day} {time_part}"
            date_str = f"{year}-{month}-{day}"
            return iso_ts, date_str, tz

        # Time-only with timezone in title: HH:MM:SS UTC+XX:XX
        m_time = re.match(r"^(\d{2}:\d{2}(?::\d{2})?)\s+(UTC[+-]\d{2}:\d{2})$", title.strip())
        if m_time and last_date:
            time_part = m_time.group(1)
            if len(time_part) == 5:
                time_part += ":00"
            tz = m_time.group(2)
            iso_ts = f"{last_date} {time_part}"
            return iso_ts, last_date, tz

    # Fallback to date_text (e.g. '18:18') if title is missing
    if date_text and last_date:
        m_fallback = re.search(r"(\d{2}:\d{2}(?::\d{2})?)", date_text.strip())
        if m_fallback:
            time_part = m_fallback.group(1)
            if len(time_part) == 5:
                time_part += ":00"
            iso_ts = f"{last_date} {time_part}"
            return iso_ts, last_date, last_tz

    return None, last_date, last_tz


def clean_text(text_element: Optional[lxml.html.HtmlElement]) -> str:
    """
    Extracts text from div.text:
    - Replaces <br> with newline
    - Strips reply_to elements if somehow nested
    - Normalizes unicode whitespace and decodes HTML entities
    """
    if text_element is None:
        return ""

    # Remove any nested reply_to if present
    for reply in text_element.xpath(".//div[contains(@class, 'reply_to')]"):
        reply.drop_tree()

    # Preserve line breaks for <br>
    for br in text_element.xpath(".//br"):
        br.tail = "\n" + (br.tail or "")

    raw = text_element.text_content()
    # Normalize non-breaking spaces and zero-width spaces
    raw = raw.replace("\xa0", " ").replace("\u200b", "").replace("\r\n", "\n").replace("\r", "\n")
    # Clean trailing whitespace per line
    lines = [line.strip() for line in raw.split("\n")]
    cleaned = "\n".join(lines).strip()
    return html.unescape(cleaned)


def get_html_files(export_dir: str) -> List[str]:
    """
    Discovers all HTML pages in export_dir and sorts them numerically:
    messages.html (1), messages2.html, messages3.html, ..., messages653.html
    """
    if not os.path.exists(export_dir):
        return []

    files = [f for f in os.listdir(export_dir) if f.endswith(".html")]

    def sort_key(f: str) -> int:
        m = re.match(r"^messages(\d+)?\.html$", f)
        if not m:
            return 9999999
        return int(m.group(1)) if m.group(1) else 1

    files.sort(key=sort_key)
    return files


def extract_messages_from_file(
    file_path: str,
    last_date: Optional[str] = None,
    last_tz: str = "UTC+02:00"
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Optional[str], str]:
    """
    Parses a single Telegram HTML file using fast direct DOM traversal.
    Returns (records, malformed_records, current_date, current_tz).
    """
    records = []
    malformed = []
    source_file = os.path.basename(file_path)

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        root = lxml.html.fromstring(content)
    except Exception as e:
        malformed.append({
            "message_id": "FILE_ERROR",
            "source_file": source_file,
            "reason": f"Failed to parse HTML file: {str(e)}",
            "raw_text": "",
        })
        return records, malformed, last_date, last_tz

    # Find message containers using fast tag iteration
    for m in root.iter("div"):
        m_cls = m.get("class")
        if not m_cls or "message" not in m_cls:
            continue

        classes = m_cls.split()
        if "service" in classes and "default" not in classes:
            continue
        if "default" not in classes:
            continue

        mid = m.get("id", "")

        date_el = None
        from_el = None
        text_el = None

        # Direct child traversal inside message
        for child in m.iter("div"):
            c_cls = child.get("class")
            if not c_cls:
                continue
            if "date" in c_cls and date_el is None:
                date_el = child
            elif "from_name" in c_cls and from_el is None:
                from_el = child
            elif "text" in c_cls and text_el is None:
                text_el = child

        title = date_el.get("title") if date_el is not None else None
        date_text = date_el.text_content().strip() if date_el is not None else None
        iso_ts, last_date, last_tz = parse_timestamp(title, date_text, last_date, last_tz)

        sender = from_el.text_content().strip() if from_el is not None else ""
        raw_text = clean_text(text_el) if text_el is not None else ""

        if not iso_ts or not raw_text:
            malformed.append({
                "message_id": mid,
                "source_file": source_file,
                "reason": "Missing timestamp" if not iso_ts else "Missing text",
                "raw_text": raw_text,
            })
            if not iso_ts:
                continue

        records.append({
            "message_id": mid,
            "timestamp": iso_ts,
            "raw_text": raw_text,
            "source_file": source_file,
            "sender": sender,
        })

    return records, malformed, last_date, last_tz

