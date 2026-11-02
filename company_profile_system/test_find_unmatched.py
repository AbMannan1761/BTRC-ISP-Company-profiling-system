import openpyxl
import re
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings()

# Fetch DIS clients
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

unmatched_names = [
    (9, 'AS136217', 'MOON NET', ''),
    (11, 'AS137453', 'Orange Bangladesh', ''),
    (22, 'AS133157', 'Firefly Solution', ''),
    (45, 'AS147292', 'Microwin Cyber Cafe', 'Thana or Upazilla'),
    (48, 'AS154120', 'PHP Computer', ''),
    (56, 'AS58682', 'Level3 Carrier Ltd.', 'IIG'),
    (57, 'AS137491', 'Peerex Networks Ltd', 'IIG'),
    (63, 'AS133477', 'Bangladesh Police', ''),
    (67, 'AS137186', 'Universal Friends Communication Network', ''),
    (74, 'AS134971', 'Md. Maniruzzaman Manir t/a Doly IT Corner', 'Divisional'),
    (78, 'AS134798', 'Hossain Ahmed Masum T/A Alicon Network', ''),
    (84, 'AS59239', 'iTel Limited', ''),
    (90, 'AS137396', 'Md Zubayrul Hoque', ''),
    (100, 'AS135410', 'Voltz System and Solutions', 'Thana or Upazilla'),
    (109, 'AS139303', 'IPDC FINANCE PLC', ''),
    (112, 'AS150384', 'Progresive Enterprise', 'Thana or Upazilla'),
    (113, 'AS150178', 'EXABYTE LTD', 'IIG'),
    (115, 'AS140949', 'Diginet', 'Divisional'),
    (131, 'AS141763', 'Titas Enterprise', 'District'),
    (142, 'AS9825', 'Sustainable Development Networking Program', 'Nationwide'),
    (148, 'AS154723', 'Optical Communication', ''),
    (158, 'AS137045', 'APNIC ASN block', ''),
    (166, 'AS141473', 'Jessore IT', 'Thana or Upazilla'),
    (185, 'AS142044', 'Contrivance Technology', ''),
    (206, 'AS138561', 'BroadBandZone', ''),
    (213, 'AS135650', 'Cyber World Communication', ''),
    (218, 'AS148970', 'FCI Information Systems Limited', ''),
    (219, 'AS149479', 'Techno Soft Communication', ''),
    (222, 'AS141977', 'Shuvo Internet Service', ''),
    (224, 'AS151978', 'Dhaka Cloud Network', ''),
    (225, 'AS152434', 'M/s Global Communication', ''),
    (226, 'AS139046', 'Ather Communication', ''),
    (229, 'AS142144', 'R F Online', ''),
    (234, 'AS148962', 'Link 2 Link BD', ''),
    (240, 'AS152341', 'Speed Zone Network', ''),
    (253, 'AS135293', 'City Information Network', ''),
    (257, 'AS152331', 'Eskay Network', ''),
    (264, 'AS140237', 'Speed Net BD', ''),
    (269, 'AS140243', 'S & A Network', ''),
    (274, 'AS152485', 'Fast Track Online', ''),
    (275, 'AS152504', 'Net Work BD', ''),
    (280, 'AS141982', 'J R Online', ''),
    (282, 'AS149021', 'City Network', ''),
    (286, 'AS148805', 'Prime Net BD', '')
]

def clean(s):
    s = s.lower()
    s = re.sub(r'[\(\)\.\,\-\_\'\"\/]', ' ', s)
    s = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation|m/s|ms|bd|bangladesh)\b', '', s)
    return ' '.join(s.split())

for r, asn, name, lic in unmatched_names:
    words = [w for w in clean(name).split() if len(w) > 3]
    matches = []
    for cid, text in dis_clients.items():
        c_text = clean(text.split(',')[0])
        # check if all words in c_text or vice versa
        if any(w in c_text for w in words):
            matches.append((cid, text))
    # Filter best matches
    best = []
    c_name = clean(name)
    for cid, text in matches:
        c_text = clean(text.split(',')[0])
        if c_name == c_text:
            best = [(cid, text, 100)]
            break
        # calculate overlap
        name_words = set(c_name.split())
        text_words = set(c_text.split())
        overlap = len(name_words & text_words)
        if overlap >= 1:
            best.append((cid, text, overlap))
    best.sort(key=lambda x: x[2], reverse=True)
    if best:
        print(f"Row {r} | {asn} | {name} -> {best[:2]}")
    else:
        print(f"Row {r} | {asn} | {name} -> NO MATCH")

