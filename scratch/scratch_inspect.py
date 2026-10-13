import sys
import lxml.html

sys.stdout.reconfigure(encoding='utf-8')

tree = lxml.html.parse('TelegramChatExport_2026-10-12/messages.html')
m2 = tree.getroot().xpath('//div[@id="message2"]//div[contains(@class, "text")]')[0]

# Without br handling:
raw1 = m2.text_content().strip()
print("Raw text_content():", repr(raw1[:100]))

# With br handling:
for br in m2.xpath('.//br'):
    br.tail = '\n' + (br.tail or '')
raw2 = m2.text_content().strip()
print("With br as newline:", repr(raw2[:100]))

