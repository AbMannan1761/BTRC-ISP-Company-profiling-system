import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
import os
import re

def sanitize_filename(name: str):
    s = re.sub(r'[\\/*?:"<>|]', "", name)
    s = re.sub(r'\s+', "_", s).strip("_")
    return s

def export_single_company(profile: dict, output_dir: str = None) -> str:
    """
    Exports a single company profile to an Excel file with the exact naming:
    [Company_Name]_[Category]_[YYYY-MM-DD_HH-MM].xlsx
    """
    if not output_dir:
        output_dir = os.path.dirname(os.path.dirname(__file__))
    
    comp_name = sanitize_filename(profile.get("canonical_name", "Company"))
    category = sanitize_filename(profile.get("license_status", "Unclassified") or "Unclassified")
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d_%I-%M%p")
    
    filename = f"{comp_name}_{category}_{timestamp_str}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Company Profile"
    ws.views.sheetView[0].showGridLines = True
    
    # Styles
    navy_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
    header_fill = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")
    sub_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    mismatch_fill = PatternFill(start_color="FFF5F5", end_color="FFF5F5", fill_type="solid")
    ok_fill = PatternFill(start_color="F0FFF4", end_color="F0FFF4", fill_type="solid")
    
    title_font = Font(name="Segoe UI", size=15, bold=True, color="FFFFFF")
    white_bold = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    sub_font = Font(name="Segoe UI", size=10, italic=True, color="4A5568")
    bold_font = Font(name="Segoe UI", size=10, bold=True)
    normal_font = Font(name="Segoe UI", size=10)
    alert_font = Font(name="Segoe UI", size=10, bold=True, color="C53030")
    ok_font = Font(name="Segoe UI", size=10, bold=True, color="22543D")
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E0'),
        right=Side(style='thin', color='CBD5E0'),
        top=Side(style='thin', color='CBD5E0'),
        bottom=Side(style='thin', color='CBD5E0')
    )
    
    # Banner
    ws.merge_cells("A1:F1")
    top_cell = ws["A1"]
    top_cell.value = f"বাংলাদেশ টেলিযোগাযোগ নিয়ন্ত্রণ কমিশন (BTRC) - কোম্পানি প্রোফাইল ও নেটওয়ার্ক অডিট"
    top_cell.font = title_font
    top_cell.fill = navy_fill
    top_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36
    
    # Metadata Sub-header
    ws.merge_cells("A2:F2")
    sub_cell = ws["A2"]
    sub_cell.value = f"কোম্পানি: {profile.get('canonical_name')}  |  ক্যাটাগরি: {profile.get('license_status')}  |  ডাউনলোডের তারিখ ও সময়: {now.strftime('%d-%m-%Y %I:%M %p')}"
    sub_cell.font = Font(name="Segoe UI", size=11, bold=True, color="1A202C")
    sub_cell.fill = sub_fill
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 24
    
    row = 4
    
    # Section 1: Core Company Profile
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "১. সাধারণ পরিচিতি ও বিটিআরসি লাইসেন্স তথ্য (Core Licensing & Profile)"
    ws[f"A{row}"].font = white_bold
    ws[f"A{row}"].fill = header_fill
    ws.row_dimensions[row].height = 22
    row += 1
    
    info_rows = [
        ("প্রতিষ্ঠানের নাম (Canonical Name)", profile.get("canonical_name", ""), "অটোনমাস সিস্টেম নম্বর (ASN)", profile.get("asn", "")),
        ("বিটিআরসি লাইসেন্স নম্বর", profile.get("license_no", ""), "লাইসেন্স ধরণ (Category)", profile.get("license_status", "")),
        ("DIS সিস্টেম নাম", profile.get("dis_operator_name", ""), "ঘোষিত ব্যান্ডউইথ (Mbps)", profile.get("dis_bandwidth_mbps", "")),
        ("যোগাযোগকারী ব্যক্তি (Contact)", profile.get("dis_contact_person", ""), "মোবাইল নম্বর", profile.get("dis_contact_phone", "")),
        ("ইমেইল ঠিকানা", profile.get("dis_contact_email", ""), "NOC ঠিকানা", profile.get("dis_noc_address", ""))
    ]
    
    for l1, v1, l2, v2 in info_rows:
        ws[f"A{row}"] = l1
        ws[f"B{row}"] = v1
        ws[f"C{row}"] = ""
        ws.merge_cells(f"B{row}:C{row}")
        ws[f"D{row}"] = l2
        ws[f"E{row}"] = v2
        ws[f"F{row}"] = ""
        ws.merge_cells(f"E{row}:F{row}")
        
        ws[f"A{row}"].font = bold_font
        ws[f"D{row}"].font = bold_font
        ws[f"B{row}"].font = normal_font
        ws[f"E{row}"].font = normal_font
        
        for c in ["A", "B", "C", "D", "E", "F"]:
            ws[f"{c}{row}"].border = thin_border
        row += 1
        
    row += 1
    
    # Section 2: Upstream Audit & Discrepancy Analysis (The Crucial Section!)
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "২. আপস্ট্রিম তুলনামূলক অডিট ও অসঙ্গতি বিশ্লেষণ (Comparative Upstream Audit)"
    ws[f"A{row}"].font = white_bold
    ws[f"A{row}"].fill = header_fill
    ws.row_dimensions[row].height = 22
    row += 1
    
    # Table headers for Upstream Comparison
    headers = ["সোর্স (Source)", "প্রাপ্ত আপস্ট্রিম সংখ্যা", "আপস্ট্রিম প্রোভাইডারের তালিকা", "লাইভ স্ট্যাটাস / অডিট পর্যবেক্ষণ"]
    ws[f"A{row}"] = "ডাটা সোর্স (Source)"
    ws[f"B{row}"] = "আপস্ট্রিম সংখ্যা"
    ws[f"C{row}"] = "আপস্ট্রিম প্রোভাইডার তালিকা"
    ws.merge_cells(f"C{row}:D{row}")
    ws[f"E{row}"] = "অডিট ফ্ল্যাগ ও বিশ্লেষণ"
    ws.merge_cells(f"E{row}:F{row}")
    
    for c in ["A", "B", "C", "D", "E", "F"]:
        ws[f"{c}{row}"].fill = sub_fill
        ws[f"{c}{row}"].font = bold_font
        ws[f"{c}{row}"].border = thin_border
    row += 1
    
    dis_up = profile.get("dis_declared_upstream", "") or "কোনো ঘোষণা নেই"
    dis_count = profile.get("dis_declared_upstream_count", 0)
    bgp_up = profile.get("bgp_live_upstream", "") or "BGP-তে দৃশ্যমান নয়"
    bgp_count = profile.get("bgp_live_upstream_count", 0)
    audit_desc = profile.get("audit_discrepancy", "তথ্য অপর্যাপ্ত")
    audit_status = profile.get("audit_status", "REVIEW")
    
    # DIS Row
    ws[f"A{row}"] = "BTRC DIS Portal (অফিসিয়াল ঘোষণা)"
    ws[f"B{row}"] = f"{dis_count} টি"
    ws[f"C{row}"] = dis_up
    ws.merge_cells(f"C{row}:D{row}")
    ws[f"E{row}"] = "অফিসিয়াল নথিবদ্ধ"
    ws.merge_cells(f"E{row}:F{row}")
    for c in ["A", "B", "C", "D", "E", "F"]:
        ws[f"{c}{row}"].border = thin_border
        ws[f"{c}{row}"].font = normal_font
    row += 1
    
    # BGP.tools / Live BGP Row
    ws[f"A{row}"] = "bgp.tools / Hurricane Electric (বাস্তব BGP ট্র্যাফিক)"
    ws[f"B{row}"] = f"{bgp_count} টি"
    ws[f"C{row}"] = bgp_up
    ws.merge_cells(f"C{row}:D{row}")
    ws[f"E{row}"] = "লাইভ ইন্টারনেটে সক্রিয়"
    ws.merge_cells(f"E{row}:F{row}")
    for c in ["A", "B", "C", "D", "E", "F"]:
        ws[f"{c}{row}"].border = thin_border
        ws[f"{c}{row}"].font = normal_font
    row += 1
    
    # Audit Verdict Row
    ws.merge_cells(f"A{row}:B{row}")
    ws[f"A{row}"] = "তুলনামূলক অডিট সিদ্ধান্ত:"
    ws[f"A{row}"].font = bold_font
    ws[f"C{row}"] = audit_desc
    ws.merge_cells(f"C{row}:F{row}")
    ws[f"C{row}"].font = alert_font if audit_status == "MISMATCH" else (ok_font if audit_status == "OK" else bold_font)
    ws[f"C{row}"].fill = mismatch_fill if audit_status == "MISMATCH" else (ok_fill if audit_status == "OK" else sub_fill)
    for c in ["A", "B", "C", "D", "E", "F"]:
        ws[f"{c}{row}"].border = thin_border
    row += 2
    
    # Section 3: Technical Routing & IP Status
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "৩. নেটওয়ার্ক রাউটিং ও আইপি তথ্য (Live BGP Routing & Visibility)"
    ws[f"A{row}"].font = white_bold
    ws[f"A{row}"].fill = header_fill
    ws.row_dimensions[row].height = 22
    row += 1
    
    net_rows = [
        ("IPv4 গ্লোবাল ভিজিবিলিটি", profile.get("bgp_visibility_v4", "N/A"), "IPv6 গ্লোবাল ভিজিবিলিটি", profile.get("bgp_visibility_v6", "N/A")),
        ("DIS-এ ঘোষিত IPv4", profile.get("raw_json_dict", {}).get("ipv4_declared", "YES"), "DIS-এ ঘোষিত IPv6", profile.get("raw_json_dict", {}).get("ipv6_declared", "NO")),
        ("লাইভ চেকের সময়", profile.get("last_live_checked_at", "N/A"), "ক্যাশ রেকর্ডের সময়", profile.get("last_cached_at", "N/A"))
    ]
    
    for l1, v1, l2, v2 in net_rows:
        ws[f"A{row}"] = l1
        ws[f"B{row}"] = v1
        ws[f"C{row}"] = ""
        ws.merge_cells(f"B{row}:C{row}")
        ws[f"D{row}"] = l2
        ws[f"E{row}"] = v2
        ws[f"F{row}"] = ""
        ws.merge_cells(f"E{row}:F{row}")
        
        ws[f"A{row}"].font = bold_font
        ws[f"D{row}"].font = bold_font
        ws[f"B{row}"].font = normal_font
        ws[f"E{row}"].font = normal_font
        for c in ["A", "B", "C", "D", "E", "F"]:
            ws[f"{c}{row}"].border = thin_border
        row += 1

    row += 1
    # Section 4: Commission Decisions
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "৪. কমিশনের সিদ্ধান্ত ও দিকনির্দেশনা (Commission Decisions & Directives)"
    ws[f"A{row}"].font = white_bold
    ws[f"A{row}"].fill = header_fill
    ws.row_dimensions[row].height = 22
    row += 1

    # Decisions header
    ws[f"A{row}"] = "কমিশন সভা নং"
    ws[f"B{row}"] = "তারিখ"
    ws[f"C{row}"] = "বিষয়"
    ws[f"D{row}"] = "সিদ্ধান্তের বিবরণ"
    ws[f"E{row}"] = "প্রদত্ত নির্দেশনা"
    ws[f"F{row}"] = "কমপ্লায়েন্স স্ট্যাটাস"
    for c in ["A", "B", "C", "D", "E", "F"]:
        ws[f"{c}{row}"].font = bold_font
        ws[f"{c}{row}"].fill = sub_fill
        ws[f"{c}{row}"].border = thin_border
    row += 1

    import db_master
    asn_key = profile.get("asn", "")
    decisions = db_master.get_commission_decisions(asn_key)
    if decisions:
        for dec in decisions:
            ws[f"A{row}"] = dec.get("meeting_no", "")
            ws[f"B{row}"] = dec.get("decision_date", "")
            ws[f"C{row}"] = dec.get("subject", "")
            ws[f"D{row}"] = dec.get("decision_summary", "")
            ws[f"E{row}"] = dec.get("directive_issued", "")
            ws[f"F{row}"] = dec.get("compliance_status", "")
            for c in ["A", "B", "C", "D", "E", "F"]:
                ws[f"{c}{row}"].font = normal_font
                ws[f"{c}{row}"].border = thin_border
            row += 1
    else:
        ws.merge_cells(f"A{row}:F{row}")
        ws[f"A{row}"] = "কোনো কমিশনের সিদ্ধান্ত রেকর্ড পাওয়া যায়নি।"
        ws[f"A{row}"].font = sub_font
        for c in ["A", "B", "C", "D", "E", "F"]:
            ws[f"{c}{row}"].border = thin_border
        row += 1

    row += 1
    # Section 5: Penalties and Disciplinary Actions
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "৫. আরোপিত প্রশাসনিক জরিমানা ও ডিসিপ্লিনারি রেকর্ড (Penalties & Violations)"
    ws[f"A{row}"].font = white_bold
    ws[f"A{row}"].fill = header_fill
    ws.row_dimensions[row].height = 22
    row += 1

    # Penalties header
    ws[f"A{row}"] = "লঙ্ঘনের ধরণ (Violation)"
    ws[f"B{row}"] = "চিঠির স্মারক নম্বর"
    ws[f"C{row}"] = "জরিমানার তারিখ"
    ws[f"D{row}"] = "পরিমাণ (টাকা)"
    ws[f"E{row}"] = "পরিশোধের স্ট্যাটাস"
    ws[f"F{row}"] = "রশিদ নং / মন্তব্য"
    for c in ["A", "B", "C", "D", "E", "F"]:
        ws[f"{c}{row}"].font = bold_font
        ws[f"{c}{row}"].fill = sub_fill
        ws[f"{c}{row}"].border = thin_border
    row += 1

    penalties = db_master.get_penalties(asn_key)
    if penalties:
        for pen in penalties:
            ws[f"A{row}"] = pen.get("violation_category", "")
            ws[f"B{row}"] = pen.get("letter_ref_no", "")
            ws[f"C{row}"] = pen.get("penalty_date", "")
            amt = pen.get("penalty_amount_bdt", 0)
            ws[f"D{row}"] = f"৳ {amt:,.2f}"
            ws[f"E{row}"] = pen.get("payment_status", "")
            ws[f"F{row}"] = pen.get("payment_receipt_no") or pen.get("remarks", "")
            for c in ["A", "B", "C", "D", "E", "F"]:
                ws[f"{c}{row}"].font = normal_font
                ws[f"{c}{row}"].border = thin_border
            row += 1
    else:
        ws.merge_cells(f"A{row}:F{row}")
        ws[f"A{row}"] = "কোনো জরিমানা বা শাস্তিমূলক রেকর্ড পাওয়া যায়নি।"
        ws[f"A{row}"].font = sub_font
        for c in ["A", "B", "C", "D", "E", "F"]:
            ws[f"{c}{row}"].border = thin_border
        row += 1
        
    # Auto-adjust column widths
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 25
    ws.column_dimensions["D"].width = 25
    ws.column_dimensions["E"].width = 25
    ws.column_dimensions["F"].width = 25
    
    wb.save(filepath)
    return filepath

def export_bulk_companies(profiles: list, output_dir: str = None, group_name: str = "All_Companies") -> str:
    """
    Exports a list of company profiles into a master comparison table.
    """
    if not output_dir:
        output_dir = os.path.dirname(os.path.dirname(__file__))
        
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d_%I-%M%p")
    filename = f"{sanitize_filename(group_name)}_Audit_{timestamp_str}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Master Audit Report"
    ws.views.sheetView[0].showGridLines = True
    
    navy_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
    header_fill = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")
    mismatch_fill = PatternFill(start_color="FED7D7", end_color="FED7D7", fill_type="solid")
    ok_fill = PatternFill(start_color="C6F6D5", end_color="C6F6D5", fill_type="solid")
    
    white_bold = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    bold_font = Font(name="Segoe UI", size=10, bold=True)
    normal_font = Font(name="Segoe UI", size=9)
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E0'),
        right=Side(style='thin', color='CBD5E0'),
        top=Side(style='thin', color='CBD5E0'),
        bottom=Side(style='thin', color='CBD5E0')
    )
    
    # Title
    ws.merge_cells("A1:K1")
    ws["A1"] = f"BTRC টেলিকম ও আইএসপি মাস্টার কোম্পানি প্রোফাইল এবং আপস্ট্রিম অডিট রিপোর্ট"
    ws["A1"].font = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32
    
    ws.merge_cells("A2:K2")
    ws["A2"] = f"মোট প্রতিষ্ঠান: {len(profiles)} টি  |  রিপোর্ট তৈরির সময়: {now.strftime('%d-%m-%Y %I:%M %p')}  |  সোর্স: DIS Portal, bgp.tools, Local DB"
    ws["A2"].font = Font(name="Segoe UI", size=10, bold=True, color="2D3748")
    ws["A2"].fill = PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid")
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22
    
    headers = [
        "SL", "ASN", "প্রতিষ্ঠানের নাম (Company)", "লাইসেন্স ধরণ (Category)", "লাইসেন্স নম্বর",
        "DIS ঘোষিত আপস্ট্রিম", "DIS আপস্ট্রিম সংখ্যা",
        "BGP লাইভ আপস্ট্রিম (bgp.tools)", "BGP আপস্ট্রিম সংখ্যা",
        "অডিট স্ট্যাটাস", "অসঙ্গতি বিশ্লেষণ (Discrepancy Details)"
    ]
    
    row = 4
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row, col_idx, h)
        cell.fill = header_fill
        cell.font = white_bold
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[row].height = 28
    
    row = 5
    for idx, p in enumerate(profiles, 1):
        ws.cell(row, 1, idx).alignment = Alignment(horizontal="center")
        ws.cell(row, 2, p.get("asn", "")).alignment = Alignment(horizontal="center")
        ws.cell(row, 3, p.get("canonical_name", ""))
        ws.cell(row, 4, p.get("license_status", "")).alignment = Alignment(horizontal="center")
        ws.cell(row, 5, p.get("license_no", "")).alignment = Alignment(horizontal="center")
        
        ws.cell(row, 6, p.get("dis_declared_upstream", ""))
        ws.cell(row, 7, p.get("dis_declared_upstream_count", 0)).alignment = Alignment(horizontal="center")
        
        ws.cell(row, 8, p.get("bgp_live_upstream", ""))
        ws.cell(row, 9, p.get("bgp_live_upstream_count", 0)).alignment = Alignment(horizontal="center")
        
        status_cell = ws.cell(row, 10, p.get("audit_status", "REVIEW"))
        status_cell.alignment = Alignment(horizontal="center")
        if p.get("audit_status") == "MISMATCH":
            status_cell.fill = mismatch_fill
            status_cell.font = Font(name="Segoe UI", size=9, bold=True, color="9B2C2C")
        elif p.get("audit_status") == "OK":
            status_cell.fill = ok_fill
            status_cell.font = Font(name="Segoe UI", size=9, bold=True, color="22543D")
        else:
            status_cell.font = normal_font
            
        ws.cell(row, 11, p.get("audit_discrepancy", ""))
        
        for c in range(1, 12):
            cell = ws.cell(row, c)
            cell.border = thin_border
            if c != 10:
                cell.font = normal_font
        row += 1

    widths = [6, 12, 32, 18, 22, 30, 10, 32, 10, 14, 45]
    for i, w in enumerate(widths, 1):
        col_letter = openpyxl.utils.get_column_letter(i)
        ws.column_dimensions[col_letter].width = w
        
    wb.save(filepath)
    return filepath
