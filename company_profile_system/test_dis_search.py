import requests
from bs4 import BeautifulSoup
import urllib3
import re
import openpyxl

urllib3.disable_warnings()

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

wb = openpyxl.load_workbook('Network structure, Orange Communication_updated.xlsx', data_only=True)
ws = wb['Sheet2']

def clean_str(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[\(\)\.\,\-\_\'\"]', ' ', s)
    s = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation|m/s|ms)\b', '', s)
    return ' '.join(s.split())

# Check some of the unmatched names
test_names = [
    'Star Internet Service',
    'MOON NET',
    'Summit Communications Ltd',
    'Orange Bangladesh',
    'Tuhin Enterprise Bangladesh',
    'M/S. SK Net City',
    'Microwin Cyber Cafe',
    'Techno Asia InfoTech Pvt. ltd',
    'Level3 Carrier Ltd.',
    'Peerex Networks Ltd',
    'Ideal Communication Network',
    'KLIK X',
    'KR Online',
    'M.E.B. Technology'
]

for name in test_names:
    cn = clean_str(name)
    found = []
    for cid, text in dis_clients.items():
        ct = clean_str(text.split(',')[0])
        if cn == ct or (len(cn) > 4 and (cn in ct or ct in cn)):
            found.append((cid, text))
    print(f"Query '{name}': {found[:3]}")

