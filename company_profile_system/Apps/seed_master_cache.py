import openpyxl
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import db_master
from reconciliation import reconcile_upstreams

def seed_cache():
    print("--- Starting Master Cache Seeding ---")
    
    # 1. Load DIS operators cache
    dis_json_path = os.path.join(r"C:\Users\mannan\.gemini\antigravity-ide\brain\a11f9a4e-ec52-4bd3-a73c-8d792d758042\scratch", "dis_operators.json")
    dis_ops = []
    if os.path.exists(dis_json_path):
        with open(dis_json_path, "r", encoding="utf-8") as f:
            dis_ops = json.load(f)
    print(f"Loaded {len(dis_ops)} DIS operators from cache.")
    
    # Map by name
    dis_by_name = {o['name'].lower().strip(): o for o in dis_ops}
    
    # 2. Load Excel workbook
    excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Network structure, Orange Communication.xlsx")
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb["Sheet2"]
    
    seeded_count = 0
    
    for r in range(2, sheet.max_row + 1):
        asn = sheet.cell(r, 2).value
        name = sheet.cell(r, 3).value
        status = sheet.cell(r, 4).value
        up_dis = sheet.cell(r, 5).value
        up_hurr = sheet.cell(r, 6).value
        
        if not name or not str(name).strip():
            continue
            
        asn_str = str(asn).strip() if asn else ""
        name_str = str(name).strip()
        status_str = str(status).strip() if status else "Unclassified"
        up_dis_str = str(up_dis).strip() if up_dis else ""
        up_hurr_str = str(up_hurr).strip() if up_hurr else ""
        
        # Match DIS operator
        dis_match = dis_by_name.get(name_str.lower())
        dis_id = dis_match.get("id") if dis_match else None
        dis_lic = dis_match.get("license_no", "") if dis_match else ""
        dis_name = dis_match.get("name", "") if dis_match else ""
        
        # Parse Upstream lists
        dis_up_list = [u.strip() for u in up_dis_str.split("\n") if u.strip()] if up_dis_str else []
        hurr_up_list = [u.strip() for u in re_split_upstreams(up_hurr_str)] if up_hurr_str else []
        
        # Reconcile audit
        audit = reconcile_upstreams(dis_up_list, hurr_up_list)
        
        # Build record
        record = {
            "asn": asn_str,
            "canonical_name": name_str,
            "license_status": status_str,
            "license_no": dis_lic,
            "dis_operator_id": dis_id,
            "dis_operator_name": dis_name or name_str,
            "dis_declared_upstream": "\n".join(dis_up_list),
            "dis_declared_upstream_count": len(dis_up_list),
            "dis_bandwidth_mbps": "",
            "dis_noc_address": "",
            "dis_contact_person": "",
            "dis_contact_phone": "",
            "dis_contact_email": "",
            "bgp_live_upstream": "\n".join(hurr_up_list),
            "bgp_live_upstream_count": len(hurr_up_list),
            "bgp_observed_asns": "",
            "bgp_visibility_v4": "Active" if hurr_up_list else "Inactive",
            "bgp_visibility_v6": "",
            "audit_discrepancy": audit["discrepancy_desc"],
            "audit_status": audit["audit_status"],
            "source_local_note": f"Imported from Network structure Row {r}",
            "ei_dashboard_status": "Synchronized",
            "last_cached_at": "",
            "last_live_checked_at": "",
            "raw_json": json.dumps({"source_row": r})
        }
        
        db_master.save_or_update_company(record)
        seeded_count += 1
        
    print(f"Successfully seeded {seeded_count} company profiles into master SQLite cache!")
    
    stats = db_master.get_stats()
    print("Database Stats:", stats)

def re_split_upstreams(text):
    # Splits by newline or comma
    lines = text.split("\n")
    res = []
    for l in lines:
        for p in l.split(","):
            val = p.strip()
            if val and val != "NA":
                res.append(val)
    return res

if __name__ == "__main__":
    seed_cache()
