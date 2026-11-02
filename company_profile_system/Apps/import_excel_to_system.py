import os
import sys
import json
import sqlite3
import openpyxl
from datetime import datetime

# UTF-8 Console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
EXCEL_PATH = os.path.join(ROOT_DIR, "BTRC_DIS_Master_Database.xlsx")
DB_PATH = os.path.join(CURRENT_DIR, "company_master_profile.db")

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import db_master
import build_html_dashboard

def import_excel_to_system():
    print("=" * 72)
    print("  BTRC_DIS_Master_Database.xlsx হতে সিস্টেমে ডাটা সিঙ্ক ও আপডেট")
    print(f"  উৎস ফাইল: {EXCEL_PATH}")
    print(f"  ডাটাবেজ:  {DB_PATH}")
    print("=" * 72)

    if not os.path.exists(EXCEL_PATH):
        print(f"❌ এক্সেল ফাইল পাওয়া যায়নি: {EXCEL_PATH}")
        return False

    print("📖 BTRC_DIS_Master_Database.xlsx লোড করা হচ্ছে...")
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    
    sheet_name = "DIS & BGP Master Database"
    if sheet_name not in wb.sheetnames:
        sheet_name = wb.sheetnames[0]
    ws = wb[sheet_name]

    headers = [str(c or '').strip() for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
    header_map = {h: idx for idx, h in enumerate(headers)}
    print(f"✅ এক্সেল ফাইলে মোট {len(headers)} টি কলাম পাওয়া গেছে।")

    # Connect to SQLite
    conn = db_master.get_connection()
    cur = conn.cursor()

    # Backup existing decisions and penalties
    cur.execute("SELECT COUNT(*) FROM commission_decisions")
    dec_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM company_penalties")
    pen_count = cur.fetchone()[0]
    print(f"ℹ️ সিস্টেমে সংরক্ষিত কমিশন সিদ্ধান্ত: {dec_count} টি | জরিমানা রেকর্ড: {pen_count} টি (অক্ষত থাকবে)")

    # Clear old company_profiles table
    cur.execute("DELETE FROM company_profiles")
    conn.commit()

    inserted_count = 0
    asn_count = 0
    live_up_count = 0
    seen_keys = set()

    # Helper to get value
    def get_val(row, header_name, default=""):
        idx = header_map.get(header_name)
        if idx is not None and idx < len(row):
            val = row[idx]
            return str(val).strip() if val is not None else default
        return default

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for r_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        dis_id = get_val(row, "[DIS] Operator ID")
        comp_name = get_val(row, "[DIS] Company Name (Licensee)")
        cat = get_val(row, "[DIS] ISP Category", "Unclassified")
        lic_no = get_val(row, "[DIS] License Number")
        contact_person = get_val(row, "[DIS] Contact Person")
        designation = get_val(row, "[DIS] Designation")
        contact_phone = get_val(row, "[DIS] Contact Mobile / Phone")
        contact_email = get_val(row, "[DIS] Contact Email")
        division = get_val(row, "[DIS] Division")
        district = get_val(row, "[DIS] District")
        thana = get_val(row, "[DIS] Thana / Upazilla")
        noc_addr = get_val(row, "[DIS] NOC Full Address")
        up_mbps = get_val(row, "[DIS] Approved Upstream (Mbps)")
        buying_price = get_val(row, "[DIS] Buying Price (BDT)")
        ipv4_dec = get_val(row, "[DIS] IPv4 Declared")
        ipv6_dec = get_val(row, "[DIS] IPv6 Declared")

        bgp_asn = get_val(row, "[BGP] Autonomous System (ASN)")
        bgp_as_name = get_val(row, "[BGP] AS Organization Name")
        bgp_as_class = get_val(row, "[BGP] AS Network Class")
        bgp_live_up = get_val(row, "[BGP] Live Upstream Providers")
        bgp_up_count = get_val(row, "[BGP] Live Upstream Count", "0")
        bgp_up_asns = get_val(row, "[BGP] Live Upstream ASNs")
        bgp_v4_vis = get_val(row, "[BGP] IPv4 Routing Visibility", "Inactive")
        bgp_v6_vis = get_val(row, "[BGP] IPv6 Routing Visibility", "Inactive")

        audit_status = get_val(row, "[AUDIT] Reconciliation Status", "UNVERIFIED")
        audit_note = get_val(row, "[AUDIT] Discrepancy Observation")
        last_synced = get_val(row, "[SYS] Last Updated At", now_str)

        if not comp_name:
            continue

        # Determine primary key ASN ensuring 100% uniqueness
        if bgp_asn and bgp_asn.upper().startswith("AS"):
            base_key = bgp_asn.upper()
            if base_key not in seen_keys:
                asn_key = base_key
            else:
                asn_key = f"{base_key}_{dis_id or r_idx}"
            asn_count += 1
        elif dis_id:
            asn_key = f"DIS{dis_id}"
            if asn_key in seen_keys:
                asn_key = f"{asn_key}_{r_idx}"
        else:
            asn_key = f"OP{r_idx}"

        seen_keys.add(asn_key)

        # Combine contact person & designation
        full_contact_p = f"{contact_person} ({designation})" if designation and contact_person else (contact_person or designation)

        # Count live upstreams
        try:
            up_int_count = int(float(bgp_up_count))
        except Exception:
            up_int_count = 0

        if bgp_live_up:
            live_up_count += 1

        # Format full address
        addr_parts = [p for p in [division, district, thana, noc_addr] if p and p != "N/A"]
        full_addr_str = ", ".join(addr_parts) if addr_parts else noc_addr

        # JSON raw data
        raw_dict = {
            "dis_operator_id": dis_id,
            "company_name": comp_name,
            "category": cat,
            "license_no": lic_no,
            "asn": bgp_asn,
            "as_org_name": bgp_as_name,
            "as_network_class": bgp_as_class,
            "contact_person": contact_person,
            "designation": designation,
            "contact_phone": contact_phone,
            "contact_email": contact_email,
            "division": division,
            "district": district,
            "thana": thana,
            "noc_address": noc_addr,
            "approved_upstream_mbps": up_mbps,
            "buying_price_bdt": buying_price,
            "ipv4_declared": ipv4_dec,
            "ipv6_declared": ipv6_dec,
            "bgp_live_upstreams": bgp_live_up,
            "bgp_live_upstream_count": up_int_count,
            "bgp_upstream_asns": bgp_up_asns,
            "bgp_v4_visibility": bgp_v4_vis,
            "bgp_v6_visibility": bgp_v6_vis,
            "audit_status": audit_status,
            "audit_note": audit_note
        }

        # Insert record into database
        cur.execute("""
        INSERT INTO company_profiles (
            asn, canonical_name, license_status, license_no,
            dis_operator_id, dis_operator_name, dis_declared_upstream,
            dis_declared_upstream_count, dis_bandwidth_mbps, dis_noc_address,
            dis_contact_person, dis_contact_phone, dis_contact_email,
            bgp_live_upstream, bgp_live_upstream_count, bgp_observed_asns,
            bgp_visibility_v4, bgp_visibility_v6, audit_discrepancy,
            audit_status, source_local_note, ei_dashboard_status,
            last_cached_at, last_live_checked_at, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            asn_key,
            comp_name,
            cat,
            lic_no,
            int(dis_id) if dis_id.isdigit() else None,
            comp_name,
            "", # declared upstream text
            0,
            up_mbps,
            full_addr_str,
            full_contact_p,
            contact_phone,
            contact_email,
            bgp_live_up.replace(", ", "\n"),
            up_int_count,
            bgp_up_asns,
            bgp_v4_vis,
            bgp_v6_vis,
            audit_note,
            audit_status,
            f"Synced from BTRC_DIS_Master_Database.xlsx (Row {r_idx})",
            "Master_Excel_Synchronized",
            last_synced or now_str,
            last_synced or now_str,
            json.dumps(raw_dict, ensure_ascii=False)
        ))
        inserted_count += 1

    conn.commit()
    conn.close()

    print(f"✅ SQLite ডাটাবেজ আপডেট সম্পন্ন! মোট ইনসার্ট হয়েছে: {inserted_count} টি অপারেটর")
    print(f"   • সক্রিয় BGP ASN সহ অপারেটর: {asn_count} টি")
    print(f"   • লাইভ BGP আপস্ট্রিম সহ অপারেটর: {live_up_count} টি")

    # Re-build Standalone HTML Dashboard
    print("🌐 ইন্টারেক্টিভ ড্যাশবোর্ড (BTRC_Company_Profile_Dashboard.html) পুনর্নির্মাণ করা হচ্ছে...")
    build_html_dashboard.generate_html_dashboard()

    print("=" * 72)
    print("🎉 অভিনন্দন! এক্সেল ফাইলের সমস্ত ডাটা সফলভাবে সিস্টেমে আপডেট করা হয়েছে।")
    print("=" * 72)
    return True

if __name__ == "__main__":
    import_excel_to_system()
