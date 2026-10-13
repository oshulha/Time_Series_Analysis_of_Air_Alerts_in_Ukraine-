"""
Automated unit tests covering all 18 requirements from Section 8:
1. Standard alert followed by end for one region.
2. Multiple alert intervals in a day.
3. An interval crossing midnight.
4. Kyiv city versus Kyiv oblast.
5. Ukrainian grammatical variants and misspellings.
6. City-only location messages.
7. Multiple regions in one message.
8. 'Загроза' in a non-alert context.
9. End without a start.
10. Repeated alert before an end.
11. Missing end at the export boundary.
12. Duplicate Telegram messages.
13. Missing or malformed timestamps.
14. Unknown or out-of-scope geographic entities.
15. Unrelated messages.
16. Joined Telegram message containers without their own sender block.
17. Missing div.text or missing timestamp title attributes.
18. A message with a reply preview and a separate actual message body.
"""

import pytest
import lxml.html
from pipeline.constants import CANONICAL_REGIONS
from pipeline.extractor import (
    parse_timestamp,
    clean_text,
    extract_messages_from_file,
)
from pipeline.classifier import (
    classify_message,
    detect_status,
    detect_geography,
)
from pipeline.pairer import pair_events


# 1. Standard alert followed by end for one region
def test_1_standard_alert_and_end():
    events = [
        {"region": "Poltavska oblast", "status": "alert", "time": "2023-05-10 10:00:00", "message_id": "m1"},
        {"region": "Poltavska oblast", "status": "end", "time": "2023-05-10 11:30:00", "message_id": "m2"},
    ]
    intervals, issues = pair_events(events)
    assert len(intervals) == 1
    assert len(issues) == 0
    assert intervals[0] == {
        "region": "Poltavska oblast",
        "started_at": "2023-05-10 10:00:00",
        "ended_at": "2023-05-10 11:30:00",
    }


# 2. Multiple alert intervals in a day
def test_2_multiple_intervals_in_day():
    events = [
        {"region": "Vinnytska oblast", "status": "alert", "time": "2023-06-01 08:00:00", "message_id": "m1"},
        {"region": "Vinnytska oblast", "status": "end", "time": "2023-06-01 09:15:00", "message_id": "m2"},
        {"region": "Vinnytska oblast", "status": "alert", "time": "2023-06-01 14:00:00", "message_id": "m3"},
        {"region": "Vinnytska oblast", "status": "end", "time": "2023-06-01 15:45:00", "message_id": "m4"},
    ]
    intervals, issues = pair_events(events)
    assert len(intervals) == 2
    assert len(issues) == 0
    assert intervals[0]["started_at"] == "2023-06-01 08:00:00"
    assert intervals[0]["ended_at"] == "2023-06-01 09:15:00"
    assert intervals[1]["started_at"] == "2023-06-01 14:00:00"
    assert intervals[1]["ended_at"] == "2023-06-01 15:45:00"


# 3. An interval crossing midnight
def test_3_interval_crossing_midnight():
    events = [
        {"region": "Cherkaska oblast", "status": "alert", "time": "2023-07-20 23:15:00", "message_id": "m1"},
        {"region": "Cherkaska oblast", "status": "end", "time": "2023-07-21 02:40:00", "message_id": "m2"},
    ]
    intervals, issues = pair_events(events)
    assert len(intervals) == 1
    assert len(issues) == 0
    assert intervals[0]["started_at"] == "2023-07-20 23:15:00"
    assert intervals[0]["ended_at"] == "2023-07-21 02:40:00"


# 4. Kyiv city versus Kyiv oblast
def test_4_kyiv_city_vs_kyiv_oblast():
    # Kyiv city start
    m_kyiv_city = {
        "message_id": "m1", "timestamp": "2023-08-01 10:00:00",
        "source_file": "test.html", "raw_text": "🚨 Київ. Повітряна тривога! Прямуйте в укриття!"
    }
    res_city = classify_message(m_kyiv_city)
    assert len(res_city) == 1
    assert res_city[0]["region"] == "Kyiv"
    assert res_city[0]["status"] == "alert"
    assert not res_city[0]["review_required"]

    # Kyivska oblast start
    m_kyiv_obl = {
        "message_id": "m2", "timestamp": "2023-08-01 10:05:00",
        "source_file": "test.html", "raw_text": "🚨 Київська область. Повітряна тривога! Прямуйте в укриття!"
    }
    res_obl = classify_message(m_kyiv_obl)
    assert len(res_obl) == 1
    assert res_obl[0]["region"] == "Kyivska oblast"
    assert res_obl[0]["status"] == "alert"
    assert not res_obl[0]["review_required"]

    # Kyivshchyna alias -> Kyivska oblast
    m_kyivshchyna = {
        "message_id": "m3", "timestamp": "2023-08-01 10:10:00",
        "source_file": "test.html", "raw_text": "🟢 Київщина. Відбій тривоги!"
    }
    res_kyivshchyna = classify_message(m_kyivshchyna)
    assert len(res_kyivshchyna) == 1
    assert res_kyivshchyna[0]["region"] == "Kyivska oblast"
    assert res_kyivshchyna[0]["status"] == "end"

    # Standalone Kyiv all-clear
    m_kyiv_clear = {
        "message_id": "m4", "timestamp": "2023-08-01 11:00:00",
        "source_file": "test.html", "raw_text": "Київ, відбій"
    }
    res_kyiv_clear = classify_message(m_kyiv_clear)
    assert len(res_kyiv_clear) == 1
    assert res_kyiv_clear[0]["region"] == "Kyiv"
    assert res_kyiv_clear[0]["status"] == "end"


# 5. Ukrainian grammatical variants and misspellings
def test_5_grammatical_variants_and_misspellings():
    # Locative grammatical forms and nicknames
    cases = [
        ("У Вінницькій області оголошено повітряну тривогу", "Vinnytska oblast", "alert"),
        ("На Волині повітряна тривога", "Volynska oblast", "alert"),
        ("Закарпаття, відбій тривоги", "Zakarpatska oblast", "end"),
        ("Прикарпаття. Повітряна тривога!", "Ivano-Frankivska oblast", "alert"),
        # Historical typo "відбій тревоги"
        ("Харківська обл. Відбій тревоги", "Kharkivska oblast", "end"),
        # "Ровенська область"
        ("Ровенська область. Повітряна тривога!", "Rivnenska oblast", "alert"),
    ]
    for text, expected_region, expected_status in cases:
        rec = {
            "message_id": "test_id", "timestamp": "2023-09-01 12:00:00",
            "source_file": "test.html", "raw_text": text
        }
        res = classify_message(rec)
        assert len(res) == 1, f"Failed for text: {text}"
        assert res[0]["region"] == expected_region, f"Failed region for: {text}"
        assert res[0]["status"] == expected_status, f"Failed status for: {text}"
        assert not res[0]["review_required"]


# 6. City-only location messages
def test_6_city_only_location_messages():
    # Bila Tserkva, Izmail
    rec1 = {
        "message_id": "m1", "timestamp": "2022-03-01 12:00:00",
        "source_file": "test.html", "raw_text": "Біла Церква. Відбій тривоги."
    }
    res1 = classify_message(rec1)
    assert len(res1) == 1
    assert res1[0]["review_required"] is True
    assert "city_level_event" in res1[0]["review_reason"]

    rec2 = {
        "message_id": "m2", "timestamp": "2022-03-01 13:00:00",
        "source_file": "test.html", "raw_text": "Ізмаїл. Одеська область. Повітряна тривога!"
    }
    res2 = classify_message(rec2)
    assert len(res2) == 1
    assert res2[0]["review_required"] is True
    assert "city_level_event" in res2[0]["review_reason"]


# 7. Multiple regions in one message
def test_7_multiple_regions_in_one_message():
    rec = {
        "message_id": "m1", "timestamp": "2023-10-15 15:30:00",
        "source_file": "test.html",
        "raw_text": "🚨 Повітряна тривога: Київська область, Черкаська область, Полтавська область!"
    }
    res = classify_message(rec)
    assert len(res) == 3
    regions = {r["region"] for r in res}
    assert regions == {"Kyivska oblast", "Cherkaska oblast", "Poltavska oblast"}
    for r in res:
        assert r["status"] == "alert"
        assert not r["review_required"]


# 8. 'Загроза' in a non-alert context
def test_8_threat_in_non_alert_context():
    # Artillery threat without air alert
    rec1 = {
        "message_id": "m1", "timestamp": "2023-04-01 10:00:00",
        "source_file": "test.html",
        "raw_text": "💥 Марганець (Дніпропетровська обл.) Загроза артилерійського обстрілу! Перейдіть в укриття!"
    }
    res1 = classify_message(rec1)
    assert len(res1) == 1
    assert res1[0]["status"] == "unrelated"

    # Drone threat without air alert
    rec2 = {
        "message_id": "m2", "timestamp": "2023-04-01 11:00:00",
        "source_file": "test.html",
        "raw_text": "🛸 Нікополь. Загроза застосування БПЛА. Перейдіть в укриття!"
    }
    res2 = classify_message(rec2)
    assert len(res2) == 1
    assert res2[0]["status"] == "unrelated"


# 9. End without a start (orphan end)
def test_9_end_without_start():
    events = [
        {"region": "Lvivska oblast", "status": "end", "time": "2023-05-01 10:00:00", "message_id": "m1"}
    ]
    intervals, issues = pair_events(events)
    assert len(intervals) == 0
    assert len(issues) == 1
    assert issues[0]["issue_type"] == "orphan_end"
    assert issues[0]["region"] == "Lvivska oblast"


# 10. Repeated alert before an end
def test_10_repeated_alert_before_end():
    events = [
        {"region": "Odeska oblast", "status": "alert", "time": "2023-05-01 10:00:00", "message_id": "m1"},
        {"region": "Odeska oblast", "status": "alert", "time": "2023-05-01 10:30:00", "message_id": "m2"},
        {"region": "Odeska oblast", "status": "end", "time": "2023-05-01 11:00:00", "message_id": "m3"},
    ]
    intervals, issues = pair_events(events)
    assert len(intervals) == 1
    # Original start time preserved
    assert intervals[0]["started_at"] == "2023-05-01 10:00:00"
    assert intervals[0]["ended_at"] == "2023-05-01 11:00:00"
    assert len(issues) == 1
    assert issues[0]["issue_type"] == "repeated_alert"
    assert issues[0]["message_id"] == "m2"


# 11. Missing end at the export boundary
def test_11_missing_end_at_boundary():
    events = [
        {"region": "Sumska oblast", "status": "alert", "time": "2026-10-12 18:00:00", "message_id": "m1"}
    ]
    intervals, issues = pair_events(events)
    assert len(intervals) == 0
    assert len(issues) == 1
    assert issues[0]["issue_type"] == "unresolved_start"
    assert issues[0]["region"] == "Sumska oblast"


# 12. Duplicate Telegram messages
def test_12_duplicate_messages():
    # If same message occurs twice, pairer detects repeated alert
    events = [
        {"region": "Zhytomyrska oblast", "status": "alert", "time": "2023-08-10 12:00:00", "message_id": "m1"},
        {"region": "Zhytomyrska oblast", "status": "alert", "time": "2023-08-10 12:00:00", "message_id": "m1"},
        {"region": "Zhytomyrska oblast", "status": "end", "time": "2023-08-10 13:00:00", "message_id": "m2"},
    ]
    intervals, issues = pair_events(events)
    assert len(intervals) == 1
    assert len(issues) == 1
    assert issues[0]["issue_type"] == "repeated_alert"


# 13. Missing or malformed timestamps
def test_13_missing_or_malformed_timestamps():
    iso_ts, date_part, tz = parse_timestamp(
        title="INVALID_FORMAT",
        date_text="14:30",
        last_date="2023-09-15",
        last_tz="UTC+02:00"
    )
    # Uses fallback
    assert iso_ts == "2023-09-15 14:30:00"

    # Completely unparseable without date
    iso_none, _, _ = parse_timestamp(
        title=None,
        date_text=None,
        last_date=None
    )
    assert iso_none is None


# 14. Unknown or out-of-scope geographic entities
def test_14_unknown_or_out_of_scope_geography():
    # Crimea
    rec_crimea = {
        "message_id": "m1", "timestamp": "2023-08-10 12:00:00",
        "source_file": "test.html",
        "raw_text": "Крим. Повітряна тривога!"
    }
    res_crimea = classify_message(rec_crimea)
    assert len(res_crimea) == 1
    assert res_crimea[0]["review_required"] is True
    assert "out_of_scope_geography" in res_crimea[0]["review_reason"]

    # Unknown region
    rec_unknown = {
        "message_id": "m2", "timestamp": "2023-08-10 12:00:00",
        "source_file": "test.html",
        "raw_text": "Незрозуміле місце. Повітряна тривога!"
    }
    res_unknown = classify_message(rec_unknown)
    assert len(res_unknown) == 1
    assert res_unknown[0]["review_required"] is True
    assert "unresolved_geography" in res_unknown[0]["review_reason"]


# 15. Unrelated messages
def test_15_unrelated_messages():
    # Curfew
    rec1 = {
        "message_id": "m1", "timestamp": "2022-02-25 19:00:00",
        "source_file": "test.html",
        "raw_text": "Дніпро. Сигнал оповіщення буде свідчити про початок комендантської години."
    }
    assert classify_message(rec1)[0]["status"] == "unrelated"

    # Explosions report
    rec2 = {
        "message_id": "m2", "timestamp": "2023-01-10 15:00:00",
        "source_file": "test.html",
        "raw_text": "⚠️ Одеська обл. ЗМІ повідомляють про вибухи. Будьте обережні!"
    }
    assert classify_message(rec2)[0]["status"] == "unrelated"


# 16. Joined Telegram message containers without their own sender block
def test_16_joined_message_containers(tmp_path):
    html_content = """
    <div class="message default clearfix joined" id="message10">
      <div class="body">
        <div class="pull_right date details" title="01.03.2022 10:51:18 UTC+02:00">
          10:51
        </div>
        <div class="text">
          Херсонська область. Повітряна тривога!
        </div>
      </div>
    </div>
    """
    f = tmp_path / "test_joined.html"
    f.write_text(html_content, encoding="utf-8")

    recs, malformed, _, _ = extract_messages_from_file(str(f))
    assert len(recs) == 1
    assert len(malformed) == 0
    assert recs[0]["message_id"] == "message10"
    assert recs[0]["sender"] == ""
    assert recs[0]["timestamp"] == "2022-03-01 10:51:18"
    assert recs[0]["raw_text"] == "Херсонська область. Повітряна тривога!"


# 17. Missing div.text or missing timestamp title attributes
def test_17_missing_text_or_timestamp(tmp_path):
    html_content = """
    <div class="message default clearfix" id="msg_no_text">
      <div class="body">
        <div class="pull_right date details" title="01.03.2022 10:51:18 UTC+02:00">10:51</div>
      </div>
    </div>
    <div class="message default clearfix" id="msg_no_date">
      <div class="body">
        <div class="text">Харківська обл. Повітряна тривога!</div>
      </div>
    </div>
    """
    f = tmp_path / "test_malformed.html"
    f.write_text(html_content, encoding="utf-8")

    recs, malformed, _, _ = extract_messages_from_file(str(f))
    assert len(malformed) == 2
    reasons = {m["reason"] for m in malformed}
    assert "Missing text" in reasons
    assert "Missing timestamp" in reasons


# 18. A message with a reply preview and a separate actual message body
def test_18_reply_preview_and_actual_body():
    html_fragment = """
    <div class="text">
      <div class="reply_to details">In reply to <a href="#go_to_1">Some old quote</a></div>
      Львівська область. Відбій тривоги!
    </div>
    """
    elem = lxml.html.fragment_fromstring(html_fragment)
    cleaned = clean_text(elem)
    assert "Some old quote" not in cleaned
    assert "In reply to" not in cleaned
    assert cleaned == "Львівська область. Відбій тривоги!"

