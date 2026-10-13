import os
import re
import time
import lxml.html

def scan_all_files():
    folder = 'TelegramChatExport_2026-10-12'
    files = [f for f in os.listdir(folder) if f.endswith('.html')]
    def file_num(f):
        m = re.match(r'messages(\d+)?\.html', f)
        return int(m.group(1)) if (m and m.group(1)) else 1
    files.sort(key=file_num)

    t0 = time.time()
    total_messages = 0
    total_default_messages = 0
    total_service_messages = 0
    missing_date_title = 0
    non_standard_titles = 0
    timezones = set()
    first_timestamp = None
    last_timestamp = None

    for idx, fname in enumerate(files):
        path = os.path.join(folder, fname)
        tree = lxml.html.parse(path)
        root = tree.getroot()
        
        all_msgs = root.xpath('//div[contains(@class, "message")]')
        total_messages += len(all_msgs)
        
        default_msgs = root.xpath('//div[contains(@class, "message") and contains(@class, "default")]')
        total_default_messages += len(default_msgs)
        
        service_msgs = root.xpath('//div[contains(@class, "message") and contains(@class, "service")]')
        total_service_messages += len(service_msgs)
        
        for m in default_msgs:
            dates = m.xpath('.//div[contains(@class, "date")]')
            title = dates[0].get('title') if dates else None
            if not title:
                missing_date_title += 1
            else:
                m_match = re.match(r'^(\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2}:\d{2}) (UTC[+-]\d{2}:\d{2})$', title)
                if m_match:
                    timezones.add(m_match.group(3))
                    if first_timestamp is None:
                        first_timestamp = title
                    last_timestamp = title
                else:
                    non_standard_titles += 1

        if (idx + 1) % 100 == 0 or idx == len(files) - 1:
            print(f'Processed {idx + 1}/{len(files)} files in {time.time() - t0:.1f}s...')

    print('=== SCAN COMPLETE ===')
    print(f'Total HTML files: {len(files)}')
    print(f'Total messages: {total_messages}')
    print(f'Default messages: {total_default_messages}')
    print(f'Service messages: {total_service_messages}')
    print(f'Missing date titles in default msgs: {missing_date_title}')
    print(f'Non-standard date titles in default msgs: {non_standard_titles}')
    print(f'Discovered timezones: {timezones}')
    print(f'First timestamp: {first_timestamp}')
    print(f'Last timestamp: {last_timestamp}')

if __name__ == '__main__':
    scan_all_files()

