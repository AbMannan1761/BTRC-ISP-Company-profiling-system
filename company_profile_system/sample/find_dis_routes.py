import sys
import requests
from bs4 import BeautifulSoup
import re
import urllib3
urllib3.disable_warnings()

sys.stdout.reconfigure(encoding='utf-8')

s = requests.Session()
s.verify = False

r = s.get('https://dis.btrc.gov.bd/login')
tok = BeautifulSoup(r.text, 'html.parser').find('input', {'name': '_token'}).get('value')
s.post('https://dis.btrc.gov.bd/login', data={'_token': tok, 'login': 'sharmin@btrc.gov.bd', 'password': 'Btrce&idd1234'})
r_dash = s.get('https://dis.btrc.gov.bd/dashboard')

hrefs = re.findall(r'href=["\']([^"\']+)["\']', r_dash.text)
for h in set(hrefs):
    if 'btrc.gov.bd' in h or h.startswith('/'):
        print('Route:', h)
