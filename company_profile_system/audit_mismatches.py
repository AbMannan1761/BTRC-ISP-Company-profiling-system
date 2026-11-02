import openpyxl
import json
import re
from difflib import SequenceMatcher

with open('company_profile_system/dis_scraped_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Load DIS clients list from orange_dis_report.html
from bs4 import BeautifulSoup
with open('company_profile_system/sample/orange_dis_report.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
    client_sel = soup.find('select', {'id': 'client'})
    dis_clients = {opt.get('value'): opt.text.strip() for opt in client_sel.find_all('option') if opt.get('value')}

# Load Master DB
wb_master = openpyxl.load_workbook('BTRC_DIS_Master_Database.xlsx', data_only=True)
ws_master = wb_master['DIS & BGP Master Database']

# Map ASN to list of all possible operators
master_by_asn_all = {}
for r in range(2, ws_master.max_row + 1):
    op_id = ws_master.cell(r, 1).value
    name = ws_master.cell(r, 2).value
    category = ws_master.cell(r, 3).value
    lic_no = ws_master.cell(r, 4).value
    asn = ws_master.cell(r, 17).value
    if asn and str(asn).strip():
        asn_str = str(asn).strip()
        if asn_str not in master_by_asn_all:
            master_by_asn_all[asn_str] = []
        master_by_asn_all[asn_str].append({
            'op_id': str(op_id).strip() if op_id else '',
            'name': str(name).strip() if name else '',
            'category': str(category).strip() if category else '',
            'lic_no': str(lic_no).strip() if lic_no else ''
        })

wb = openpyxl.load_workbook('Network structure, Orange Communication_updated.xlsx', data_only=True)
ws = wb['Sheet2']

def clean(s):
    if not s:
        return ''
    s = s.lower()
    s = re.sub(r'[\(\)\.\,\-\_\'\"\/]', ' ', s)
    s = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation|m/s|ms|bd|bangladesh|t/a|plc|internet|service|services|communication|communications|network|networks|telecom|telecommunication|broadband)\b', '', s)
    return ' '.join(s.split())

print("=== CHECKING MULTIPLE OPERATORS PER ASN IN MASTER DB ===")
multi_asn_count = 0
for asn, ops in master_by_asn_all.items():
    if len(ops) > 1:
        multi_asn_count += 1
print(f"ASNs with multiple operators: {multi_asn_count}")

# Now check each row in Excel Sheet2
print("\n=== AUDITING ALL ROWS IN SHEET2 ===")
mismatches = []
better_matches = []

for r in range(2, ws.max_row + 1):
    sl = ws.cell(r, 1).value
    asn = str(ws.cell(r, 2).value or '').strip()
    name = str(ws.cell(r, 3).value or '').strip()
    lic = str(ws.cell(r, 4).value or '').strip()
    curr_dis = ws.cell(r, 5).value
    
    if not name and not asn:
        continue

    # 1. Check if multiple operators exist for this ASN
    candidates_by_asn = master_by_asn_all.get(asn, [])
    
    # 2. Check all DIS clients that match name
    c_name = clean(name)
    dis_name_candidates = []
    for cid, text in dis_clients.items():
        c_dis = clean(text.split(',')[0])
        if c_name and (c_name == c_dis or c_name in c_dis or c_dis in c_name):
            dis_name_candidates.append((cid, text, SequenceMatcher(None, c_name, c_dis).ratio()))
    dis_name_candidates.sort(key=lambda x: x[2], reverse=True)

    # Let's see what is currently in cell and what was matched
    # E.g. for row 295
    if 'cyber link' in name.lower():
        print(f"Row {r} (SL {sl}): {asn} | {name}")
        print(f"   Candidates by ASN: {candidates_by_asn}")
        print(f"   Top candidates by Name: {dis_name_candidates[:3]}")

    # If ASN has multiple candidates, find the one that best matches name
    if len(candidates_by_asn) > 1:
        best_candidate = None
        best_score = -1
        for cand in candidates_by_asn:
            score = SequenceMatcher(None, clean(name), clean(cand['name'])).ratio()
            if score > best_score:
                best_score = score
                best_candidate = cand
        mismatches.append({
            'row': r,
            'sl': sl,
            'asn': asn,
            'name': name,
            'candidates': candidates_by_asn,
            'best_by_name': best_candidate,
            'curr_dis': curr_dis
        })

print(f"\nTotal rows with multiple ASN candidates: {len(mismatches)}")
for m in mismatches:
    print(f"\nRow {m['row']} (SL {m['sl']}): {m['asn']} | {m['name']}")
    for c in m['candidates']:
        print(f"   Option: ID {c['op_id']} - {c['name']} ({c['category']})")
    print(f"   Best Match: ID {m['best_by_name']['op_id']} - {m['best_by_name']['name']}")
    print(f"   Current in Excel: {repr(m['curr_dis'])}")

