import sys
import re
import lxml.html
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

# The 25 canonical regions:
CANONICAL_REGIONS = [
    "Vinnytska oblast",
    "Volynska oblast",
    "Dnipropetrovska oblast",
    "Donetska oblast",
    "Zhytomyrska oblast",
    "Zakarpatska oblast",
    "Zaporizka oblast",
    "Ivano-Frankivska oblast",
    "Kyivska oblast",
    "Kirovohradska oblast",
    "Luhanska oblast",
    "Lvivska oblast",
    "Mykolaivska oblast",
    "Odeska oblast",
    "Poltavska oblast",
    "Rivnenska oblast",
    "Sumska oblast",
    "Ternopilska oblast",
    "Kharkivska oblast",
    "Khersonska oblast",
    "Khmelnytska oblast",
    "Cherkaska oblast",
    "Chernivetska oblast",
    "Chernihivska oblast",
    "Kyiv",
]

# Let's inspect messages in messages.html (early 2022), messages10.html (mid 2022),
# messages100.html (2023), messages300.html (2025), messages650.html (2026)
test_files = ['messages.html', 'messages2.html', 'messages10.html', 'messages50.html', 'messages100.html', 'messages300.html', 'messages650.html']

for fn in test_files:
    tree = lxml.html.parse(f'TelegramChatExport_2026-10-12/{fn}')
    msgs = tree.getroot().xpath('//div[contains(@class, "message") and contains(@class, "default")]')
    print(f'=== {fn} ({len(msgs)} msgs) ===')
    for m in msgs[:15]:
        t_el = m.xpath('.//div[contains(@class, "text")]')
        if not t_el: continue
        txt = t_el[0].text_content().strip()
        print('  *', txt.replace('\n', ' ')[:90])

