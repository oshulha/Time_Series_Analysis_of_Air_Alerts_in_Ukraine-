import sys
import re
import lxml.html

sys.stdout.reconfigure(encoding='utf-8')

# Search for messages with multiple regions across files
files = ['messages.html', 'messages5.html', 'messages10.html', 'messages25.html', 'messages50.html', 'messages100.html', 'messages300.html', 'messages500.html', 'messages650.html']

for fn in files:
    tree = lxml.html.parse(f'TelegramChatExport_2026-10-12/{fn}')
    msgs = tree.getroot().xpath('//div[contains(@class, "message") and contains(@class, "default")]')
    for m in msgs:
        t_el = m.xpath('.//div[contains(@class, "text")]')
        if not t_el: continue
        txt = t_el[0].text_content().strip()
        # Find occurrences of 'обл'
        obls = re.findall(r'(\w+)\s+обл', txt)
        if len(obls) > 1:
            mid = m.get('id')
            dt = m.xpath('.//div[contains(@class, "date")]')[0].get('title')
            print(f"{fn} | {mid} | {dt} | obls={obls} | text={repr(txt[:120])}")

