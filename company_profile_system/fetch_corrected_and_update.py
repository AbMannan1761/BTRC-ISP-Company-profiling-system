import openpyxl
import json
import re
import time
import requests
from bs4 import BeautifulSoup
from openpyxl.styles import Alignment
import urllib3
import sys
sys.path.append('company_profile_system')
import thorough_audit_all_rows as tau

urllib3.disable_warnings()

CACHE_PATH = 'company_profile_system/dis_scraped_cache.json'
EXCEL_PATH = 'Network structure, Orange Communication_updated.xlsx'

with open(CACHE_PATH, 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Find all operator IDs from tau.audit_results that are not in cache or don't have valid iigs
needed_ids = set()
for r in tau.audit_results:
    op_id = r['op_id']
    if op_id:
        if str(op_id) not in cache or not cache[str(op_id)].get('iigs'):
            needed_ids.add(str(op_id))

print(f"Total operators needing DIS fetch: {len(needed_ids)}")

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
form_token = BeautifulSoup(r_rep.text, 'html.parser').find('input', {'name': '_token'})['value']

def parse_iigs_from_html(html):
    table_match = re.search(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
    if not table_match:
        return []
    table_html = table_match.group(1)
    tr_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
    if len(tr_matches) < 4:
        return []
    
    iigs = []
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
                break
    return iigs

def query_dis_op(op_id):
    global form_token
    payload = {
        '_token': form_token,
        'client_type': '',
        'client[]': [str(op_id)],
        'fmonth': 'September',
        'fyear': '2026'
    }
    for attempt in range(3):
        try:
            res = session.post('https://dis.btrc.gov.bd/isp-operator-wise-report-get', data=payload, timeout=25)
            if 'login' in res.url.lower():
                login_dis()
                r_rep = session.get('https://dis.btrc.gov.bd/isp-operator-wise-report', timeout=20)
                form_token = BeautifulSoup(r_rep.text, 'html.parser').find('input', {'name': '_token'})['value']
                payload['_token'] = form_token
                res = session.post('https://dis.btrc.gov.bd/isp-operator-wise-report-get', data=payload, timeout=25)
            iigs = parse_iigs_from_html(res.text)
            if iigs:
                return iigs, 'September 2026'
                
            # August fallback
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
                
            return [], 'No Data'
        except Exception as e:
            print(f"   [Error attempt {attempt+1}] for {op_id}: {e}")
            time.sleep(2)
    return [], "Failed after 3 attempts"

for count, op_id in enumerate(sorted(needed_ids, key=int), 1):
    client_name = tau.dis_clients.get(op_id, 'Unknown')[:35]
    print(f"[{count}/{len(needed_ids)}] Querying ID {op_id} ({client_name})...")
    iigs, source_m = query_dis_op(op_id)
    cache[op_id] = {
        'op_id': op_id,
        'dis_client_text': tau.dis_clients.get(op_id, ''),
        'iigs': iigs,
        'source_month': source_m,
        'updated_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    print(f"       -> {iigs} ({source_m})")
    time.sleep(0.3)

with open(CACHE_PATH, 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print("\n[Cache] Successfully updated cache.")

# Now update the Excel Sheet2 with the DEFINITIVE audit results
print("\n[Excel] Updating Sheet2 with definitive results...")
wb = openpyxl.load_workbook(EXCEL_PATH)
ws = wb['Sheet2']

updated_count = 0
for item in tau.audit_results:
    r = item['row']
    op_id = item['op_id']
    cell = ws.cell(row=r, column=5)
    
    if op_id and str(op_id) in cache and cache[str(op_id)]['iigs']:
        iigs = cache[str(op_id)]['iigs']
        val = "\n".join(iigs)
        cell.value = val
        cell.alignment = Alignment(wrap_text=True, vertical='top')
        updated_count += 1
    elif item['client_text'] == 'NON_ISP':
        cell.value = None
    elif not op_id:
        cell.value = None

wb.save(EXCEL_PATH)
print(f"[Excel] Successfully saved {EXCEL_PATH}!")
print(f"        Total rows populated with Upstream (DIS): {updated_count}")

# Verify Row 295 specifically
wb_check = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
ws_check = wb_check['Sheet2']
r295_val = ws_check.cell(295, 5).value
print("\n=== SPECIFIC VERIFICATION FOR ROW 295 (Cyber Link Communication) ===")
print("SL:", ws_check.cell(295, 1).value)
print("ASN:", ws_check.cell(295, 2).value)
print("Name:", ws_check.cell(295, 3).value)
print("Lic:", ws_check.cell(295, 4).value)
print("Upstrim (DIS):\n" + str(r295_val))
print("Upstrim (Hurrican):", ws_check.cell(295, 6).value)

