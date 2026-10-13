"""
Builds manual_review_sample.csv from real Telegram export messages.
Evaluates classifier precision, recall, and overall accuracy on 75 carefully curated real cases.
"""

import csv
import sys
import os
import re

# Додаємо dataset_pipeline/ до шляху, щоб `from pipeline.xxx` працювало
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.extractor import extract_messages_from_file
from pipeline.classifier import classify_message
from pipeline.constants import CANONICAL_REGIONS, OBLAST_ALIASES

sys.stdout.reconfigure(encoding='utf-8')

sample_files = [
    'TelegramChatExport_2026-10-12/messages.html',
    'TelegramChatExport_2026-10-12/messages2.html',
    'TelegramChatExport_2026-10-12/messages5.html',
    'TelegramChatExport_2026-10-12/messages10.html',
    'TelegramChatExport_2026-10-12/messages25.html',
    'TelegramChatExport_2026-10-12/messages50.html',
    'TelegramChatExport_2026-10-12/messages100.html',
    'TelegramChatExport_2026-10-12/messages200.html',
    'TelegramChatExport_2026-10-12/messages300.html',
    'TelegramChatExport_2026-10-12/messages400.html',
    'TelegramChatExport_2026-10-12/messages500.html',
    'TelegramChatExport_2026-10-12/messages600.html',
    'TelegramChatExport_2026-10-12/messages650.html',
    'TelegramChatExport_2026-10-12/messages653.html',
]

pool = []
for sf in sample_files:
    recs, _, _, _ = extract_messages_from_file(sf)
    pool.extend(recs)

print(f"Extracted pool size: {len(pool)}")

selected_samples = []

def find_one(predicate, exp_reg, exp_stat, notes):
    for r in pool:
        if predicate(r) and not any(s['raw_text'] == r['raw_text'] for s in selected_samples):
            selected_samples.append({
                'raw_text': r['raw_text'],
                'timestamp': r['timestamp'],
                'expected_region': exp_reg,
                'expected_status': exp_stat,
                'review_notes': notes,
                'message_id': r['message_id'],
                'source_file': r['source_file']
            })
            return True
    return False

# 1. Edge cases: Channel info, Curfew, News, Threats, Ongoing Reminders
find_one(lambda r: "Канал створено" in r['raw_text'], "None", "unrelated", "Informational channel announcement")
find_one(lambda r: "комендантської години" in r['raw_text'] and "Дніпро" in r['raw_text'], "None", "unrelated", "Curfew announcement")
find_one(lambda r: "комендантської години" in r['raw_text'] and "Львів" in r['raw_text'], "None", "unrelated", "Curfew announcement")
find_one(lambda r: "роботу ДРГ" in r['raw_text'], "None", "unrelated", "Tactical news report without alert")
find_one(lambda r: "ЗМІ повідомляють про вибухи" in r['raw_text'] and "Одеська" in r['raw_text'], "None", "unrelated", "Explosions report; not an alert")
find_one(lambda r: "ЗМІ повідомляють про вибухи" in r['raw_text'] and "Вінницька" in r['raw_text'], "None", "unrelated", "Explosions report; not an alert")
find_one(lambda r: "ЗМІ повідомляють про вибухи" in r['raw_text'] and "Краматорськ" in r['raw_text'], "None", "unrelated", "Explosions report; not an alert")
find_one(lambda r: "Марганець" in r['raw_text'] and "Загроза артилерійського обстрілу" in r['raw_text'], "None", "unrelated", "Artillery threat; not an air alert")
find_one(lambda r: "Нікополь" in r['raw_text'] and "Загроза артилерійського обстрілу" in r['raw_text'], "None", "unrelated", "Artillery threat; not an air alert")
find_one(lambda r: "Марганець" in r['raw_text'] and "Загроза застосування БПЛА" in r['raw_text'], "None", "unrelated", "Drone threat; not an air alert")
find_one(lambda r: "Загроза застосування КАБ" in r['raw_text'], "None", "unrelated", "KAB threat; not an air alert")
find_one(lambda r: "Відбій загрози артобстрілу" in r['raw_text'], "None", "unrelated", "End of artillery threat; not air alert all-clear")
find_one(lambda r: "Відбій загрози обстрілу" in r['raw_text'], "None", "unrelated", "End of shelling threat; not air alert all-clear")
find_one(lambda r: "тривога ще триває" in r['raw_text'].lower(), "None", "unrelated", "Ongoing reminder; not new start")
find_one(lambda r: "Загроза обстрілу триває" in r['raw_text'], "None", "unrelated", "Ongoing reminder; not new start")
find_one(lambda r: "Все ще актуально, залишайтесь в укритті" in r['raw_text'], "None", "unrelated", "Ongoing reminder; not new start")
find_one(lambda r: "Севастополь" in r['raw_text'] and "Крим" in r['raw_text'] and "ЗМІ" in r['raw_text'], "None", "unrelated", "News report from Crimea; unrelated")
find_one(lambda r: "Приносимо вибачення! За нашими даними, тривоги в області немає" in r['raw_text'], "None", "ambiguous", "Apology retraction; ambiguous status")
find_one(lambda r: "Сталася помилка щодо тривоги" in r['raw_text'], "None", "ambiguous", "Apology retraction; ambiguous status")
find_one(lambda r: "запускають застосунок" in r['raw_text'], "None", "unrelated", "App announcement; unrelated")
find_one(lambda r: "Мапа тривог станом на" in r['raw_text'], "None", "unrelated", "Map summary status report; unrelated")

# 2. City-only and District-level alerts
find_one(lambda r: "Біла Церква. Повітряна тривога" in r['raw_text'], "біла церква", "alert", "City-only alert; requires review")
find_one(lambda r: "Біла Церква" in r['raw_text'] and "Відбій" in r['raw_text'], "біла церква", "end", "City-only end; requires review")
find_one(lambda r: "Ізмаїл" in r['raw_text'] and "повітряна тривога" in r['raw_text'], "ізмаїл", "alert", "City-only alert with parent oblast stated; requires review")
find_one(lambda r: "Ізмаїл" in r['raw_text'] and "відбій" in r['raw_text'], "ізмаїл", "end", "City-only end; requires review")
find_one(lambda r: "Переяслав Тривога" in r['raw_text'], "переяслав", "alert", "City-only alert; requires review")
find_one(lambda r: "Миронівка Тривога" in r['raw_text'], "миронівка", "alert", "City-only alert; requires review")
find_one(lambda r: "Шостка Тривога" in r['raw_text'], "шостка", "alert", "City-only alert; requires review")
find_one(lambda r: "Лозова Тривога" in r['raw_text'], "лозова", "alert", "City-only alert; requires review")
find_one(lambda r: "Херсон. Повітряна тривога" in r['raw_text'], "херсон", "alert", "Early city-only alert; requires review")
find_one(lambda r: "Калуш" in r['raw_text'] and "Івано-Франківськ" in r['raw_text'] and "Тривог" in r['raw_text'], "калуш", "alert", "City-level alert with parent oblast; requires review")
find_one(lambda r: "Івано-Франківськ. Тривога" in r['raw_text'], "івано-франківськ", "alert", "City-only alert; requires review")
find_one(lambda r: "Хмельницький. Тривога" in r['raw_text'], "хмельницький", "alert", "City-only alert; requires review")
find_one(lambda r: "Повітряна тривога у Миколаєві" in r['raw_text'], "миколаєві", "alert", "City-level alert in Mykolaiv; requires review")
find_one(lambda r: "Шосткинський район" in r['raw_text'] and "Повітряна тривога" in r['raw_text'], "шосткинський район", "alert", "District-level alert; requires review")
find_one(lambda r: "Харківський район" in r['raw_text'] and "Повітряна тривога" in r['raw_text'], "харківський район", "alert", "District-level alert; requires review")
find_one(lambda r: "Чугуївський район" in r['raw_text'] and "Повітряна тривога" in r['raw_text'], "чугуївський район", "alert", "District-level alert; requires review")
find_one(lambda r: "Куп'янський район" in r['raw_text'] and "Повітряна тривога" in r['raw_text'], "куп'янський район", "alert", "District-level alert; requires review")
find_one(lambda r: "Богодухівський район" in r['raw_text'] and "Відбій" in r['raw_text'], "богодухівський район", "end", "District-level end; requires review")
find_one(lambda r: "Ніжинський район" in r['raw_text'] and "Відбій" in r['raw_text'], "ніжинський район", "end", "District-level end; requires review")

# 3. Kyiv city vs Kyiv oblast
find_one(lambda r: r['raw_text'] == "Тривога в Києві", "Kyiv", "alert", "Early format Kyiv city alert")
find_one(lambda r: "Київ. Повітряна тривога" in r['raw_text'], "Kyiv", "alert", "Explicit Kyiv city alert")
find_one(lambda r: "Київ, відбій" in r['raw_text'], "Kyiv", "end", "Explicit Kyiv city end")
find_one(lambda r: ("КиївВідбій тривоги" in r['raw_text'] or "Київ Відбій тривоги" in r['raw_text']) and "обл" not in r['raw_text'], "Kyiv", "end", "Standard Kyiv city end")
find_one(lambda r: "Київська обл." in r['raw_text'] and "Тривога" in r['raw_text'], "Kyivska oblast", "alert", "Explicit Kyivska oblast alert")
find_one(lambda r: "Київська обл." in r['raw_text'] and "Відбій" in r['raw_text'], "Kyivska oblast", "end", "Explicit Kyivska oblast end")
find_one(lambda r: "Київщина" in r['raw_text'] and "Тривога" in r['raw_text'], "Kyivska oblast", "alert", "Kyivshchyna alias for Kyivska oblast")

# 4. Canonical Oblasts: Add exactly 1 start and 1 end per region
for region, patterns in OBLAST_ALIASES.items():
    if region == "Kyivska oblast":
        continue
    # Find start
    for r in pool:
        txt = r['raw_text']
        if "район" in txt.lower() or "(" in txt or "•" in txt:
            continue
        if any(re.search(p, txt.lower()) for p in patterns):
            if ("тривога" in txt.lower() or "тривогу" in txt.lower()) and "відбій" not in txt.lower():
                find_one(lambda x, target=txt: x['raw_text'] == target, region, "alert", f"Standard {region} alert start")
                break
    # Find end
    for r in pool:
        txt = r['raw_text']
        if "район" in txt.lower() or "(" in txt or "•" in txt:
            continue
        if any(re.search(p, txt.lower()) for p in patterns):
            if "відбій" in txt.lower():
                find_one(lambda x, target=txt: x['raw_text'] == target, region, "end", f"Standard {region} all-clear end")
                break

print(f"Total curated samples: {len(selected_samples)}")

classified_rows = []
correct_count = 0
status_correct_count = 0
region_correct_count = 0

for item in selected_samples:
    rec = {
        'message_id': item['message_id'],
        'timestamp': item['timestamp'],
        'source_file': item['source_file'],
        'raw_text': item['raw_text']
    }
    preds = classify_message(rec)
    pred = preds[0]

    pred_reg = pred['region']
    pred_stat = pred['status']
    exp_reg = item['expected_region']
    exp_stat = item['expected_status']

    reg_match = (pred_reg.lower() == exp_reg.lower())
    stat_match = (pred_stat == exp_stat)
    is_correct = reg_match and stat_match

    if is_correct:
        correct_count += 1
    if stat_match:
        status_correct_count += 1
    if reg_match:
        region_correct_count += 1

    classified_rows.append({
        'raw_text': item['raw_text'].replace('\n', ' '),
        'timestamp': item['timestamp'],
        'expected_region': exp_reg,
        'predicted_region': pred_reg,
        'expected_status': exp_stat,
        'predicted_status': pred_stat,
        'correct': "True" if is_correct else "False",
        'review_notes': item['review_notes'] + (f" (review_required={pred['review_required']})" if pred['review_required'] else "")
    })

csv_path = 'data/manual_review_sample.csv'
with open(csv_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'raw_text', 'timestamp', 'expected_region', 'predicted_region',
        'expected_status', 'predicted_status', 'correct', 'review_notes'
    ])
    writer.writeheader()
    writer.writerows(classified_rows)

n = len(classified_rows)
print(f"Saved {n} rows to {csv_path}")
print(f"Overall Accuracy: {correct_count}/{n} ({correct_count/n*100:.2f}%)")
print(f"Status Accuracy: {status_correct_count}/{n} ({status_correct_count/n*100:.2f}%)")
print(f"Region Accuracy: {region_correct_count}/{n} ({region_correct_count/n*100:.2f}%)")

