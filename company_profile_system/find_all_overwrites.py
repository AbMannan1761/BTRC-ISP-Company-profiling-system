import openpyxl
import json
import re
from difflib import SequenceMatcher

# Load Master DB
wb_master = openpyxl.load_workbook('BTRC_DIS_Master_Database.xlsx', data_only=True)
ws_master = wb_master['DIS & BGP Master Database']

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

# Load Sheet2
wb = openpyxl.load_workbook('Network structure, Orange Communication_updated.xlsx', data_only=True)
ws = wb['Sheet2']

with open('company_profile_system/dis_scraped_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

def clean(s):
    if not s:
        return ''
    s = s.lower()
    s = re.sub(r'[\(\)\.\,\-\_\'\"\/]', ' ', s)
    s = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation|m/s|ms|bd|bangladesh|t/a|plc|internet|service|services|communication|communications|network|networks|telecom|telecommunication|broadband)\b', '', s)
    return ' '.join(s.split())

# Check each row where ASN has multiple candidates
suspects = []
for r in range(2, ws.max_row + 1):
    sl = ws.cell(r, 1).value
    asn = str(ws.cell(r, 2).value or '').strip()
    name = str(ws.cell(r, 3).value or '').strip()
    lic = str(ws.cell(r, 4).value or '').strip()
    curr_dis = ws.cell(r, 5).value
    
    if not name and not asn:
        continue
        
    candidates = master_by_asn_all.get(asn, [])
    if len(candidates) > 1:
        # Check which candidate best matches name
        best_cand = None
        best_score = -1
        c_name = clean(name)
        for c in candidates:
            score = SequenceMatcher(None, c_name, clean(c['name'])).ratio()
            if score > best_score:
                best_score = score
                best_cand = c
        
        # Check what was actually used in cache / Excel
        # The old master_by_asn dictionary picked the LAST candidate in the Excel!
        last_cand = candidates[-1]
        if best_cand['op_id'] != last_cand['op_id']:
            suspects.append({
                'row': r,
                'sl': sl,
                'asn': asn,
                'name': name,
                'candidates': candidates,
                'correct_cand': best_cand,
                'wrong_cand_used': last_cand,
                'curr_dis': curr_dis
            })

print(f"Total suspects where the wrong candidate was used due to dictionary overwrite: {len(suspects)}")
for s in suspects:
    print(f"\nRow {s['row']} (SL {s['sl']}): {s['asn']} | {s['name']}")
    print(f"   Correct Candidate: ID {s['correct_cand']['op_id']} - {s['correct_cand']['name']} ({s['correct_cand']['lic_no']})")
    print(f"   Wrong Candidate Used: ID {s['wrong_cand_used']['op_id']} - {s['wrong_cand_used']['name']} ({s['wrong_cand_used']['lic_no']})")
    print(f"   Current in Excel: {repr(s['curr_dis'])}")

