# Data Quality and Pipeline Report: Ukrainian Air Alerts

**Generated:** 2026-10-13 12:48:09  
**Pipeline Runtime:** 1606.3 seconds  
**Source Directory:** `TelegramChatExport_2026-10-12`  

---

## 1. Executive Summary

A robust, streaming data engineering pipeline was implemented to parse, classify, and reconstruct historical air-raid alerts for the 24 administrative oblasts of Ukraine and the city of Kyiv (25 canonical entities).

- **Total HTML Export Files Processed:** 653 (0 failed out of 653)
- **Total Telegram Messages Extracted:** 652,303
- **Observed Date Coverage:** `2022-02-25 18:18:44` to `2026-10-12 20:14:53` (Timezone: `UTC+02:00` normalized)
- **Coverage Verification:** The source export begins on **25 February 2022 18:18:44 UTC+02:00** and concludes on **12 October 2026 20:14:53 UTC+02:00**, covering the complete 4.5+ year period.
- **Completed Alert Intervals:** 70,351 intervals in `alerts.csv`
- **Pairing Issues Flagged:** 4,463 in `pairing_issues.csv`

---

## 2. Extraction & Parsing Metrics

| Metric | Value | Description |
| :--- | :--- | :--- |
| **HTML Files Discovered** | `653` | Paginated `messages.html` ... `messages653.html` |
| **HTML Files Successfully Processed** | `653` | 100% parse success rate via lxml DOM streaming |
| **HTML Files Failed** | `0` | 0 failures |
| **Total Extracted Records** | `652,303` | Valid default message containers |
| **Earliest Timestamp** | `2022-02-25 18:18:44` | 25 February 2022 |
| **Latest Timestamp** | `2026-10-12 20:14:53` | 12 October 2026 |
| **Duplicate Message IDs** | `0` | Telegram container ID duplicates |
| **Duplicate Content & Timestamps** | `91` | Repeated identical messages |
| **Malformed Messages / Missing Date** | `116` | Recorded in extraction audit |

---

## 3. Classification Breakdown

All extracted messages were categorized deterministically using context-aware rules and centralized Ukrainian morphological alias dictionaries:

| Classification Status | Count | Share (%) | Description |
| :--- | :--- | :--- | :--- |
| **alert** (Air-Raid Alert Start) | `184,708` | 28.32% | Air alert announcements |
| **end** (All-Clear Announcement) | `175,283` | 26.87% | All-clear / Відбій events |
| **unrelated** (Excluded) | `281,841` | 43.21% | Curfews, media explosion news, tactical threats, app announcements |
| **ambiguous** (Review Required) | `10,475` | 1.61% | Retractions, false alarms, unclear status |

### Review & Exclusions Details
- **City-Level Events:** `12,108` (e.g., Bila Tserkva, Izmail, Nikopol; per Rule 4, kept in `review_required.csv` rather than silently promoted to oblast level).
- **Sub-Oblast / District-Level Events:** `198,570` (e.g., Nizhynskyi rayon, Shostkynskyi rayon, yellow/red bullet levels; per Rule 6, kept in `review_required.csv`).
- **Out-of-Scope Geography:** `1` (e.g., Crimea, Sevastopol).

---

## 4. Regional Statistics (25 Canonical Target Entities)

| Canonical Region | Start Events | End Events | Total Events | Completed Intervals | Unresolved Starts | Orphan Ends |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Vinnytska oblast** | 1,499 | 1,493 | 2,992 | 1,485 | 0 | 8 |
| **Volynska oblast** | 841 | 842 | 1,683 | 833 | 0 | 9 |
| **Dnipropetrovska oblast** | 5,593 | 5,612 | 11,205 | 5,566 | 0 | 46 |
| **Donetska oblast** | 7,134 | 6,894 | 14,028 | 6,860 | 0 | 34 |
| **Zhytomyrska oblast** | 1,476 | 1,461 | 2,937 | 1,457 | 0 | 4 |
| **Zakarpatska oblast** | 672 | 671 | 1,343 | 666 | 0 | 5 |
| **Zaporizka oblast** | 6,691 | 6,667 | 13,358 | 6,656 | 1 | 11 |
| **Ivano-Frankivska oblast** | 763 | 759 | 1,522 | 749 | 0 | 10 |
| **Kyivska oblast** | 2,960 | 2,606 | 5,566 | 2,515 | 0 | 91 |
| **Kirovohradska oblast** | 6,036 | 5,122 | 11,158 | 4,941 | 0 | 181 |
| **Luhanska oblast** | 4 | 0 | 4 | 0 | 1 | 0 |
| **Lvivska oblast** | 748 | 751 | 1,499 | 746 | 0 | 5 |
| **Mykolaivska oblast** | 3,730 | 3,695 | 7,425 | 3,682 | 0 | 13 |
| **Odeska oblast** | 2,443 | 2,434 | 4,877 | 2,422 | 0 | 12 |
| **Poltavska oblast** | 4,010 | 3,996 | 8,006 | 3,989 | 0 | 7 |
| **Rivnenska oblast** | 925 | 925 | 1,850 | 916 | 0 | 9 |
| **Sumska oblast** | 4,105 | 4,089 | 8,194 | 4,075 | 1 | 14 |
| **Ternopilska oblast** | 870 | 873 | 1,743 | 865 | 0 | 8 |
| **Kharkivska oblast** | 10,034 | 9,787 | 19,821 | 9,186 | 1 | 601 |
| **Khersonska oblast** | 3,570 | 3,564 | 7,134 | 3,554 | 0 | 10 |
| **Khmelnytska oblast** | 1,063 | 1,055 | 2,118 | 1,047 | 0 | 8 |
| **Cherkaska oblast** | 2,496 | 2,488 | 4,984 | 2,475 | 0 | 13 |
| **Chernivetska oblast** | 765 | 765 | 1,530 | 752 | 0 | 13 |
| **Chernihivska oblast** | 2,544 | 2,534 | 5,078 | 2,517 | 1 | 17 |
| **Kyiv** | 2,606 | 2,419 | 5,025 | 2,397 | 0 | 22 |

---

## 5. Event Pairing & Anomaly Analysis

Pairing was executed independently per region in chronological order:
- An `alert` event opens an active interval.
- An `end` event closes the currently open active interval.
- Events are never paired across different regions.
- Intervals require `ended_at >= started_at`.

### Summary of Pairing Issues (`pairing_issues.csv`)
| Issue Type | Count | Description |
| :--- | :--- | :--- |
| **Orphan End (`orphan_end`)** | `1,151` | All-clear received when no preceding alert was active |
| **Repeated Alert (`repeated_alert`)** | `3,222` | New alert received while interval was already open |
| **Unresolved Start (`unresolved_start`)** | `5` | Alert start never closed by end of export |
| **Negative Duration (`negative_duration`)** | `0` | `ended_at < started_at` |
| **Excessive Duration (`excessive_duration`)** | `85` | Valid interval lasting > 24 hours (e.g., frontline / Luhansk) |

---

## 6. City-Level Interpretation & Boundary Analysis

1. **Kyiv City vs Kyiv Oblast:**
   - Standalone `Київ` and `м. Київ` map exclusively to `Kyiv` (canonical city entity).
   - `Київська область` and `Київщина` map exclusively to `Kyivska oblast`.
   - Distinct events and independent intervals are preserved for both entities.

2. **City-Only Alerts:**
   - In 2022, before the channel fully standardized whole-oblast reporting, some alerts were issued for individual cities (e.g., Bila Tserkva, Izmail, Pereyaslav, Myronivka, Kherson city).
   - Per Project Rule 4, city-level alerts are recorded in `review_required.csv` with `review_reason="city_level_event"` rather than silently converted to oblast events.

3. **District-Level / Tactical Alerts:**
   - In 2023–2026, the channel introduced localized district alerts (`... район`), artillery threat notices, and color-coded alert levels (yellow/red).
   - These sub-oblast events are isolated in `review_required.csv` to preserve the integrity of whole-oblast time series intervals in `alerts.csv`.

---

## 7. Assumptions, Known Limitations & Reproducibility

### Assumptions
- **Timezone:** All timestamps in the Telegram export explicitly carry `UTC+02:00`. Timestamps in `alerts.csv` are normalized to `YYYY-MM-DD HH:MM:SS` (local export standard time, UTC+02:00).
- **Export Boundaries:** Alerts open at the end of the export or ends without starts at the beginning are treated as boundary truncations and recorded in `pairing_issues.csv` without fabricating artificial timestamps.

### How to Run
```bash
# 1. Install dependencies
python -m pip install -r requirements.txt
# or: python -m pip install beautifulsoup4 lxml pytest

# 2. Run unit tests
python -m pytest -v tests/test_pipeline.py

# 3. Execute full pipeline
python run_pipeline.py
```
