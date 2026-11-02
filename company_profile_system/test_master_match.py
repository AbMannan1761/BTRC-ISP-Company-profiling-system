import openpyxl
import re
import difflib

# Load Sheet2
wb_orange = openpyxl.load_workbook('Network structure, Orange Communication_updated.xlsx', data_only=True)
ws_orange = wb_orange['Sheet2']

# Load Master DB
wb_master = openpyxl.load_workbook('BTRC_DIS_Master_Database.xlsx', data_only=True)
ws_master = wb_master['DIS & BGP Master Database']

master_by_asn = {}
master_by_id = {}
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
    if entry['op_id']:
        master_by_id[entry['op_id']] = entry
    master_by_name.append(entry)

print(f"Master records: {len(master_by_name)}, with ASN: {len(master_by_asn)}")

def clean_name(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[\(\)\.\,\-\_\'\"\/]', ' ', s)
    s = re.sub(r'\b(ltd|limited|pvt|co|corp|corporation|m/s|ms|bd|bangladesh)\b', '', s)
    return ' '.join(s.split())

matched = []
unmatched = []

for r in range(2, 296):
    sl = ws_orange.cell(r, 1).value
    asn = ws_orange.cell(r, 2).value
    name = ws_orange.cell(r, 3).value
    lic = ws_orange.cell(r, 4).value
    dis_val = ws_orange.cell(r, 5).value
    
    asn_str = str(asn).strip() if asn else ''
    name_str = str(name).strip() if name else ''
    lic_str = str(lic).strip() if lic else ''
    
    found = None
    match_type = ''
    
    # 1. Match by ASN
    if asn_str and asn_str in master_by_asn:
        found = master_by_asn[asn_str]
        match_type = 'ASN'
    
    # 2. Match by exact cleaned name + category
    if not found:
        c_name = clean_name(name_str)
        for m in master_by_name:
            if clean_name(m['name']) == c_name:
                found = m
                match_type = 'CleanName'
                break
                
    # 3. Match by partial name
    if not found:
        c_name = clean_name(name_str)
        if len(c_name) > 3:
            candidates = []
            for m in master_by_name:
                mc_name = clean_name(m['name'])
                if c_name in mc_name or mc_name in c_name:
                    candidates.append(m)
            if len(candidates) == 1:
                found = candidates[0]
                match_type = 'PartialSingle'
            elif len(candidates) > 1 and lic_str:
                for c in candidates:
                    if lic_str.lower() in c['category'].lower() or c['category'].lower() in lic_str.lower():
                        found = c
                        match_type = 'PartialCategory'
                        break
                        
    if found:
        matched.append((r, sl, asn_str, name_str, lic_str, found['op_id'], found['name'], match_type))
    else:
        unmatched.append((r, sl, asn_str, name_str, lic_str))

print(f"Matched: {len(matched)} / 294")
print(f"Unmatched: {len(unmatched)}")
print("\nSample unmatched:")
for u in unmatched[:25]:
    print(u)

