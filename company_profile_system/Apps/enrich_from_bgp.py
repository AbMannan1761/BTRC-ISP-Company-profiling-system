import os
import sys
import re
import json
import time
import urllib.request
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime

# Path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
EXCEL_OUTPUT = os.path.join(ROOT_DIR, "BTRC_DIS_Master_Database.xlsx")
DIS_CACHE = os.path.join(ROOT_DIR, "company_profile_system", "dis_all_operators_cache.json")
BGP_ASNS_CACHE = os.path.join(ROOT_DIR, "company_profile_system", "bgp_tools_bd_asns.json")
BGP_PROFILES_CACHE = os.path.join(ROOT_DIR, "company_profile_system", "bgp_profiles_cache.json")
NETWORK_STRUCTURE_EXCEL = os.path.join(ROOT_DIR, "Network structure, Orange Communication.xlsx")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import db_master
from bgp_client import BGPClient

def normalize_company_name(name: str) -> str:
    if not name:
        return ""
    s = name.lower()
    # Remove common ISP/telecom suffixes
    suffixes = [
        "limited", "ltd.", "ltd", "pvt.", "pvt", "private", "inc.", "inc",
        "technologies", "technology", "communications", "communication",
        "networks", "network", "online", "broadband", "internet",
        "services", "service", "telecom", "systems", "system",
        "(isp)", "isp", "co.", "co"
    ]
    for suf in suffixes:
        s = re.sub(r'\b' + re.escape(suf) + r'\b', '', s)
    # Remove non-alphanumeric
    s = re.sub(r'[^a-z0-9]', '', s)
    return s.strip()

def load_verified_asns_from_network_excel():
    """Loads existing verified ASNs from Network structure, Orange Communication.xlsx Sheet2"""
    verified = {}
    if os.path.exists(NETWORK_STRUCTURE_EXCEL):
        try:
            wb = openpyxl.load_workbook(NETWORK_STRUCTURE_EXCEL, data_only=True)
            if "Sheet2" in wb.sheetnames:
                sheet = wb["Sheet2"]
                for r in range(2, sheet.max_row + 1):
                    asn = sheet.cell(r, 2).value
                    name = sheet.cell(r, 3).value
                    if asn and name and str(asn).strip().startswith("AS"):
                        asn_clean = str(asn).strip()
                        name_clean = str(name).strip()
                        norm_k = normalize_company_name(name_clean)
                        if norm_k:
                            verified[norm_k] = (asn_clean, name_clean)
                        verified[name_clean.lower()] = (asn_clean, name_clean)
        except Exception as e:
            print(f"Notice reading network structure excel: {e}")
    return verified

def load_bgp_profiles_cache():
    if os.path.exists(BGP_PROFILES_CACHE):
        try:
            with open(BGP_PROFILES_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_bgp_profiles_cache(cache):
    with open(BGP_PROFILES_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def enrich_master_database():
    print("=" * 72)
    print("  BTRC DIS মাস্টার ডাটাবেজ - BGP.TOOLS ডাটা সমৃদ্ধকরণ ও অডিট")
    print("=" * 72)

    # 1. Load DIS operators cache
    if not os.path.exists(DIS_CACHE):
        print("❌ dis_all_operators_cache.json পাওয়া যায়নি। প্রথমে DIS সিঙ্ক চালান।")
        return False
    
    with open(DIS_CACHE, "r", encoding="utf-8") as f:
        dis_data = json.load(f)
    print(f"✅ DIS মাস্টার ক্যাশ থেকে {len(dis_data)} টি অপারেটর লোড করা হয়েছে।")

    # 2. Load BGP.tools Bangladesh ASNs
    if not os.path.exists(BGP_ASNS_CACHE):
        print("📥 bgp.tools হতে বাংলাদেশ ASNs ডাউনলোড করা হচ্ছে...")
        url = "https://bgp.tools/asns.csv"
        req = urllib.request.Request(url, headers={'User-Agent': 'BTRC-Audit/1.0'})
        import csv, io
        csv_data = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        reader = csv.DictReader(io.StringIO(csv_data))
        bd_asns = [r for r in reader if r.get('cc') == 'BD']
        with open(BGP_ASNS_CACHE, "w", encoding="utf-8") as f:
            json.dump(bd_asns, f, ensure_ascii=False, indent=2)
    else:
        with open(BGP_ASNS_CACHE, "r", encoding="utf-8") as f:
            bd_asns = json.load(f)
    print(f"✅ bgp.tools ডাটাবেজ হতে {len(bd_asns)} টি বাংলাদেশ ASN রেকর্ড লোড করা হয়েছে।")

    # 3. Load verified ASNs from Network Structure Excel
    verified_asns = load_verified_asns_from_network_excel()
    print(f"✅ অডিট এক্সেল হতে {len(verified_asns)} টি ভেরিফাইড ASN ম্যাপিং পাওয়া গেছে।")

    # Build bgp.tools lookup maps
    bgp_exact_map = {}
    bgp_norm_map = {}
    for item in bd_asns:
        asn = item.get("asn", "")
        name = item.get("name", "").strip()
        bgp_exact_map[name.lower()] = item
        norm_k = normalize_company_name(name)
        if len(norm_k) >= 3 and norm_k not in bgp_norm_map:
            bgp_norm_map[norm_k] = item

    # 4. Match DIS companies with BGP.tools ASNs
    bgp_client = BGPClient()
    bgp_cache = load_bgp_profiles_cache()
    
    matched_asn_count = 0
    enriched_operators = []

    print("🔍 DIS কোম্পানির নামের সাথে BGP.tools ASN ম্যাপিং ও রুট অ্যানালাইসিস শুরু হচ্ছে...")

    for op_id, op in dis_data.items():
        comp_name = op.get("company_name", "").strip()
        norm_name = normalize_company_name(comp_name)
        
        assigned_asn = ""
        as_org_name = ""
        as_class = ""

        # Priority 1: Check verified network structure excel
        if norm_name in verified_asns:
            assigned_asn = verified_asns[norm_name][0]
            as_org_name = verified_asns[norm_name][1]
        elif comp_name.lower() in verified_asns:
            assigned_asn = verified_asns[comp_name.lower()][0]
            as_org_name = verified_asns[comp_name.lower()][1]
        # Priority 2: Check bgp.tools exact name match
        elif comp_name.lower() in bgp_exact_map:
            bgp_item = bgp_exact_map[comp_name.lower()]
            assigned_asn = bgp_item["asn"]
            as_org_name = bgp_item["name"]
            as_class = bgp_item.get("class", "")
        # Priority 3: Check bgp.tools normalized name match
        elif norm_name in bgp_norm_map:
            bgp_item = bgp_norm_map[norm_name]
            assigned_asn = bgp_item["asn"]
            as_org_name = bgp_item["name"]
            as_class = bgp_item.get("class", "")

        # If ASN found, fetch live BGP routing & upstreams
        bgp_upstreams = []
        bgp_up_asns = []
        bgp_v4_vis = "No ASN / Inactive"
        bgp_v6_vis = "No ASN / Inactive"
        audit_status = "UNVERIFIED"
        audit_note = "কোনো সক্রিয় ASN ম্যাপ হয়নি"

        if assigned_asn:
            matched_asn_count += 1
            asn_clean = assigned_asn.strip()
            
            # Check BGP cache
            if asn_clean in bgp_cache:
                bgp_info = bgp_cache[asn_clean]
            else:
                try:
                    bgp_info = bgp_client.get_live_bgp_profile(asn_clean)
                    if bgp_info:
                        bgp_cache[asn_clean] = bgp_info
                except Exception as e:
                    bgp_info = None

            if bgp_info:
                bgp_upstreams = bgp_info.get("live_upstreams", [])
                bgp_up_asns = bgp_info.get("upstream_asns", [])
                bgp_v4_vis = bgp_info.get("ipv4_visibility", "Inactive")
                bgp_v6_vis = bgp_info.get("ipv6_visibility", "Inactive")

                # Audit reconciliation
                dis_bw = str(op.get("upstream_mbps") or "").strip()
                if bgp_upstreams:
                    audit_status = "MATCH"
                    audit_note = f"BGP-তে {len(bgp_upstreams)} টি আপস্ট্রিম সক্রিয় রয়েছে।"
                else:
                    audit_status = "UNVERIFIED"
                    audit_note = "ASN রয়েছে কিন্তু বর্তমানে কোনো সক্রিয় BGP রুট পাওয়া যায়নি।"

        enriched_record = {
            # DIS Fields
            "dis_operator_id": op.get("dis_operator_id", op_id),
            "dis_company_name": comp_name,
            "dis_category": op.get("category", ""),
            "dis_license_no": op.get("license_no", ""),
            "dis_contact_person": op.get("contact_name", ""),
            "dis_designation": op.get("contact_designation", ""),
            "dis_contact_phone": op.get("contact_phone", ""),
            "dis_contact_email": op.get("contact_email", ""),
            "dis_division": op.get("division", ""),
            "dis_district": op.get("district", ""),
            "dis_thana": op.get("thana", ""),
            "dis_noc_address": op.get("noc_address", ""),
            "dis_upstream_mbps": op.get("upstream_mbps", ""),
            "dis_buying_price": op.get("buying_price_bdt", ""),
            "dis_ipv4": op.get("ipv4_declared", ""),
            "dis_ipv6": op.get("ipv6_declared", ""),

            # BGP Fields
            "bgp_asn": assigned_asn,
            "bgp_as_name": as_org_name,
            "bgp_as_class": as_class,
            "bgp_live_upstreams": ", ".join(bgp_upstreams),
            "bgp_live_upstream_count": len(bgp_upstreams),
            "bgp_upstream_asns": ", ".join(bgp_up_asns),
            "bgp_v4_visibility": bgp_v4_vis,
            "bgp_v6_visibility": bgp_v6_vis,

            # Audit & System Fields
            "audit_status": audit_status,
            "audit_note": audit_note,
            "last_synced": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        enriched_operators.append(enriched_record)

    save_bgp_profiles_cache(bgp_cache)
    print(f"🎉 ম্যাপিং সম্পন্ন! মোট {len(enriched_operators)} টি কোম্পানির মধ্যে {matched_asn_count} টি কোম্পানির BGP ASN সফলভাবে পাওয়া গেছে।")

    # 5. Write enriched data into BTRC_DIS_Master_Database.xlsx
    print(f"📊 এক্সেল ফাইলে সোর্স লেবেলযুক্ত হেডার সহ ডাটা লেখা হচ্ছে: {EXCEL_OUTPUT}")
    write_enriched_excel(enriched_operators)

    # 6. Sync SQLite Database & HTML Dashboard
    sync_enriched_to_sqlite(enriched_operators)

    print("=" * 72)
    print("✅ BTRC_DIS_Master_Database.xlsx সফলভাবে এনরিচ ও সোর্স লেবেল সহ সেভ হয়েছে!")
    print("=" * 72)
    return True

def write_enriched_excel(records):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DIS & BGP Master Database"
    ws.views.sheetView[0].showGridLines = True

    # Header styling definitions
    dis_fill = PatternFill(start_color="001F54", end_color="001F54", fill_type="solid")     # Deep Navy
    bgp_fill = PatternFill(start_color="0353A4", end_color="0353A4", fill_type="solid")     # Royal Blue
    audit_fill = PatternFill(start_color="581C87", end_color="581C87", fill_type="solid")   # Royal Purple
    sys_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")     # Slate Dark Gray

    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center")
    border_thin = Border(
        left=Side(style="thin", color="E5E7EB"),
        right=Side(style="thin", color="E5E7EB"),
        top=Side(style="thin", color="E5E7EB"),
        bottom=Side(style="thin", color="E5E7EB")
    )
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    # 26 Columns with explicit Source in Headline
    columns = [
        # DIS Columns (1-16)
        ("[DIS] Operator ID", "dis_operator_id", dis_fill, 14, center_align),
        ("[DIS] Company Name (Licensee)", "dis_company_name", dis_fill, 32, left_align),
        ("[DIS] ISP Category", "dis_category", dis_fill, 18, center_align),
        ("[DIS] License Number", "dis_license_no", dis_fill, 28, left_align),
        ("[DIS] Contact Person", "dis_contact_person", dis_fill, 22, left_align),
        ("[DIS] Designation", "dis_designation", dis_fill, 16, left_align),
        ("[DIS] Contact Mobile / Phone", "dis_contact_phone", dis_fill, 20, center_align),
        ("[DIS] Contact Email", "dis_contact_email", dis_fill, 24, left_align),
        ("[DIS] Division", "dis_division", dis_fill, 14, center_align),
        ("[DIS] District", "dis_district", dis_fill, 14, center_align),
        ("[DIS] Thana / Upazilla", "dis_thana", dis_fill, 16, center_align),
        ("[DIS] NOC Full Address", "dis_noc_address", dis_fill, 35, left_align),
        ("[DIS] Approved Upstream (Mbps)", "dis_upstream_mbps", dis_fill, 18, center_align),
        ("[DIS] Buying Price (BDT)", "dis_buying_price", dis_fill, 18, center_align),
        ("[DIS] IPv4 Declared", "dis_ipv4", dis_fill, 14, center_align),
        ("[DIS] IPv6 Declared", "dis_ipv6", dis_fill, 14, center_align),

        # BGP Columns (17-23)
        ("[BGP] Autonomous System (ASN)", "bgp_asn", bgp_fill, 16, center_align),
        ("[BGP] AS Organization Name", "bgp_as_name", bgp_fill, 28, left_align),
        ("[BGP] AS Network Class", "bgp_as_class", bgp_fill, 16, center_align),
        ("[BGP] Live Upstream Providers", "bgp_live_upstreams", bgp_fill, 36, left_align),
        ("[BGP] Live Upstream Count", "bgp_live_upstream_count", bgp_fill, 16, center_align),
        ("[BGP] Live Upstream ASNs", "bgp_upstream_asns", bgp_fill, 24, left_align),
        ("[BGP] IPv4 Routing Visibility", "bgp_v4_visibility", bgp_fill, 20, center_align),
        ("[BGP] IPv6 Routing Visibility", "bgp_v6_visibility", bgp_fill, 20, center_align),

        # Audit Columns (24-25)
        ("[AUDIT] Reconciliation Status", "audit_status", audit_fill, 18, center_align),
        ("[AUDIT] Discrepancy Observation", "audit_note", audit_fill, 32, left_align),

        # System Column (26)
        ("[SYS] Last Updated At", "last_synced", sys_fill, 20, center_align)
    ]

    # Write Headers
    header_titles = [c[0] for c in columns]
    ws.append(header_titles)
    ws.row_dimensions[1].height = 28

    for col_idx, col_def in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = col_def[2] # Specific source color
        cell.font = header_font
        cell.alignment = center_align
        cell.border = border_thin
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_def[3]

    # Sort: First companies with ASN, then by Category, then by Name
    sorted_records = sorted(
        records,
        key=lambda r: (
            0 if r.get("bgp_asn") else 1,
            r.get("dis_category", ""),
            r.get("dis_company_name", "")
        )
    )

    # Populate Data Rows
    for row_idx, r in enumerate(sorted_records, start=2):
        row_values = []
        for col_def in columns:
            key = col_def[1]
            val = r.get(key, "")
            # Numeric conversion if suitable
            if key in ["dis_upstream_mbps", "dis_buying_price"]:
                if str(val).replace(".", "").isdigit():
                    val = float(val)
            row_values.append(val)

        ws.append(row_values)

        for col_idx, col_def in enumerate(columns, start=1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = border_thin
            cell.alignment = col_def[4]

            if row_idx % 2 == 0:
                cell.fill = alt_fill

            # Highlight ASN and Match status
            if col_def[1] == "bgp_asn" and cell.value:
                cell.font = Font(name="Calibri", size=10, bold=True, color="0284C7")
            elif col_def[1] == "audit_status":
                if cell.value == "MATCH":
                    cell.fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color="166534")
                elif cell.value == "MISMATCH":
                    cell.fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color="991B1B")

        ws.row_dimensions[row_idx].height = 20

    # Apply Auto-Filter & Freeze Panes
    last_col_letter = get_column_letter(len(columns))
    ws.auto_filter.ref = f"A1:{last_col_letter}{len(sorted_records) + 1}"
    ws.freeze_panes = "C2" # Freeze ID and Company Name columns horizontally, and row 1 vertically

    # Sheet 2: Category & BGP Summary Sheet
    ws_sum = wb.create_sheet(title="Category & BGP Summary")
    ws_sum.views.sheetView[0].showGridLines = True
    
    summary_headers = ["ISP Category", "Total DIS Operators", "With BGP ASN", "Coverage %", "Total Bandwidth (Mbps)"]
    ws_sum.append(summary_headers)
    for col_n in range(1, len(summary_headers) + 1):
        c = ws_sum.cell(row=1, column=col_n)
        c.fill = dis_fill
        c.font = header_font
        c.alignment = center_align

    # Calculate metrics
    stats = {}
    for r in sorted_records:
        cat = r.get("dis_category", "Unclassified") or "Unclassified"
        stats.setdefault(cat, {"total": 0, "with_asn": 0, "bw": 0})
        stats[cat]["total"] += 1
        if r.get("bgp_asn"):
            stats[cat]["with_asn"] += 1
        try:
            stats[cat]["bw"] += float(r.get("dis_upstream_mbps") or 0)
        except Exception:
            pass

    for cat_name, s in sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True):
        cov = f"{(s['with_asn'] / s['total'] * 100):.1f}%" if s['total'] > 0 else "0%"
        ws_sum.append([cat_name, s["total"], s["with_asn"], cov, round(s["bw"], 2)])

    total_ops = len(sorted_records)
    total_asns = sum(s["with_asn"] for s in stats.values())
    total_cov = f"{(total_asns / total_ops * 100):.1f}%" if total_ops > 0 else "0%"
    total_bw = round(sum(s["bw"] for s in stats.values()), 2)
    ws_sum.append(["Total", total_ops, total_asns, total_cov, total_bw])

    ws_sum.row_dimensions[1].height = 24
    ws_sum.column_dimensions["A"].width = 25
    ws_sum.column_dimensions["B"].width = 22
    ws_sum.column_dimensions["C"].width = 18
    ws_sum.column_dimensions["D"].width = 16
    ws_sum.column_dimensions["E"].width = 28

    wb.save(EXCEL_OUTPUT)

def sync_enriched_to_sqlite(records):
    print("🔄 SQLite ডাটাবেজ এবং ইন্টারেক্টিভ ড্যাশবোর্ড আপডেট করা হচ্ছে...")
    for r in records:
        asn_key = r.get("bgp_asn") or f"DIS{r.get('dis_operator_id')}"
        db_record = {
            "asn": asn_key,
            "canonical_name": r.get("dis_company_name", ""),
            "license_status": r.get("dis_category", "Unclassified"),
            "license_no": r.get("dis_license_no", ""),
            "dis_operator_id": r.get("dis_operator_id"),
            "dis_operator_name": r.get("dis_company_name", ""),
            "dis_declared_upstream": "",
            "dis_declared_upstream_count": 0,
            "dis_bandwidth_mbps": str(r.get("dis_upstream_mbps") or ""),
            "dis_noc_address": r.get("dis_noc_address", ""),
            "dis_contact_person": r.get("dis_contact_person", ""),
            "dis_contact_phone": r.get("dis_contact_phone", ""),
            "dis_contact_email": r.get("dis_contact_email", ""),
            "bgp_live_upstream": r.get("bgp_live_upstreams", "").replace(", ", "\n"),
            "bgp_live_upstream_count": r.get("bgp_live_upstream_count", 0),
            "bgp_observed_asns": r.get("bgp_upstream_asns", ""),
            "bgp_visibility_v4": r.get("bgp_v4_visibility", "Inactive"),
            "bgp_visibility_v6": r.get("bgp_v6_visibility", "Inactive"),
            "audit_discrepancy": r.get("audit_note", ""),
            "audit_status": r.get("audit_status", "UNVERIFIED"),
            "source_local_note": f"Enriched from DIS & BGP on {r.get('last_synced')}",
            "ei_dashboard_status": "Enriched",
            "last_cached_at": r.get("last_synced", ""),
            "last_live_checked_at": r.get("last_synced", ""),
            "raw_json": json.dumps(r, ensure_ascii=False)
        }
        db_master.save_or_update_company(db_record)

    try:
        import build_html_dashboard
        build_html_dashboard.generate_html_dashboard()
    except Exception as e:
        print(f"Notice HTML rebuild: {e}")

if __name__ == "__main__":
    enrich_master_database()
