import os
import sys
import json
import time
import re
import openpyxl
from openpyxl.styles import Alignment
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings()

CACHE_PATH = 'company_profile_system/dis_scraped_cache.json'
EXCEL_PATH = 'Network structure, Orange Communication_updated.xlsx'

with open(CACHE_PATH, 'r', encoding='utf-8') as f:
    cache = json.load(f)

retry_ids = [op_id for op_id, data in cache.items() if 'Error' in data.get('source_month', '')]
print(f"Operators to retry: {len(retry_ids)} -> {retry_ids}")

if not retry_ids:
    print("No errors to retry!")
    sys.exit(0)

session = requests.Session()
session.verify = False

def login_dis():
    print("[DIS] Logging in...")
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
    # Try September 2026
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
            print(f"Attempt {attempt+1} failed for {op_id}: {e}")
            time.sleep(2)
    return [], f"Failed after 3 attempts"

for op_id in retry_ids:
    print(f"Retrying Operator ID {op_id} ({cache[op_id]['dis_client_text'][:35]})...")
    iigs, smonth = query_dis_op(op_id)
    cache[op_id]['iigs'] = iigs
    cache[op_id]['source_month'] = smonth
    cache[op_id]['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"   -> Result [{smonth}]: {iigs}")
    time.sleep(0.5)

with open(CACHE_PATH, 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print("[Cache] Updated cache with retried operators.")

# Re-run Excel update
print("[Excel] Updating Sheet2 in Excel...")
wb = openpyxl.load_workbook(EXCEL_PATH)
ws = wb['Sheet2']

# Import mapping from build_full_mapping logic
from build_full_mapping import resolve_op

updated = 0
for r in range(2, ws.max_row + 1):
    sl = ws.cell(r, 1).value
    asn = str(ws.cell(r, 2).value or '').strip()
    name = str(ws.cell(r, 3).value or '').strip()
    lic = str(ws.cell(r, 4).value or '').strip()
    curr_dis = ws.cell(r, 5).value
    
    if not name and not asn:
        continue
        
    op_id, matched_name, mtype = resolve_op(asn, name, lic)
    if op_id and str(op_id) in cache and cache[str(op_id)]['iigs']:
        iigs = cache[str(op_id)]['iigs']
        ws.cell(r, 5).value = "\n".join(iigs)
        ws.cell(r, 5).alignment = Alignment(wrap_text=True, vertical='top')
        updated += 1

wb.save(EXCEL_PATH)
print(f"[Excel] Saved successfully! Total rows with Upstream (DIS): {updated}")

