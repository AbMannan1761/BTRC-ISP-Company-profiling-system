import openpyxl
import requests
from bs4 import BeautifulSoup
import urllib3
import re

urllib3.disable_warnings()

wb = openpyxl.load_workbook('Network structure, Orange Communication_updated.xlsx', data_only=True)
ws = wb['Sheet2']
excel_ops = []
for r in range(2, ws.max_row + 1):
    sl = ws.cell(r, 1).value
    asn = ws.cell(r, 2).value
    name = ws.cell(r, 3).value
    lic = ws.cell(r, 4).value
    dis_val = ws.cell(r, 5).value
    if name:
        excel_ops.append((r, sl, asn, str(name).strip(), lic, dis_val))

print(f"Total excel operators: {len(excel_ops)}")

s = requests.Session()
s.verify = False
r = s.get('https://dis.btrc.gov.bd/login', timeout=15)
tok = BeautifulSoup(r.text, 'html.parser').find('input', {'name': '_token'})['value']
s.post('https://dis.btrc.gov.bd/login', data={'_token': tok, 'login': 'sharmin@btrc.gov.bd', 'password': 'Btrce&idd1234'}, timeout=15)

r_rep = s.get('https://dis.btrc.gov.bd/isp-operator-wise-report', timeout=15)
sp_rep = BeautifulSoup(r_rep.text, 'html.parser')
client_sel = sp_rep.find('select', {'id': 'client'})
dis_clients = {}
for opt in client_sel.find_all('option'):
    val = opt.get('value')
    if val:
        dis_clients[val] = opt.text.strip()

print(f"Total DIS clients: {len(dis_clients)}")

def normalize(name):
    name = name.lower()
    name = re.sub(r'[\(\)\.\,\-\_\'\"]', ' ', name)
    name = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation)\b', '', name)
    return ' '.join(name.split())

matched = 0
unmatched = []
for r, sl, asn, name, lic, dis_val in excel_ops:
    norm_name = normalize(name)
    matches = []
    # 1. exact match on operator name before comma
    for cid, dis_text in dis_clients.items():
        parts = dis_text.split(',')
        op_name = parts[0].strip()
        norm_op = normalize(op_name)
        if norm_name == norm_op:
            matches.append((cid, dis_text, 'exact'))
    
    # 2. if no exact, partial
    if not matches:
        for cid, dis_text in dis_clients.items():
            parts = dis_text.split(',')
            op_name = parts[0].strip()
            norm_op = normalize(op_name)
            if (len(norm_name) > 3 and norm_name in norm_op) or (len(norm_op) > 3 and norm_op in norm_name):
                matches.append((cid, dis_text, 'partial'))
                
    if matches:
        matched += 1
    else:
        unmatched.append((r, asn, name, lic))

print(f"Matched: {matched}/{len(excel_ops)}")
print(f"Unmatched: {len(unmatched)}")
print("Sample unmatched (first 20):")
for u in unmatched[:20]:
    print(u)

