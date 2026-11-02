import sys
import urllib.request
import re
import json

sys.stdout.reconfigure(encoding='utf-8')

req = urllib.request.Request('https://abmannan1761.github.io/btrc-meeting-portal/', headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

m = re.search(r'const masterDb\s*=\s*(\{[\s\S]*?\});\s*(?:const|let|var|function|window)', html)
if m:
    json_text = m.group(1)
    print("Found masterDb, length:", len(json_text))
    data = json.loads(json_text)
    meetings = data.get('meetings', [])
    print(f"Total meetings: {len(meetings)}")
    agendas_count = sum(len(m.get('agendas', [])) for m in meetings)
    print(f"Total agendas: {agendas_count}")
    
    # Save masterDb locally
    with open('company_profile_system/btrc_meeting_portal_db.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Saved to company_profile_system/btrc_meeting_portal_db.json")
    
    # Show first 2 agenda samples
    for m in meetings[:2]:
        print("Meeting:", m.get('meeting_number'), m.get('meeting_date'))
        for a in m.get('agendas', [])[:2]:
            print("  - Agenda:", a.get('agenda_no'), a.get('subject')[:80])
            print("    Decision:", a.get('decision', '')[:100])
else:
    print("masterDb pattern not found")
