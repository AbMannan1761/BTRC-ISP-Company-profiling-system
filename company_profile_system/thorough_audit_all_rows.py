import openpyxl
import json
import re
from difflib import SequenceMatcher
from bs4 import BeautifulSoup

# Load DIS clients list from orange_dis_report.html
with open('company_profile_system/sample/orange_dis_report.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')
    client_sel = soup.find('select', {'id': 'client'})
    dis_clients = {opt.get('value'): opt.text.strip() for opt in client_sel.find_all('option') if opt.get('value')}

# Load Master DB
wb_master = openpyxl.load_workbook('BTRC_DIS_Master_Database.xlsx', data_only=True)
ws_master = wb_master['DIS & BGP Master Database']

master_records = []
for r in range(2, ws_master.max_row + 1):
    op_id = ws_master.cell(r, 1).value
    name = ws_master.cell(r, 2).value
    category = ws_master.cell(r, 3).value
    lic_no = ws_master.cell(r, 4).value
    asn = ws_master.cell(r, 17).value
    master_records.append({
        'op_id': str(op_id).strip() if op_id else '',
        'name': str(name).strip() if name else '',
        'category': str(category).strip() if category else '',
        'lic_no': str(lic_no).strip() if lic_no else '',
        'asn': str(asn).strip() if asn else ''
    })

wb = openpyxl.load_workbook('Network structure, Orange Communication_updated.xlsx', data_only=True)
ws = wb['Sheet2']

def clean(s):
    if not s:
        return ''
    s = s.lower()
    s = re.sub(r'[\(\)\.\,\-\_\'\"\/]', ' ', s)
    s = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation|m/s|ms|bd|bangladesh|t/a|plc|internet|service|services|communication|communications|network|networks|telecom|telecommunication|broadband)\b', '', s)
    return ' '.join(s.split())

def extract_trade_name(name):
    m = re.search(r'[\s\b]t/a[\s\b](.+)$', name, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

NON_ISPS = {
    'AS58717', 'AS58682', 'AS137491', 'AS150178', 'AS150774', 'AS133477',
    'AS139303', 'AS137045', 'AS139233', 'AS138203', 'AS141423', 'AS151488'
}

def resolve_operator_definitive(asn, name, lic):
    if asn in NON_ISPS:
        return None, "NON_ISP", "Non-ISP Entity"
        
    c_name = clean(name)
    t_name = extract_trade_name(name)
    c_tname = clean(t_name) if t_name else ''
    
    # Priority 1: Match by ASN from master records, BUT if multiple or single, VERIFY NAME SCORE!
    if asn:
        matching_by_asn = [mr for mr in master_records if mr['asn'] == asn]
        if matching_by_asn:
            # Score each candidate against c_name (or trade name)
            scored = []
            for mr in matching_by_asn:
                s_name = SequenceMatcher(None, c_name, clean(mr['name'])).ratio()
                s_trade = SequenceMatcher(None, c_tname, clean(mr['name'])).ratio() if c_tname else 0
                best_s = max(s_name, s_trade)
                scored.append((mr, best_s))
            scored.sort(key=lambda x: x[1], reverse=True)
            # If the best score is reasonable (>= 0.5) or if it's the only one and >= 0.4
            if scored[0][1] >= 0.5:
                mr = scored[0][0]
                return mr['op_id'], dis_clients.get(mr['op_id'], mr['name']), f"ASN_VerifiedName(s={scored[0][1]:.2f})"

    # Priority 2: Exact cleaned name in DIS clients
    target_names = [c_name]
    if c_tname:
        target_names.insert(0, c_tname)
        
    for tn in target_names:
        if not tn: continue
        matches = []
        for cid, text in dis_clients.items():
            op_part = clean(text.split(',')[0].strip())
            if op_part == tn:
                matches.append((cid, text))
        if len(matches) == 1:
            return matches[0][0], matches[0][1], "DIS_ExactCleanName"
        elif len(matches) > 1:
            # disambiguate by license category
            if lic:
                for cid, text in matches:
                    # check master record
                    for mr in master_records:
                        if mr['op_id'] == cid and lic.lower() in mr['category'].lower():
                            return cid, text, "DIS_ExactCleanName+Cat"
            return matches[0][0], matches[0][1], "DIS_ExactCleanName_First"

    # Priority 3: Fuzzy in DIS clients
    for tn in target_names:
        if len(tn) > 3:
            fuzzy = []
            for cid, text in dis_clients.items():
                op_part = clean(text.split(',')[0].strip())
                if tn in op_part or op_part in tn:
                    s = SequenceMatcher(None, tn, op_part).ratio()
                    fuzzy.append((cid, text, s))
            if fuzzy:
                fuzzy.sort(key=lambda x: x[2], reverse=True)
                if fuzzy[0][2] >= 0.7:
                    return fuzzy[0][0], fuzzy[0][1], f"DIS_Fuzzy(s={fuzzy[0][2]:.2f})"

    return None, None, "Unresolved"

# Audit all 294 rows
audit_results = []
for r in range(2, ws.max_row + 1):
    sl = ws.cell(r, 1).value
    asn = str(ws.cell(r, 2).value or '').strip()
    name = str(ws.cell(r, 3).value or '').strip()
    lic = str(ws.cell(r, 4).value or '').strip()
    curr_dis = ws.cell(r, 5).value
    
    if not name and not asn:
        continue
        
    op_id, client_text, mtype = resolve_operator_definitive(asn, name, lic)
    audit_results.append({
        'row': r,
        'sl': sl,
        'asn': asn,
        'name': name,
        'lic': lic,
        'op_id': op_id,
        'client_text': client_text,
        'mtype': mtype,
        'curr_dis': curr_dis
    })

print(f"Total rows evaluated: {len(audit_results)}")
resolved = [a for a in audit_results if a['op_id']]
print(f"Resolved to valid DIS Operator ID: {len(resolved)}")
print(f"Non-ISP: {len([a for a in audit_results if a['client_text'] == 'NON_ISP'])}")
print(f"Unresolved: {len([a for a in audit_results if not a['op_id'] and a['client_text'] != 'NON_ISP'])}")

# Check row 295
r295 = [a for a in audit_results if a['row'] == 295][0]
print(f"\nRow 295: {r295['name']} -> ID: {r295['op_id']} | Text: {r295['client_text']} | Type: {r295['mtype']}")

