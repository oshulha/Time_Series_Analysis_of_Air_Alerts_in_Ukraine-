import time
import lxml.html

with open('TelegramChatExport_2026-10-12/messages.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Approach 1: xpath
t0 = time.time()
root = lxml.html.fromstring(content)
for m in root.xpath('//div[contains(@class, "message") and contains(@class, "default")]'):
    d = m.xpath('.//div[contains(@class, "date")]')
    t = m.xpath('.//div[contains(@class, "text")]')
t1 = time.time()
print('XPath per element:', t1 - t0)

# Approach 2: iterating children / class check
t0 = time.time()
root = lxml.html.fromstring(content)
for m in root.iter('div'):
    cls = m.get('class')
    if cls and 'default' in cls and 'message' in cls:
        date_el = None
        text_el = None
        for child in m.iter('div'):
            ccls = child.get('class')
            if ccls:
                if 'date' in ccls and not date_el: date_el = child
                if 'text' in ccls and not text_el: text_el = child
t2 = time.time()
print('Direct iter:', t2 - t0)

