import os
import sys
import json
import time
import re
import openpyxl
from openpyxl.styles import Alignment
import sqlite3
import requests
from bs4 import BeautifulSoup
import urllib3
from difflib import SequenceMatcher

urllib3.disable_warnings()

# Configuration
EXCEL_PATH = 'Network structure, Orange Communication_updated.xlsx'
CACHE_PATH = 'company_profile_system/dis_scraped_cache.json'
MASTER_DB_XLSX = 'BTRC_DIS_Master_Database.xlsx'
SQLITE_DB = 'company_profile_system/Apps/company_master_profile.db'

print(f"=== Starting DIS Upstream Sync for {EXCEL_PATH} ===")

# 1. Load Master DB and SQLite DB for mapping
wb_master = openpyxl.load_workbook(MASTER_DB_XLSX, data_only=True)
ws_master = wb_master['DIS & BGP Master Database']
master_by_asn = {}
for r in range(2, ws_master.max_row + 1):
    op_id = ws_master.cell(r, 1).value
    name = ws_master.cell(r, 2).value
    asn = ws_master.cell(r, 17).value
    if asn and str(asn).strip():
        master_by_asn[str(asn).strip()] = {
            'op_id': str(op_id).strip() if op_id else '',
            'name': str(name).strip() if name else ''
        }

conn = sqlite3.connect(SQLITE_DB)
cur = conn.cursor()
cur.execute('SELECT asn, dis_operator_id, canonical_name FROM company_profiles WHERE dis_operator_id IS NOT NULL AND dis_operator_id != ""')
sqlite_by_asn = {}
for row in cur.fetchall():
    if row[0]:
        sqlite_by_asn[row[0].strip()] = {
            'op_id': str(row[1]).strip(),
            'name': row[2].strip() if row[2] else ''
        }
conn.close()

# 2. DIS Session & Client Select options
session = requests.Session()
session.verify = False

def login_dis():
    print("[DIS] Logging into https://dis.btrc.gov.bd/login ...")
    r = session.get('https://dis.btrc.gov.bd/login', timeout=20)
    tok = BeautifulSoup(r.text, 'html.parser').find('input', {'name': '_token'})['value']
    session.post('https://dis.btrc.gov.bd/login', data={
        '_token': tok,
        'login': 'sharmin@btrc.gov.bd',
        'password': 'Btrce&idd1234'
    }, timeout=20)
    print("[DIS] Logged in successfully.")

login_dis()

r_rep = session.get('https://dis.btrc.gov.bd/isp-operator-wise-report', timeout=20)
sp_rep = BeautifulSoup(r_rep.text, 'html.parser')
form_token = sp_rep.find('input', {'name': '_token'})['value']
client_sel = sp_rep.find('select', {'id': 'client'})
dis_clients = {}
for opt in client_sel.find_all('option'):
    val = opt.get('value')
    if val:
        dis_clients[val] = opt.text.strip()
print(f"[DIS] Found {len(dis_clients)} operators in client dropdown.")

# 3. Known Manual & Trade Name Overrides
MANUAL_OVERRIDES = {
    'AS134424': '3032', # Orange Communication
    'AS135341': '3032', # Orange Communication
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
    'AS137186': '5025', # Universal Friends Communication Network -> Universal Friends Communication Network
    'AS136948': '4950', # Today Vision -> M/s. Today Vision Internet & Dish Network
    'AS149649': '3480', # Speed Touch Network and Technology -> Speed Touch Network & Technology
    'AS154828': '5057', # Airnet Broadband Internet Gateway -> Airnet Broadband Internet
    'AS133957': '3124', # SOL-BD -> M/s. SOL-BD
    'AS140544': '2959', # INNOVATIVE TECHNOLOGY & ENGINEERING -> Innovative Online Limited
    'AS140287': '3478', # OK Network and Communications -> Ok Network & Communications
    'AS138403': '3148', # Bismilla Enterprise -> Bismillah Enterprise
    'AS38256': '3382',  # Bengal Group Ltd. -> Bengal Broadband Ltd.
    'AS139672': '5988', # Cherry Enterprise -> Cherry Enterprice
    'AS149426': '5540', # DDN-Media -> DDN Communication
    'AS138981': '5056', # M/S. SK Net City -> Net City
}

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

def clean(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[\(\)\.\,\-\_\'\"\/]', ' ', s)
    s = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation|m/s|ms|bd|bangladesh|t/a|plc|internet|service|services|communication|communications|network|networks|telecom|telecommunication|broadband)\b', '', s)
    return ' '.join(s.split())

def extract_trade_name(name):
    m = re.search(r'[\s\b]t/a[\s\b](.+)$', name, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

def resolve_op(asn_str, name_str, lic_str):
    if asn_str in NON_ISPS:
        return None, "NON_ISP", "Non-ISP Entity"
        
    if asn_str in MANUAL_OVERRIDES:
        cid = MANUAL_OVERRIDES[asn_str]
        return cid, dis_clients.get(cid, ''), 'ManualOverride'
        
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

    if asn_str and asn_str in master_by_asn:
        e = master_by_asn[asn_str]
        return e['op_id'], e['name'], 'Master_ASN'
        
    if asn_str and asn_str in sqlite_by_asn:
        e = sqlite_by_asn[asn_str]
        return e['op_id'], e['name'], 'SQLite_ASN'
        
    c_name = clean(name_str)
    if c_name:
        for cid, text in dis_clients.items():
            c_op = clean(text.split(',')[0])
            if c_name == c_op:
                return cid, text, 'DIS_ExactClean'
                
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

# 4. Fast Parser for Table
def parse_iigs_from_html(html):
    table_match = re.search(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
    if not table_match:
        return []
    table_html = table_match.group(1)
    tr_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
    if len(tr_matches) < 4:
        return []
    
    iigs = []
    # Row 0: ['Upstream Information', 'Downstream Information']
    # Row 1: ['Month', 'Operator name', 'Sl', 'Name of IIG', ...]
    # Row 2: ['From', 'To']
    # Row 3+: Data rows
    for i, tr in enumerate(tr_matches[3:], start=1):
        tds = [re.sub(r'<[^>]+>', '', td).strip() for td in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)]
        if not tds:
            continue
        if i == 1:
            if len(tds) >= 4:
                val = tds[3]
                if val and val not in ['No Data Available', 'Name of IIG', ''] and val not in iigs:
                    iigs.append(val)
        else:
            if tds[0].isdigit():
                if len(tds) >= 2:
                    val = tds[1]
                    if val and val not in ['No Data Available', 'Name of IIG', ''] and val not in iigs:
                        iigs.append(val)
            else:
                # Upstream section completed
                break
    return iigs

# 5. Query function with retry and fallback
def query_dis_operator(op_id):
    global form_token
    payload_sep = {
        '_token': form_token,
        'client_type': '',
        'client[]': [str(op_id)],
        'fmonth': 'September',
        'fyear': '2026'
    }
    try:
        res = session.post('https://dis.btrc.gov.bd/isp-operator-wise-report-get', data=payload_sep, timeout=25)
        # Check if session expired
        if 'login' in res.url.lower():
            print(f"[DIS] Session expired. Re-logging in...")
            login_dis()
            r_rep = session.get('https://dis.btrc.gov.bd/isp-operator-wise-report', timeout=20)
            form_token = BeautifulSoup(r_rep.text, 'html.parser').find('input', {'name': '_token'})['value']
            payload_sep['_token'] = form_token
            res = session.post('https://dis.btrc.gov.bd/isp-operator-wise-report-get', data=payload_sep, timeout=25)

        iigs = parse_iigs_from_html(res.text)
        if iigs:
            return iigs, 'September 2026'
            
        # Fallback to August 2026
        payload_aug = {
            '_token': form_token,
            'client_type': '',
            'client[]': [str(op_id)],
            'fmonth': 'August',
            'fyear': '2026'
        }
        res_aug = session.post('https://dis.btrc.gov.bd/isp-operator-wise-report-get', data=payload_aug, timeout=25)
        iigs_aug = parse_iigs_from_html(res_aug.text)
        if iigs_aug:
            return iigs_aug, 'August 2026'

        # Fallback to July 2026
        payload_jul = {
            '_token': form_token,
            'client_type': '',
            'client[]': [str(op_id)],
            'fmonth': 'July',
            'fyear': '2026'
        }
        res_jul = session.post('https://dis.btrc.gov.bd/isp-operator-wise-report-get', data=payload_jul, timeout=25)
        iigs_jul = parse_iigs_from_html(res_jul.text)
        if iigs_jul:
            return iigs_jul, 'July 2026'

        return [], 'No Data'
    except Exception as e:
        print(f"[DIS Error] Error querying operator {op_id}: {e}")
        return [], f'Error: {e}'

# 6. Load Cache
cache = {}
if os.path.exists(CACHE_PATH):
    try:
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(f"[Cache] Loaded {len(cache)} cached operators.")
    except Exception as e:
        print(f"[Cache] Failed to load cache: {e}")

# 7. Collect all rows from Excel
wb_target = openpyxl.load_workbook(EXCEL_PATH)
ws_target = wb_target['Sheet2']

rows_to_process = []
for r in range(2, ws_target.max_row + 1):
    sl = ws_target.cell(r, 1).value
    asn = str(ws_target.cell(r, 2).value or '').strip()
    name = str(ws_target.cell(r, 3).value or '').strip()
    lic = str(ws_target.cell(r, 4).value or '').strip()
    curr_dis = ws_target.cell(r, 5).value
    
    if not name and not asn:
        continue
        
    op_id, matched_name, mtype = resolve_op(asn, name, lic)
    rows_to_process.append({
        'row': r,
        'sl': sl,
        'asn': asn,
        'name': name,
        'lic': lic,
        'curr_dis': curr_dis,
        'op_id': op_id,
        'matched_name': matched_name,
        'mtype': mtype
    })

print(f"[Excel] Total rows with data: {len(rows_to_process)}")

# Collect unique op_ids to query
unique_op_ids = set()
for item in rows_to_process:
    if item['op_id']:
        unique_op_ids.add(item['op_id'])

print(f"[DIS] Unique DIS operator IDs to query: {len(unique_op_ids)}")

# 8. Query DIS for each unique op_id
count = 0
for op_id in sorted(unique_op_ids, key=int):
    count += 1
    if str(op_id) in cache:
        continue
        
    print(f"[{count}/{len(unique_op_ids)}] Fetching DIS data for Operator ID {op_id} ({dis_clients.get(str(op_id), 'Unknown')[:40]})...")
    iigs, source_month = query_dis_operator(op_id)
    cache[str(op_id)] = {
        'op_id': str(op_id),
        'dis_client_text': dis_clients.get(str(op_id), ''),
        'iigs': iigs,
        'source_month': source_month,
        'updated_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    print(f"       -> Result [{source_month}]: {iigs}")
    
    # Save cache incrementally
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
        
    # Politeness delay
    time.sleep(0.3)

print(f"\n[DIS] All operator queries completed. Cache has {len(cache)} entries.")

# 9. Update Excel Sheet2
print("\n[Excel] Updating Sheet2 column 'Upstrim (DIS) '...")
updated_rows_count = 0
empty_rows_count = 0

for item in rows_to_process:
    r = item['row']
    op_id = item['op_id']
    cell = ws_target.cell(row=r, column=5)
    
    # If operator has DIS data
    if op_id and str(op_id) in cache and cache[str(op_id)]['iigs']:
        iigs = cache[str(op_id)]['iigs']
        val = "\n".join(iigs)
        cell.value = val
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        updated_rows_count += 1
    elif item['curr_dis'] and str(item['curr_dis']).strip():
        # Keep existing manual value if any
        pass
    else:
        empty_rows_count += 1

wb_target.save(EXCEL_PATH)
print(f"[Excel] Successfully saved {EXCEL_PATH}!")
print(f"        Rows with Upstream (DIS) populated: {updated_rows_count}")
print(f"        Rows without DIS upstream data: {empty_rows_count}")

# 10. Verification
print("\n=== VERIFICATION (Sample Rows) ===")
wb_check = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
ws_check = wb_check['Sheet2']
for test_r in [2, 3, 4, 12, 137, 138, 139, 140, 141, 142]:
    r_sl = ws_check.cell(test_r, 1).value
    r_asn = ws_check.cell(test_r, 2).value
    r_name = ws_check.cell(test_r, 3).value
    r_dis = ws_check.cell(test_r, 5).value
    r_dis_disp = repr(r_dis)[:60] if r_dis else 'None'
    print(f"Row {test_r:3d} | SL: {r_sl} | {r_asn} | {r_name[:30]:30s} | DIS: {r_dis_disp}")

print("\n=== All Tasks Completed Successfully ===")

