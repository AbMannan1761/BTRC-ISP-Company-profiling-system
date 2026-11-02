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

# 4. Read DIS client options
with open('company_profile_system/sample/orange_dis_report.html', 'r', encoding='utf-8') as f:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(f.read(), 'html.parser')
    client_sel = soup.find('select', {'id': 'client'})
    dis_clients = {}
    for opt in client_sel.find_all('option'):
        val = opt.get('value')
        if val:
            dis_clients[val] = opt.text.strip()

def clean(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[\(\)\.\,\-\_\'\"\/]', ' ', s)
    s = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation|m/s|ms|bd|bangladesh|t/a|plc|internet|service|services|communication|communications|network|networks|telecom|telecommunication|broadband)\b', '', s)
    return ' '.join(s.split())

def extract_trade_name(name):
    # look for t/a or T/A
    m = re.search(r'[\s\b]t/a[\s\b](.+)$', name, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

# Known manual overrides for tricky names
MANUAL_OVERRIDES = {
    'AS134424': '3032', # Orange Communication
    'AS135341': '3032', # Orange Communication (alternate ASN)
    'AS137868': '3494', # Star Internet Service -> M/S Star Internet Services
    'AS147292': '3620', # Microwin Cyber Cafe -> M/s. Microwin Cyber Café
    'AS134971': '3379', # Md. Maniruzzaman Manir t/a Doly IT Corner -> M/s. Doly IT Corner
    'AS134798': '4160', # Hossain Ahmed Masum T/A Alicon Network -> Alicon Network
    'AS135410': '5833', # Voltz System and Solutions -> Voltz System & Solutions
    'AS150384': '5166', # Progresive Enterprise -> Progressive Enterprise
    'AS9825': '5770',   # Sustainable Development Networking Program -> SDNF
    'AS135353': '3500', # MD SHIRAJUL HAIDER T/A Cue Club Technology -> Cue Club Technology
    'AS134236': '3467', # Sheikh Mohammad Zulfiquer t/a Tetrasoft -> Tetrasoft
    'AS135578': '3586', # Muhammad Nasir t/a Dhaka Information Technology -> M/s. Dhaka Information Technology
    'AS24556': '2947',  # Bijoy Online Ltd. Multihome Internet Service Provider -> Bijoy Online Limited
    'AS134180': '3378', # Md. Shariful Islam T/A BRISK SYSTEMS -> Brisk Systems
    'AS135311': '3602', # Golam Mohammad T/A 29Communication -> M/s. 29 Communication
    'AS132092': '3400', # Mir Mosharrof Hossain t/a IT Base -> IT Base
    'AS136272': '3761', # MOHAMMAD ANOWER HOSSAIN t/a SUN ONLINE -> Sun Online
    'AS135604': '3592', # Sharmin Akter Shilpi t/a M/S. Saiba International -> M/s. Saiba International
    'AS137385': '3504', # Saddam Hossain t/a Asian Network -> M/s. Asian Network
    'AS138522': '4153', # Kazi Rajib Ferdous t/a Chocolate Broadband -> Chocolate Broadband
    'AS136732': '3526', # Yellow Net & Cyber Cafe -> Yellow Net
    'AS153432': '5041', # Tongi Online -> Tongi On Line
    'AS140237': '4159', # Speed Net BD -> Speed Net
    'AS149021': '4323', # City Network -> City Network
    'AS137186': '5025', # Universal Friends Communication Network -> Universal Friends Communication Network (Ufc. Net)
}

# Non-ISPs (should be skipped or marked as non-ISP)
NON_ISPS = {
    'AS58717',  # Summit Communications Ltd (NTTN)
    'AS58682',  # Level3 Carrier Ltd. (IIG)
    'AS137491', # Peerex Networks Ltd (IIG)
    'AS150178', # EXABYTE LTD (IIG)
    'AS150774', # EXABYTE LTD (IIG)
    'AS133477', # Bangladesh Police (Govt)
    'AS139303', # IPDC FINANCE PLC (Financial)
    'AS137045', # APNIC ASN block
    'AS139233', # PT REKAYASA ANAK BUMI INDONESIA (Overseas)
    'AS138203', # Sonali Bank Limited (Bank)
    'AS141423', # UCB FinTech Company Ltd (FinTech)
    'AS151488', # Ad-din Mother Care Limited (Hospital)
}

def resolve_op(asn_str, name_str, lic_str):
    if asn_str in NON_ISPS:
        return None, "NON_ISP", "Non-ISP Entity"
        
    if asn_str in MANUAL_OVERRIDES:
        cid = MANUAL_OVERRIDES[asn_str]
        return cid, dis_clients.get(cid, ''), 'ManualOverride'
        
    # Check trade name
    tname = extract_trade_name(name_str)
    if tname:
        c_tname = clean(tname)
        for cid, text in dis_clients.items():
            c_op = clean(text.split(',')[0])
            if c_tname and c_op == c_tname:
                return cid, text, 'TradeName_Exact'
        for cid, text in dis_clients.items():
            c_op = clean(text.split(',')[0])
            if c_tname and (c_tname in c_op or c_op in c_tname):
                return cid, text, 'TradeName_Partial'

    # Master ASN
    if asn_str and asn_str in master_by_asn:
        e = master_by_asn[asn_str]
        return e['op_id'], e['name'], 'Master_ASN'
        
    # SQLite ASN
    if asn_str and asn_str in sqlite_by_asn:
        e = sqlite_by_asn[asn_str]
        return e['op_id'], e['name'], 'SQLite_ASN'
        
    # Clean name match in DIS
    c_name = clean(name_str)
    if c_name:
        for cid, text in dis_clients.items():
            c_op = clean(text.split(',')[0])
            if c_name == c_op:
                return cid, text, 'DIS_ExactClean'
                
        # Partial match in DIS
        candidates = []
        for cid, text in dis_clients.items():
            c_op = clean(text.split(',')[0])
            if c_name in c_op or c_op in c_name:
                r = SequenceMatcher(None, c_name, c_op).ratio()
                candidates.append((cid, text, r))
        if candidates:
            candidates.sort(key=lambda x: x[2], reverse=True)
            if candidates[0][2] >= 0.75:
                return candidates[0][0], candidates[0][1], f"DIS_Fuzzy_{candidates[0][2]:.2f}"
                
    return None, None, 'Unmatched'

mapped = 0
non_isps = 0
unmatched = []
final_mapping = []

for r in range(2, 296):
    sl = ws_orange.cell(r, 1).value
    asn = str(ws_orange.cell(r, 2).value or '').strip()
    name = str(ws_orange.cell(r, 3).value or '').strip()
    lic = str(ws_orange.cell(r, 4).value or '').strip()
    
    op_id, dis_name, mtype = resolve_op(asn, name, lic)
    if op_id:
        mapped += 1
        final_mapping.append((r, sl, asn, name, lic, op_id, dis_name, mtype))
    elif mtype == 'Non-ISP Entity':
        non_isps += 1
        final_mapping.append((r, sl, asn, name, lic, None, 'NON_ISP', mtype))
    else:
        unmatched.append((r, sl, asn, name, lic))

print(f"Total rows: 294")
print(f"Successfully mapped to DIS: {mapped} ({mapped/294*100:.1f}%)")
print(f"Non-ISP entities: {non_isps}")
print(f"Remaining unmatched: {len(unmatched)}")
if unmatched:
    print("\nRemaining unmatched rows:")
    for u in unmatched:
        print(u)

