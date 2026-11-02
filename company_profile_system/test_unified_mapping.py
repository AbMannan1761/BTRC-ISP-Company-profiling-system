import openpyxl
import sqlite3
import re
from difflib import SequenceMatcher

# 1. Load Excel Sheet2
wb_orange = openpyxl.load_workbook('Network structure, Orange Communication_updated.xlsx', data_only=True)
ws_orange = wb_orange['Sheet2']

# 2. Load Master DB xlsx
wb_master = openpyxl.load_workbook('BTRC_DIS_Master_Database.xlsx', data_only=True)
ws_master = wb_master['DIS & BGP Master Database']

master_by_asn = {}
master_by_name = []
for r in range(2, ws_master.max_row + 1):
    op_id = ws_master.cell(r, 1).value
    name = ws_master.cell(r, 2).value
    category = ws_master.cell(r, 3).value
    lic_no = ws_master.cell(r, 4).value
    asn = ws_master.cell(r, 17).value
    
    entry = {
        'op_id': str(op_id).strip() if op_id else '',
        'name': str(name).strip() if name else '',
        'category': str(category).strip() if category else '',
        'lic_no': str(lic_no).strip() if lic_no else '',
        'asn': str(asn).strip() if asn else ''
    }
    if entry['asn']:
        master_by_asn[entry['asn']] = entry
    master_by_name.append(entry)

# 3. Load SQLite DB
conn = sqlite3.connect('company_profile_system/Apps/company_master_profile.db')
cur = conn.cursor()
cur.execute('SELECT asn, dis_operator_id, canonical_name, license_status FROM company_profiles WHERE dis_operator_id IS NOT NULL AND dis_operator_id != ""')
sqlite_by_asn = {}
for row in cur.fetchall():
    if row[0]:
        sqlite_by_asn[row[0].strip()] = {
            'op_id': str(row[1]).strip(),
            'name': row[2].strip() if row[2] else '',
            'category': row[3].strip() if row[3] else ''
        }

# 4. Read DIS client options (saved from report page)
with open('company_profile_system/sample/orange_dis_report.html', 'r', encoding='utf-8') as f:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(f.read(), 'html.parser')
    client_sel = soup.find('select', {'id': 'client'})
    dis_clients = {}
    for opt in client_sel.find_all('option'):
        val = opt.get('value')
        if val:
            dis_clients[val] = opt.text.strip()

print(f"Master ASN entries: {len(master_by_asn)}")
print(f"SQLite ASN entries: {len(sqlite_by_asn)}")
print(f"DIS Clients: {len(dis_clients)}")

def clean(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[\(\)\.\,\-\_\'\"\/]', ' ', s)
    s = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation|m/s|ms|bd|bangladesh|t/a|plc|internet|service|services|communication|communications|network|networks|telecom|telecommunication)\b', '', s)
    return ' '.join(s.split())

def match_row(asn_str, name_str, lic_str):
    # 1. ASN in master_by_asn
    if asn_str and asn_str in master_by_asn:
        e = master_by_asn[asn_str]
        return e['op_id'], e['name'], 'Master_ASN'
        
    # 2. ASN in sqlite_by_asn
    if asn_str and asn_str in sqlite_by_asn:
        e = sqlite_by_asn[asn_str]
        return e['op_id'], e['name'], 'SQLite_ASN'
        
    # 3. DIS Client exact name (before comma)
    c_name = clean(name_str)
    for cid, text in dis_clients.items():
        op_part = text.split(',')[0].strip()
        if clean(op_part) == c_name and c_name:
            return cid, text, 'DIS_ExactClean'
            
    # 4. Partial in DIS clients
    if len(c_name) > 3:
        candidates = []
        for cid, text in dis_clients.items():
            op_part = text.split(',')[0].strip()
            c_op = clean(op_part)
            if c_op == c_name:
                candidates.append((cid, text, 100))
            elif c_name in c_op or c_op in c_name:
                # similarity
                r = SequenceMatcher(None, c_name, c_op).ratio()
                candidates.append((cid, text, r))
        if candidates:
            candidates.sort(key=lambda x: x[2], reverse=True)
            if candidates[0][2] >= 0.7:
                return candidates[0][0], candidates[0][1], f"DIS_Fuzzy_{candidates[0][2]:.2f}"
                
    return None, None, 'Unmatched'

mapped = 0
unmapped = []
mapping_result = []

for r in range(2, 296):
    sl = ws_orange.cell(r, 1).value
    asn = str(ws_orange.cell(r, 2).value or '').strip()
    name = str(ws_orange.cell(r, 3).value or '').strip()
    lic = str(ws_orange.cell(r, 4).value or '').strip()
    dis_curr = ws_orange.cell(r, 5).value
    hur_curr = ws_orange.cell(r, 6).value
    
    op_id, matched_name, mtype = match_row(asn, name, lic)
    if op_id:
        mapped += 1
        mapping_result.append((r, sl, asn, name, lic, op_id, matched_name, mtype))
    else:
        unmapped.append((r, sl, asn, name, lic))

print(f"\nTotal rows evaluated: 294")
print(f"Successfully mapped: {mapped} / 294 ({mapped/294*100:.1f}%)")
print(f"Unmapped: {len(unmapped)}")
print("\nUnmapped rows:")
for u in unmapped:
    print(u)

