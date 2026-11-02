import sys
import os
import json
import sqlite3
import re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "company_profile_system/Apps/company_master_profile.db"

def clean_str(s):
    if not s:
        return ""
    s = s.strip().lower()
    for drop in ["limited", "ltd.", "ltd", "private", "pvt.", "pvt", "online", "communication", "communications", "internet", "network", "networks", "broadband", "cyber", "technology", "technologies", "tel", "telecom", "it", "link"]:
        s = re.sub(rf'\b{drop}\b', '', s)
    return re.sub(r'[^a-z0-9]', '', s)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all companies
cur.execute("SELECT asn, canonical_name, dis_operator_id, audit_status FROM company_profiles")
companies = [dict(r) for r in cur.fetchall()]
print(f"Total Companies in DB: {len(companies)}", flush=True)

# Precompute cleaned names
comp_lookup = {}
cleaned_list = []
for c in companies:
    c_clean = clean_str(c["canonical_name"])
    if c_clean:
        comp_lookup[c_clean] = c
        cleaned_list.append((c_clean, c))

# 1. Sync Penalties
print("Syncing Penalties from ei_penalties_cache.json...", flush=True)
with open("company_profile_system/ei_penalties_cache.json", "r", encoding="utf-8") as f:
    penalties_cache = json.load(f)

cur.execute("DELETE FROM company_penalties")
penalty_rows = []

bn_digits = {'০':'0', '১':'1', '২':'2', '৩':'3', '৪':'4', '৫':'5', '৬':'6', '৭':'7', '৮':'8', '৯':'9'}

for p in penalties_cache:
    raw_name = p.get("company_name", "")
    c_clean = clean_str(raw_name)
    target_comp = comp_lookup.get(c_clean)
    
    if not target_comp and len(c_clean) >= 4:
        for k, c in cleaned_list:
            if len(k) >= 4 and (k in c_clean or c_clean in k):
                target_comp = c
                break
                
    asn = target_comp["asn"] if target_comp else f"NO_ASN_{hash(raw_name) % 100000}"
    canonical_name = target_comp["canonical_name"] if target_comp else raw_name
    
    raw_fine = p.get("fine_amount", "")
    for bn, en in bn_digits.items():
        raw_fine = raw_fine.replace(bn, en)
    fine_str = re.sub(r'[^\d.]', '', raw_fine)
    try:
        fine_bdt = float(fine_str) if fine_str else 0.0
    except Exception:
        fine_bdt = 0.0
        
    penalty_rows.append((
        asn,
        canonical_name,
        p.get("reason", "প্রশাসনিক জরিমানা"),
        p.get("sheet", "E-I Dashboard"),
        p.get("meeting_info", datetime.now().strftime("%Y-%m-%d")),
        fine_bdt,
        p.get("status", "বকেয়া"),
        f"উৎস: E-I Dashboard ({p.get('sheet', '')})",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

cur.executemany("""
    INSERT INTO company_penalties (
        asn, company_name, violation_category, letter_ref_no, penalty_date,
        penalty_amount_bdt, payment_status, remarks, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", penalty_rows)

print(f"Inserted {len(penalty_rows)} penalties into company_penalties table.", flush=True)

# 2. Sync Commission Decisions
print("Syncing Commission Decisions from ei_commission_cache.json...", flush=True)
with open("company_profile_system/ei_commission_cache.json", "r", encoding="utf-8") as f:
    comm_cache = json.load(f)

cur.execute("DELETE FROM commission_decisions")
decision_rows = []

for dec in comm_cache:
    subj = dec.get("subject", "")
    decision_text = dec.get("decision", "")
    full_text = subj + " " + decision_text
    clean_full = clean_str(full_text)
    
    matched_for_this = []
    for k, c in cleaned_list:
        if len(k) >= 5 and k in clean_full:
            matched_for_this.append(c)
            if len(matched_for_this) >= 2:
                break
            
    if not matched_for_this:
        decision_rows.append((
            "GENERAL",
            "সাধারণ কমিশন সিদ্ধান্ত",
            dec.get("meeting_number", ""),
            dec.get("meeting_date", ""),
            subj[:250],
            decision_text[:400],
            f"এজেন্ডা নং: {dec.get('agenda_no', '')}",
            "গৃহীত",
            "BTRC Meeting Portal",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
    else:
        for tc in matched_for_this:
            decision_rows.append((
                tc["asn"],
                tc["canonical_name"],
                dec.get("meeting_number", ""),
                dec.get("meeting_date", ""),
                subj[:250],
                decision_text[:400],
                f"এজেন্ডা নং: {dec.get('agenda_no', '')}",
                "গৃহীত",
                "BTRC Meeting Portal",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

cur.executemany("""
    INSERT INTO commission_decisions (
        asn, company_name, meeting_no, decision_date, subject,
        decision_summary, directive_issued, compliance_status, remarks, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", decision_rows)

conn.commit()
conn.close()

print(f"Inserted {len(decision_rows)} commission decisions into commission_decisions table.", flush=True)
print("E&I Sync complete successfully!", flush=True)
