import sys
import csv
import json
import urllib.request
import re
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding='utf-8')

def clean_name(n):
    if not n:
        return ""
    n = n.strip().lower()
    for s in ["limited", "ltd.", "ltd", "private", "pvt.", "pvt", "online", "communication", "communications", "internet", "network", "networks", "broadband", "cyber", "technology", "technologies", "tel", "telecom", "it", "link"]:
        n = re.sub(rf'\b{s}\b', '', n)
    return re.sub(r'[^a-z0-9]', '', n)

print("1. Parsing Commission Meetings Database...")
with open('company_profile_system/btrc_meeting_portal_db.json', 'r', encoding='utf-8') as f:
    meeting_data = json.load(f)

meetings = meeting_data.get('meetings', [])
commission_records = []
for m in meetings:
    m_no = m.get('meeting_number', '')
    m_date = m.get('meeting_date', '')
    for a in m.get('agendas', []):
        subj = a.get('subject', '')
        dec = a.get('decision', '')
        a_no = a.get('agenda_no', '')
        commission_records.append({
            'meeting_number': m_no,
            'meeting_date': m_date,
            'agenda_no': a_no,
            'subject': subj,
            'decision': dec
        })

print(f"Total Commission Decisions extracted: {len(commission_records)}")

print("\n2. Downloading and Parsing Administrative Penalty Sheets...")
penalty_gids = {
    '1406070721': 'ISP Penalties Main',
    '2103364223': 'ISP Penalties Archive',
    '1015475416': 'IIG Penalties',
    '1029870126': 'IPTSP Penalties',
    '1590013494': 'NTTN Penalties',
    '1504476267': 'TVAS Penalties'
}

penalties = []
for gid, label in penalty_gids.items():
    try:
        url = f"https://docs.google.com/spreadsheets/d/14xfghrOlfgDNspFHYNaJanuTkDDx_bWLigBwXBGySrU/export?format=csv&gid={gid}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        csv_text = urllib.request.urlopen(req, timeout=8).read().decode('utf-8')
        reader = csv.reader(csv_text.splitlines())
        rows = list(reader)
        print(f"  - Sheet '{label}' (GID: {gid}): {len(rows)} rows")
        
        # Determine column indexes
        header_idx = -1
        name_col = -1
        fine_col = -1
        meeting_col = -1
        reason_col = -1
        status_col = -1
        
        for r_idx, row in enumerate(rows[:6]):
            for c_idx, cell in enumerate(row):
                c_low = cell.strip().lower()
                if 'প্রতিষ্ঠানের নাম' in c_low or 'অপারেটর' in c_low or 'কোম্পানি' in c_low:
                    header_idx = r_idx
                    name_col = c_idx
                if 'জরিমানা' in c_low and ('পরিমাণ' in c_low or 'টাকা' in c_low):
                    fine_col = c_idx
                if 'কমিশন সভা' in c_low or 'সভা' in c_low:
                    meeting_col = c_idx
                if 'কারণ' in c_low or 'অভিযোগ' in c_low or 'বিষয়' in c_low:
                    reason_col = c_idx
                if 'পরিশোধ' in c_low or 'অবস্থা' in c_low:
                    status_col = c_idx
        
        if name_col != -1 and header_idx != -1:
            for row in rows[header_idx + 1:]:
                if len(row) > name_col and row[name_col].strip():
                    comp_name = row[name_col].strip()
                    if comp_name in ['মোট', 'সর্বমোট', 'Total'] or len(comp_name) < 2:
                        continue
                    fine_val = row[fine_col].strip() if fine_col != -1 and len(row) > fine_col else ''
                    meeting_val = row[meeting_col].strip() if meeting_col != -1 and len(row) > meeting_col else ''
                    reason_val = row[reason_col].strip() if reason_col != -1 and len(row) > reason_col else ''
                    status_val = row[status_col].strip() if status_col != -1 and len(row) > status_col else 'বকেয়া'
                    
                    penalties.append({
                        'company_name': comp_name,
                        'category': label,
                        'fine_amount': fine_val,
                        'meeting_info': meeting_val,
                        'reason': reason_val,
                        'status': status_val,
                        'sheet': label
                    })
    except Exception as e:
        print(f"Error fetching sheet {gid}: {e}")

print(f"\nTotal Penalties extracted: {len(penalties)}")

# Save to local cache
with open('company_profile_system/ei_penalties_cache.json', 'w', encoding='utf-8') as f:
    json.dump(penalties, f, ensure_ascii=False, indent=2)

with open('company_profile_system/ei_commission_cache.json', 'w', encoding='utf-8') as f:
    json.dump(commission_records, f, ensure_ascii=False, indent=2)

print("Saved ei_penalties_cache.json and ei_commission_cache.json successfully!")
