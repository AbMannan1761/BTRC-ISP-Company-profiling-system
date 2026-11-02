import openpyxl
import json
import re
from difflib import SequenceMatcher
from bs4 import BeautifulSoup

# Load DIS clients list from orange_dis_report.html
with open('company_profile_system/sample/orange_dis_report.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
    client_sel = soup.find('select', {'id': 'client'})
    dis_clients = {}
    for opt in client_sel.find_all('option'):
        val = opt.get('value')
        if val:
            dis_clients[val] = opt.text.strip()

# Load Master DB
wb_master = openpyxl.load_workbook('BTRC_DIS_Master_Database.xlsx', data_only=True)
ws_master = wb_master['DIS & BGP Master Database']

master_records = []
for r in range(2, ws_master.max_row + 1):
    op_id = ws_master.cell(r, 1).value
    name = ws_master.cell(r, 2).value
    category = ws_master.cell(r, 3).value
    lic_no = ws_master.cell(r, 4).value
    asn = ws_master.cell(r, 17).value
    master_records.append({
        'op_id': str(op_id).strip() if op_id else '',
        'name': str(name).strip() if name else '',
        'category': str(category).strip() if category else '',
        'lic_no': str(lic_no).strip() if lic_no else '',
        'asn': str(asn).strip() if asn else ''
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

def extract_trade_name(name):
    m = re.search(r'[\s\b]t/a[\s\b](.+)$', name, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

def find_best_dis_client(asn_str, name_str, lic_str):
    c_name = clean(name_str)
    t_name = extract_trade_name(name_str)
    c_tname = clean(t_name) if t_name else ''
    
    # Check trade name exact
    target_names = [c_name]
    if c_tname:
        target_names.insert(0, c_tname)
        
    # Strategy 1: Look for exact cleaned name in DIS clients
    for tn in target_names:
        if not tn: continue
        exact_matches = []
        for cid, text in dis_clients.items():
            op_part = text.split(',')[0].strip()
            if clean(op_part) == tn:
                exact_matches.append((cid, text))
        if len(exact_matches) == 1:
            return exact_matches[0][0], exact_matches[0][1], 'ExactNameDIS'
        elif len(exact_matches) > 1:
            # disambiguate by license_no or ASN in master
            for em_id, em_text in exact_matches:
                for mr in master_records:
                    if mr['op_id'] == em_id and asn_str and mr['asn'] == asn_str:
                        return em_id, em_text, 'ExactNameDIS+ASN'
            # disambiguate by category
            if lic_str:
                for em_id, em_text in exact_matches:
                    for mr in master_records:
                        if mr['op_id'] == em_id and lic_str.lower() in mr['category'].lower():
                            return em_id, em_text, 'ExactNameDIS+Cat'
            return exact_matches[0][0], exact_matches[0][1], 'ExactNameDIS_First'

    # Strategy 2: ASN match in Master Records, but SCORE BY NAME!
    if asn_str:
        asn_candidates = [mr for mr in master_records if mr['asn'] == asn_str]
        if len(asn_candidates) == 1:
            cid = asn_candidates[0]['op_id']
            # Make sure name is at least somewhat related!
            s = SequenceMatcher(None, c_name, clean(asn_candidates[0]['name'])).ratio()
            if s >= 0.4:
                return cid, dis_clients.get(cid, asn_candidates[0]['name']), f'MasterASN_Single(s={s:.2f})'
        elif len(asn_candidates) > 1:
            # Pick candidate that best matches name
            best_c = None
            best_s = -1
            for cand in asn_candidates:
                s = SequenceMatcher(None, c_name, clean(cand['name'])).ratio()
                if s > best_s:
                    best_s = s
                    best_c = cand
            if best_c and best_s >= 0.4:
                return best_c['op_id'], dis_clients.get(best_c['op_id'], best_c['name']), f'MasterASN_MultiBest(s={best_s:.2f})'

    # Strategy 3: Partial / Fuzzy name match in DIS clients
    for tn in target_names:
        if len(tn) > 3:
            fuzzy = []
            for cid, text in dis_clients.items():
                op_part = clean(text.split(',')[0].strip())
                if tn in op_part or op_part in tn:
                    s = SequenceMatcher(None, tn, op_part).ratio()
                    fuzzy.append((cid, text, s))
            if fuzzy:
                fuzzy.sort(key=lambda x: x[2], reverse=True)
                if fuzzy[0][2] >= 0.6:
                    return fuzzy[0][0], fuzzy[0][1], f'FuzzyDIS(s={fuzzy[0][2]:.2f})'
                    
    return None, None, 'NoMatch'

# Compare existing vs new resolution
changed = []
for r in range(2, ws.max_row + 1):
    sl = ws.cell(r, 1).value
    asn = str(ws.cell(r, 2).value or '').strip()
    name = str(ws.cell(r, 3).value or '').strip()
    lic = str(ws.cell(r, 4).value or '').strip()
    curr_dis = ws.cell(r, 5).value
    
    if not name and not asn:
        continue
        
    op_id, client_text, mtype = find_best_dis_client(asn, name, lic)
    
    # Check row 295 specifically
    if r == 295:
        print(f"Row 295 resolution: ID={op_id}, text='{client_text}', type={mtype}")

with open('company_profile_system/dis_scraped_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

for r in range(2, ws.max_row + 1):
    sl = ws.cell(r, 1).value
    asn = str(ws.cell(r, 2).value or '').strip()
    name = str(ws.cell(r, 3).value or '').strip()
    lic = str(ws.cell(r, 4).value or '').strip()
    curr_dis = ws.cell(r, 5).value
    
    if not name and not asn:
        continue
        
    op_id, client_text, mtype = find_best_dis_client(asn, name, lic)
    if op_id:
        cached_data = cache.get(str(op_id), {})
        cached_iigs = cached_data.get('iigs', [])
        cached_str = "\n".join(cached_iigs) if cached_iigs else None
        
        # Check if different from current cell
        curr_clean = str(curr_dis).strip() if curr_dis else None
        cached_clean = str(cached_str).strip() if cached_str else None
        if curr_clean != cached_clean and cached_clean is not None:
            changed.append((r, sl, asn, name, op_id, client_text, curr_clean, cached_clean))

print(f"\nTotal rows with improved/different resolution: {len(changed)}")
for ch in changed:
    print(f"\nRow {ch[0]} (SL {ch[1]}): {ch[2]} | {ch[3]}")
    print(f"   Mapped to: ID {ch[4]} - {ch[5]}")
    print(f"   Old Excel DIS:\n   {repr(ch[6])}")
    print(f"   New DIS:\n   {repr(ch[7])}")

