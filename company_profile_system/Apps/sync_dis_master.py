import os
import sys
import io

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding='utf-8')

import re
import json
import time
import requests
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from bs4 import BeautifulSoup
from datetime import datetime

# Path setups
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
EXCEL_OUTPUT = os.path.join(ROOT_DIR, "BTRC_DIS_Master_Database.xlsx")
CACHE_JSON = os.path.join(ROOT_DIR, "company_profile_system", "dis_all_operators_cache.json")

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import db_master
from dis_client import DISClient

def parse_contact_info(raw_text):
    """Parses Contact Personnel string into primary contact and full raw text."""
    if not raw_text:
        return "", "", "", "", ""
    
    # Try finding first contact
    m_name = re.search(r"Name:\s*([^\n\r]+)", raw_text)
    m_desig = re.search(r"Designation:\s*([^\n\r]+)", raw_text)
    m_phone = re.search(r"Mobile:\s*([^\n\r]+)", raw_text)
    m_email = re.search(r"Email:\s*([^\n\r]+)", raw_text)

    name = m_name.group(1).strip() if m_name else ""
    desig = m_desig.group(1).strip() if m_desig else ""
    phone = m_phone.group(1).strip() if m_phone else ""
    email = m_email.group(1).strip() if m_email else ""
    
    return name, desig, phone, email, raw_text.strip()

def parse_address_info(raw_text):
    """Parses NOC Address string into division, district, thana, and address."""
    if not raw_text:
        return "", "", "", "", ""
    
    m_div = re.search(r"Division:\s*([^\n\r]+)", raw_text)
    m_dist = re.search(r"District:\s*([^\n\r]+)", raw_text)
    m_thana = re.search(r"Thana:\s*([^\n\r]+)", raw_text)
    m_addr = re.search(r"Address:\s*([^\n\r]+)", raw_text)

    div = m_div.group(1).strip() if m_div else ""
    dist = m_dist.group(1).strip() if m_dist else ""
    thana = m_thana.group(1).strip() if m_thana else ""
    addr = m_addr.group(1).strip() if m_addr else ""

    full_clean = raw_text.replace("\n", " ").strip()
    return div, dist, thana, addr, full_clean

def load_cached_data():
    if os.path.exists(CACHE_JSON):
        try:
            with open(CACHE_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cached_data(data):
    os.makedirs(os.path.dirname(CACHE_JSON), exist_ok=True)
    with open(CACHE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def sync_dis_database(limit=None, batch_size=25):
    print("=" * 70)
    print("  BTRC DIS মাস্টার ডাটাবেজ ডাউনলোডার ও ক্যাশ সার্ভার সিঙ্ক")
    print(f"  লক্ষ্য ফাইল: {EXCEL_OUTPUT}")
    print("=" * 70)

    client = DISClient()
    if not client.ensure_authenticated():
        print("❌ DIS পোর্টালে লগইন ব্যর্থ হয়েছে। ক্রেডেনশিয়াল পরীক্ষা করুন।")
        return False

    # 1. Fetch all operators list from /ispByType
    print("📥 DIS পোর্টাল থেকে সকল আইএসপি অপারেটরের তালিকা লোড করা হচ্ছে...")
    isps = client.get_all_isps_by_type()
    total_isps = len(isps)
    print(f"✅ মোট {total_isps} টি আইএসপি অপারেটর পাওয়া গেছে।")

    if limit and limit < total_isps:
        isps = isps[:limit]
        print(f"ℹ️ টেস্ট রান হিসেবে প্রথম {len(isps)} টি অপারেটর প্রসেস করা হবে।")

    # Load existing cache & ASN mapping from DB
    cache = load_cached_data()
    existing_comps = db_master.get_all_companies()
    asn_by_name = {}
    for c in existing_comps:
        name_key = c.get('canonical_name', '').strip().lower()
        if name_key and c.get('asn'):
            asn_by_name[name_key] = c.get('asn')
            
    # Check form token from isp-operator-report
    r_form = client.session.get(f"{client.BASE_URL}/isp-operator-report", timeout=15)
    soup_form = BeautifulSoup(r_form.text, "html.parser")
    token_elem = soup_form.find("input", {"name": "_token"})
    if not token_elem:
        print("❌ DIS রিপোর্ট ফর্মের টোকেন পাওয়া যায়নি।")
        return False
    form_token = token_elem.get("value")

    # Targets to query
    targets = ['isp_type', 'total_upstream', 'noc_address', 'contact_personnel', 'ip_information']

    # Filter isps that need full details
    pending_isps = [item for item in isps if str(item['id']) not in cache]
    print(f"📊 ক্যাশে সংরক্ষিত আছে: {len(cache)} টি | নতুন ফেচ প্রয়োজন: {len(pending_isps)} টি")

    # Batch process
    processed_count = 0
    start_time = time.time()

    for i in range(0, len(pending_isps), batch_size):
        batch = pending_isps[i:i + batch_size]
        batch_ids = [str(item['id']) for item in batch]
        
        payload = [
            ('_token', form_token),
            ('type', ''),
            ('division_id', ''),
            ('district_id', ''),
            ('thana_id', ''),
            ('month', ''),
            ('year', '')
        ] + [('name[]', op_id) for op_id in batch_ids] + [('target[]', t) for t in targets]

        try:
            r_post = client.session.post(f"{client.BASE_URL}/isp-operator-report", data=payload, timeout=30)
            sp_res = BeautifulSoup(r_post.text, "html.parser")
            table = sp_res.find("table")
            
            if table:
                rows = table.find_all("tr")[1:] # skip header
                for row_idx, tr in enumerate(rows):
                    tds = [td.text.strip() for td in tr.find_all("td")]
                    if len(tds) >= 10 and row_idx < len(batch):
                        orig_item = batch[row_idx]
                        op_id = str(orig_item['id'])
                        
                        raw_name = tds[1].replace("\n(ISP)", "").strip()
                        lic_no = tds[2].strip() or orig_item.get('license_no', '')
                        cat = tds[3].strip() or orig_item.get('category', '')
                        raw_noc = tds[4].strip()
                        raw_contact = tds[5].strip()
                        up_mbps = tds[6].strip()
                        buy_price = tds[7].strip()
                        ipv4 = tds[8].strip()
                        ipv6 = tds[9].strip()

                        # Parse contact & address
                        c_name, c_desig, c_phone, c_email, c_full = parse_contact_info(raw_contact)
                        div, dist, thana, addr, noc_full = parse_address_info(raw_noc)

                        # Match ASN if available
                        matched_asn = asn_by_name.get(raw_name.lower()) or ""

                        cache[op_id] = {
                            "dis_operator_id": int(op_id),
                            "company_name": raw_name,
                            "category": cat,
                            "license_no": lic_no,
                            "asn": matched_asn,
                            "contact_name": c_name,
                            "contact_designation": c_desig,
                            "contact_phone": c_phone,
                            "contact_email": c_email,
                            "division": div,
                            "district": dist,
                            "thana": thana,
                            "noc_address": addr or noc_full,
                            "upstream_mbps": up_mbps,
                            "buying_price_bdt": buy_price,
                            "ipv4_declared": ipv4,
                            "ipv6_declared": ipv6,
                            "full_contact_raw": c_full,
                            "last_synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        processed_count += 1
            
            print(f"  --> প্রসেস হয়েছে: {len(cache)} / {total_isps} টি অপারেটর (চলতি ব্যাচ: {len(batch)} টি)...")
            save_cached_data(cache)
            time.sleep(0.5) # Gentle rate limiting

        except Exception as e:
            print(f"⚠️ ব্যাচ ফেচ ত্রুটি ({batch_ids[0]}..): {e}")
            time.sleep(2)
            continue

    total_time = round(time.time() - start_time, 1)
    print(f"\n🎉 ডাটা ফেচ সম্পন্ন! মোট রেকর্ড: {len(cache)} টি (সময় লেগেছে: {total_time} সেকেন্ড)")

    # 2. Write / Update Excel Master Database
    print(f"📊 এক্সেল মাস্টার ফাইল তৈরি করা হচ্ছে: {EXCEL_OUTPUT}")
    generate_excel_master(cache)
    
    # 3. Update SQLite Database
    sync_to_sqlite(cache)

    print("=" * 70)
    print("✅ বিটিআরসি DIS মাস্টার এক্সেল ডাটাবেজ সফলভাবে আপডেট ও সেভ হয়েছে!")
    print(f"📁 ফাইল পাথ: {EXCEL_OUTPUT}")
    print("=" * 70)
    return True

def generate_excel_master(cache: dict):
    wb = openpyxl.Workbook()
    ws_main = wb.active
    ws_main.title = "DIS Master Database"
    ws_main.views.sheetView[0].showGridLines = True

    # Header styling
    header_fill = PatternFill(start_color="001f54", end_color="001f54", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    border_thin = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB")
    )
    alt_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")

    headers = [
        "DIS Operator ID",
        "Company Name (Licensee)",
        "ISP Category",
        "License Number",
        "ASN",
        "Contact Person",
        "Designation",
        "Contact Mobile / Phone",
        "Contact Email",
        "Division",
        "District",
        "Thana / Upazilla",
        "NOC Full Address",
        "Approved Upstream (Mbps)",
        "Buying Price (BDT)",
        "IPv4 Declared",
        "IPv6 Declared",
        "Last Synced At"
    ]

    ws_main.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws_main.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = border_thin

    ws_main.row_dimensions[1].height = 28

    # Populate rows
    sorted_items = sorted(cache.values(), key=lambda x: (x.get("category", ""), x.get("company_name", "")))
    
    for row_idx, item in enumerate(sorted_items, start=2):
        row_data = [
            item.get("dis_operator_id", ""),
            item.get("company_name", ""),
            item.get("category", ""),
            item.get("license_no", ""),
            item.get("asn", ""),
            item.get("contact_name", ""),
            item.get("contact_designation", ""),
            item.get("contact_phone", ""),
            item.get("contact_email", ""),
            item.get("division", ""),
            item.get("district", ""),
            item.get("thana", ""),
            item.get("noc_address", ""),
            float(item.get("upstream_mbps") or 0) if str(item.get("upstream_mbps", "")).replace(".", "").isdigit() else item.get("upstream_mbps", ""),
            float(item.get("buying_price_bdt") or 0) if str(item.get("buying_price_bdt", "")).replace(".", "").isdigit() else item.get("buying_price_bdt", ""),
            item.get("ipv4_declared", ""),
            item.get("ipv6_declared", ""),
            item.get("last_synced_at", "")
        ]
        ws_main.append(row_data)

        # Style data cells
        for col_idx in range(1, len(row_data) + 1):
            cell = ws_main.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = border_thin
            if col_idx in [1, 3, 5, 16, 17, 18]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align

            if row_idx % 2 == 0:
                cell.fill = alt_fill

        ws_main.row_dimensions[row_idx].height = 20

    # Auto-filter on all headers
    last_col_letter = get_column_letter(len(headers))
    ws_main.auto_filter.ref = f"A1:{last_col_letter}{len(sorted_items) + 1}"
    ws_main.freeze_panes = "A2"

    # Auto-fit column widths
    for col in ws_main.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_main.column_dimensions[col_letter].width = max(min(max_len + 3, 40), 12)

    # Sheet 2: Summary Stats
    ws_sum = wb.create_sheet(title="Category Summary")
    ws_sum.views.sheetView[0].showGridLines = True
    
    ws_sum.append(["ISP Category", "Total Operators", "Total Declared Bandwidth (Mbps)"])
    for col_num in range(1, 4):
        c = ws_sum.cell(row=1, column=col_num)
        c.fill = header_fill
        c.font = header_font
        c.alignment = center_align

    # Calculate categories
    cats = {}
    for item in sorted_items:
        cat = item.get("category", "Unclassified")
        bw = float(item.get("upstream_mbps") or 0) if str(item.get("upstream_mbps", "")).replace(".", "").isdigit() else 0
        cats.setdefault(cat, {"count": 0, "bw": 0})
        cats[cat]["count"] += 1
        cats[cat]["bw"] += bw

    for cat_name, val in sorted(cats.items(), key=lambda x: x[1]["count"], reverse=True):
        ws_sum.append([cat_name, val["count"], val["bw"]])

    ws_sum.append(["Total", len(sorted_items), sum(v["bw"] for v in cats.values())])
    ws_sum.row_dimensions[1].height = 24
    ws_sum.column_dimensions["A"].width = 25
    ws_sum.column_dimensions["B"].width = 18
    ws_sum.column_dimensions["C"].width = 32

    wb.save(EXCEL_OUTPUT)

def sync_to_sqlite(cache: dict):
    """Updates SQLite master database with newly fetched DIS metadata."""
    print("🔄 SQLite মাস্টার ডাটাবেজ আপডেট করা হচ্ছে...")
    for item in cache.values():
        name = item.get("company_name", "").strip()
        asn = item.get("asn", "").strip()
        
        # If no ASN, construct placeholder key or match by name
        if not asn:
            asn_key = f"DIS{item.get('dis_operator_id')}"
        else:
            asn_key = asn

        record = {
            "asn": asn_key,
            "canonical_name": name,
            "license_status": item.get("category", "Unclassified"),
            "license_no": item.get("license_no", ""),
            "dis_operator_id": item.get("dis_operator_id"),
            "dis_operator_name": name,
            "dis_declared_upstream": "",
            "dis_declared_upstream_count": 0,
            "dis_bandwidth_mbps": str(item.get("upstream_mbps") or ""),
            "dis_noc_address": item.get("noc_address", ""),
            "dis_contact_person": item.get("contact_name", ""),
            "dis_contact_phone": item.get("contact_phone", ""),
            "dis_contact_email": item.get("contact_email", ""),
            "bgp_live_upstream": "",
            "bgp_live_upstream_count": 0,
            "bgp_observed_asns": "",
            "bgp_visibility_v4": "Active",
            "bgp_visibility_v6": "",
            "audit_discrepancy": "DIS মাস্টার ডাটাবেজ হতে সিঙ্ককৃত",
            "audit_status": "UNVERIFIED",
            "source_local_note": f"Synced from DIS on {item.get('last_synced_at', '')}",
            "ei_dashboard_status": "DIS_Master_Cached",
            "last_cached_at": item.get("last_synced_at", ""),
            "last_live_checked_at": "",
            "raw_json": json.dumps(item, ensure_ascii=False)
        }
        db_master.save_or_update_company(record)

    # Sync Standalone HTML Dashboard as well
    try:
        import build_html_dashboard
        build_html_dashboard.generate_html_dashboard()
    except Exception as e:
        print(f"Notice: HTML dashboard sync error: {e}")

if __name__ == "__main__":
    # If run directly with argument: python sync_dis_master.py [limit]
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    sync_dis_database(limit=limit_arg)
