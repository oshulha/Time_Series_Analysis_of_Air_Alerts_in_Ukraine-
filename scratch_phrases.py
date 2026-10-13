import sys
import re
import lxml.html
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

alert_phrases = Counter()
end_phrases = Counter()
other_phrases = Counter()

sample_files = ['messages.html', 'messages5.html', 'messages10.html', 'messages20.html', 'messages50.html', 
                'messages100.html', 'messages200.html', 'messages300.html', 'messages400.html', 'messages500.html', 'messages600.html', 'messages653.html']

for fn in sample_files:
    tree = lxml.html.parse(f'TelegramChatExport_2026-10-12/{fn}')
    msgs = tree.getroot().xpath('//div[contains(@class, "message") and contains(@class, "default")]')
    for m in msgs:
        t_el = m.xpath('.//div[contains(@class, "text")]')
        if not t_el: continue
        txt = t_el[0].text_content().strip()
        lower = txt.lower()
        
        # Check end
        if 'відбій' in lower:
            # find sentence or clause with vidbiy
            m_v = re.search(r'відбій[^\.\!\n\—\-]*', lower)
            if m_v:
                end_phrases[m_v.group(0).strip()] += 1
        elif 'тривог' in lower:
            m_t = re.search(r'([^\.\!\n\—\-]*повітряна\s+тривога[^\.\!\n\—\-]*|тривога[^\.\!\n\—\-]*)', lower)
            if m_t:
                alert_phrases[m_t.group(0).strip()] += 1
        else:
            first_words = ' '.join(re.sub(r'^[^\w\s]+', '', txt).split()[:3])
            other_phrases[first_words] += 1

print('=== TOP ALERT PHRASES ===')
for p, c in alert_phrases.most_common(25):
    print(f'{c:5d} | {p}')

print('\n=== TOP END PHRASES ===')
for p, c in end_phrases.most_common(25):
    print(f'{c:5d} | {p}')

print('\n=== TOP OTHER PHRASES ===')
for p, c in other_phrases.most_common(25):
    print(f'{c:5d} | {p}')

