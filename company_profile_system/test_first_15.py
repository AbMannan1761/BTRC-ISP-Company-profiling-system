import openpyxl
import requests
from bs4 import BeautifulSoup
import urllib3
import re
import time

urllib3.disable_warnings()

# 1. Load Excel Sheet2
wb = openpyxl.load_workbook('Network structure, Orange Communication_updated.xlsx', data_only=True)
ws = wb['Sheet2']

# 2. Load Master DB for mapping
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

# 3. DIS Login
s = requests.Session()
s.verify = False
r = s.get('https://dis.btrc.gov.bd/login', timeout=15)
tok = BeautifulSoup(r.text, 'html.parser').find('input', {'name': '_token'})['value']
s.post('https://dis.btrc.gov.bd/login', data={'_token': tok, 'login': 'sharmin@btrc.gov.bd', 'password': 'Btrce&idd1234'}, timeout=15)

r_rep = s.get('https://dis.btrc.gov.bd/isp-operator-wise-report', timeout=15)
sp_rep = BeautifulSoup(r_rep.text, 'html.parser')
tok2 = sp_rep.find('input', {'name': '_token'})['value']

def parse_iigs(html):
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
                if val and val != 'No Data Available' and val not in iigs:
                    iigs.append(val)
        else:
            if tds[0].isdigit():
                if len(tds) >= 2:
                    val = tds[1]
                    if val and val != 'No Data Available' and val not in iigs:
                        iigs.append(val)
            else:
                break
    return iigs

def query_dis(op_id, month='September', year='2026'):
    payload = {
        '_token': tok2,
        'client_type': '',
        'client[]': [str(op_id)],
        'fmonth': month,
        'fyear': year
    }
    try:
        res = s.post('https://dis.btrc.gov.bd/isp-operator-wise-report-get', data=payload, timeout=20)
        return parse_iigs(res.text)
    except Exception as e:
        print(f"Error querying {op_id}: {e}")
        return []

# Test first 15 operators from Sheet2
for r in range(2, 17):
    sl = ws.cell(r, 1).value
    asn = str(ws.cell(r, 2).value or '').strip()
    name = str(ws.cell(r, 3).value or '').strip()
    lic = str(ws.cell(r, 4).value or '').strip()
    dis_curr = ws.cell(r, 5).value
    hur_curr = ws.cell(r, 6).value
    
    op_id = None
    if asn and asn in master_by_asn:
        op_id = master_by_asn[asn]['op_id']
        
    print(f"\nRow {r}: {sl} | {asn} | {name} | Lic: {lic} | ID: {op_id}")
    if op_id:
        iigs_sep = query_dis(op_id, 'September', '2026')
        print(f"   Sep 2026: {iigs_sep}")
        if not iigs_sep:
            # check August 2026
            iigs_aug = query_dis(op_id, 'August', '2026')
            print(f"   Aug 2026: {iigs_aug}")
            if not iigs_aug:
                # check latest available
                iigs_oct = query_dis(op_id, 'October', '2026')
                print(f"   Oct 2026: {iigs_oct}")
    else:
        print("   No DIS ID mapped")

