"""
Ukrainian Air Alerts Pipeline Package.
"""

from pipeline.constants import CANONICAL_REGIONS, OBLAST_ALIASES
from pipeline.extractor import extract_messages_from_file, get_html_files, parse_timestamp, clean_text
from pipeline.classifier import classify_message, detect_status, detect_geography
from pipeline.pairer import pair_events

__all__ = [
    "CANONICAL_REGIONS",
    "OBLAST_ALIASES",
    "extract_messages_from_file",
    "get_html_files",
    "parse_timestamp",
    "clean_text",
    "classify_message",
    "detect_status",
    "detect_geography",
    "pair_events",
]

