import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "company_master_profile.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS company_profiles (
        asn TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        license_status TEXT,
        license_no TEXT,
        dis_operator_id INTEGER,
        dis_operator_name TEXT,
        dis_declared_upstream TEXT,
        dis_declared_upstream_count INTEGER DEFAULT 0,
        dis_bandwidth_mbps TEXT,
        dis_noc_address TEXT,
        dis_contact_person TEXT,
        dis_contact_phone TEXT,
        dis_contact_email TEXT,
        bgp_live_upstream TEXT,
        bgp_live_upstream_count INTEGER DEFAULT 0,
        bgp_observed_asns TEXT,
        bgp_visibility_v4 TEXT,
        bgp_visibility_v6 TEXT,
        audit_discrepancy TEXT,
        audit_status TEXT,
        source_local_note TEXT,
        ei_dashboard_status TEXT,
        last_cached_at TEXT,
        last_live_checked_at TEXT,
        raw_json TEXT
    );

    CREATE TABLE IF NOT EXISTS commission_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asn TEXT,
        company_name TEXT,
        meeting_no TEXT,
        decision_date TEXT,
        subject TEXT,
        decision_summary TEXT,
        directive_issued TEXT,
        compliance_status TEXT DEFAULT 'Pending',
        remarks TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS company_penalties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asn TEXT,
        company_name TEXT,
        violation_category TEXT,
        letter_ref_no TEXT,
        penalty_date TEXT,
        penalty_amount_bdt REAL DEFAULT 0,
        payment_status TEXT DEFAULT 'Unpaid',
        payment_receipt_no TEXT,
        due_date TEXT,
        remarks TEXT,
        created_at TEXT
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_name ON company_profiles(canonical_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_status ON company_profiles(license_status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dis_id ON company_profiles(dis_operator_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dec_asn ON commission_decisions(asn)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pen_asn ON company_penalties(asn)")
    conn.commit()
    conn.close()

def save_or_update_company(data: dict):
    """
    Saves or updates a company profile in the master cache.
    Returns True if an existing record was updated with deltas, or False if newly inserted.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    asn = data.get("asn", "").strip()
    if not asn:
        conn.close()
        return False

    cur.execute("SELECT * FROM company_profiles WHERE asn = ?", (asn,))
    existing = cur.fetchone()
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["last_cached_at"] = now_str
    
    columns = [
        "asn", "canonical_name", "license_status", "license_no",
        "dis_operator_id", "dis_operator_name", "dis_declared_upstream",
        "dis_declared_upstream_count", "dis_bandwidth_mbps", "dis_noc_address",
        "dis_contact_person", "dis_contact_phone", "dis_contact_email",
        "bgp_live_upstream", "bgp_live_upstream_count", "bgp_observed_asns",
        "bgp_visibility_v4", "bgp_visibility_v6", "audit_discrepancy",
        "audit_status", "source_local_note", "ei_dashboard_status",
        "last_cached_at", "last_live_checked_at", "raw_json"
    ]
    
    vals = [data.get(c) for c in columns]
    placeholders = ",".join(["?"] * len(columns))
    update_clause = ",".join([f"{c}=excluded.{c}" for c in columns if c != "asn"])
    
    query = f"""
    INSERT INTO company_profiles ({",".join(columns)})
    VALUES ({placeholders})
    ON CONFLICT(asn) DO UPDATE SET {update_clause}
    """
    
    cur.execute(query, vals)
    conn.commit()
    conn.close()
    return existing is not None

def get_company_by_asn(asn: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM company_profiles WHERE asn = ? COLLATE NOCASE", (asn.strip(),))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def search_companies(query: str):
    conn = get_connection()
    cur = conn.cursor()
    q = f"%{query.strip()}%"
    cur.execute("""
    SELECT * FROM company_profiles 
    WHERE asn LIKE ? OR canonical_name LIKE ? OR dis_operator_name LIKE ? OR license_no LIKE ?
    ORDER BY canonical_name ASC LIMIT 50
    """, (q, q, q, q))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_companies(category=None):
    conn = get_connection()
    cur = conn.cursor()
    if category:
        cur.execute("SELECT * FROM company_profiles WHERE license_status = ? ORDER BY canonical_name ASC", (category,))
    else:
        cur.execute("SELECT * FROM company_profiles ORDER BY canonical_name ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM company_profiles")
    total = cur.fetchone()[0]
    cur.execute("SELECT license_status, COUNT(*) FROM company_profiles GROUP BY license_status")
    by_status = dict(cur.fetchall())
    cur.execute("SELECT audit_status, COUNT(*) FROM company_profiles GROUP BY audit_status")
    by_audit = dict(cur.fetchall())
    conn.close()
    return {
        "total": total,
        "by_status": by_status,
        "by_audit": by_audit
    }

# ================= Commission Decisions CRUD =================

def add_commission_decision(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO commission_decisions 
    (asn, company_name, meeting_no, decision_date, subject, decision_summary, directive_issued, compliance_status, remarks, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("asn", "").strip().upper(),
        data.get("company_name", ""),
        data.get("meeting_no", ""),
        data.get("decision_date", ""),
        data.get("subject", ""),
        data.get("decision_summary", ""),
        data.get("directive_issued", ""),
        data.get("compliance_status", "Pending"),
        data.get("remarks", ""),
        now_str
    ))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_commission_decisions(asn: str = None):
    conn = get_connection()
    cur = conn.cursor()
    if asn:
        cur.execute("""
        SELECT * FROM commission_decisions 
        WHERE asn = ? COLLATE NOCASE 
        ORDER BY decision_date DESC, id DESC
        """, (asn.strip().upper(),))
    else:
        cur.execute("SELECT * FROM commission_decisions ORDER BY decision_date DESC, id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_commission_decision(decision_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM commission_decisions WHERE id = ?", (decision_id,))
    conn.commit()
    conn.close()

# ================= Company Penalties CRUD =================

def add_penalty(data: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
    INSERT INTO company_penalties 
    (asn, company_name, violation_category, letter_ref_no, penalty_date, penalty_amount_bdt, payment_status, payment_receipt_no, due_date, remarks, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("asn", "").strip().upper(),
        data.get("company_name", ""),
        data.get("violation_category", "General Non-Compliance"),
        data.get("letter_ref_no", ""),
        data.get("penalty_date", ""),
        float(data.get("penalty_amount_bdt") or 0.0),
        data.get("payment_status", "Unpaid"),
        data.get("payment_receipt_no", ""),
        data.get("due_date", ""),
        data.get("remarks", ""),
        now_str
    ))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_penalties(asn: str = None):
    conn = get_connection()
    cur = conn.cursor()
    if asn:
        cur.execute("""
        SELECT * FROM company_penalties 
        WHERE asn = ? COLLATE NOCASE 
        ORDER BY penalty_date DESC, id DESC
        """, (asn.strip().upper(),))
    else:
        cur.execute("SELECT * FROM company_penalties ORDER BY penalty_date DESC, id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_penalty_status(penalty_id: int, payment_status: str, payment_receipt_no: str = ""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    UPDATE company_penalties 
    SET payment_status = ?, payment_receipt_no = ? 
    WHERE id = ?
    """, (payment_status, payment_receipt_no, penalty_id))
    conn.commit()
    conn.close()

def delete_penalty(penalty_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM company_penalties WHERE id = ?", (penalty_id,))
    conn.commit()
    conn.close()

def get_compliance_stats():
    conn = get_connection()
    cur = conn.cursor()
    
    # Decisions count
    cur.execute("SELECT compliance_status, COUNT(*) FROM commission_decisions GROUP BY compliance_status")
    dec_by_status = dict(cur.fetchall())
    
    # Penalties sum and count
    cur.execute("""
    SELECT 
        COUNT(*), 
        COALESCE(SUM(penalty_amount_bdt), 0),
        COALESCE(SUM(CASE WHEN payment_status = 'Paid' THEN penalty_amount_bdt ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN payment_status != 'Paid' THEN penalty_amount_bdt ELSE 0 END), 0)
    FROM company_penalties
    """)
    p_row = cur.fetchone()
    total_penalties_count = p_row[0]
    total_amount = p_row[1]
    total_paid = p_row[2]
    total_unpaid = p_row[3]
    
    cur.execute("SELECT payment_status, COUNT(*) FROM company_penalties GROUP BY payment_status")
    pen_by_status = dict(cur.fetchall())

    conn.close()
    return {
        "decisions_by_status": dec_by_status,
        "penalties_count": total_penalties_count,
        "total_penalty_bdt": total_amount,
        "paid_penalty_bdt": total_paid,
        "unpaid_penalty_bdt": total_unpaid,
        "penalties_by_status": pen_by_status
    }

def get_company_full_profile(asn: str):
    asn_clean = asn.strip().upper()
    comp = get_company_by_asn(asn_clean)
    if not comp:
        return None
    decisions = get_commission_decisions(asn_clean)
    penalties = get_penalties(asn_clean)
    return {
        "profile": comp,
        "decisions": decisions,
        "penalties": penalties
    }

def seed_sample_records_if_empty():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM commission_decisions")
    dec_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM company_penalties")
    pen_count = cur.fetchone()[0]
    conn.close()

    if dec_count == 0:
        samples_dec = [
            {
                "asn": "AS133112",
                "company_name": "Spectra Technologies Limited",
                "meeting_no": "278th Commission Meeting",
                "decision_date": "2026-08-14",
                "subject": "অঘোষিত আপস্ট্রিম আইআইজি সংযোগ ও বিজিএম মিসম্যাচ সংশোধন",
                "decision_summary": "কমিশনের অনুমোদন ব্যতীত অতিরিক্ত আপস্ট্রিম (Summit & Virgo) ব্যবহার করায় সতর্কীকরণ এবং ৩০ দিনের মধ্যে ডিআইএস পোর্টালে ডিক্লেয়ার করার নির্দেশ।",
                "directive_issued": "১ মাসের মধ্যে ডিআইএস ডাটাবেজ হালনাগাদ ও কমপ্লায়েন্স রিপোর্ট জমা দান।",
                "compliance_status": "Under Review",
                "remarks": "নিরীক্ষায় বিজিএম লাইভ আপস্ট্রিম ৩টি পাওয়া গেছে যেখানে ডিআইএসে ১টি ঘোষিত।"
            },
            {
                "asn": "AS137453",
                "company_name": "Orange Bangladesh",
                "meeting_no": "274th Commission Meeting",
                "decision_date": "2026-06-20",
                "subject": "লাইসেন্স নবায়ন ও বার্ষিক নিরীক্ষা সংক্রান্ত সিদ্ধান্ত",
                "decision_summary": "আইএসপি লাইসেন্সের মেয়াদ উত্তীর্ণ হওয়ায় নবায়ন ফি ও বিলম্ব ফি পরিশোধ সাপেক্ষে সাময়িক কার্যপরিচালনার অনুমোদন।",
                "directive_issued": "সকল বকেয়া রাজস্ব পরিশোধের নোটিশ প্রদান।",
                "compliance_status": "Complied",
                "remarks": "রাজস্ব শাখা হতে ছাড়পত্র প্রাপ্ত।"
            },
            {
                "asn": "AS137810",
                "company_name": "Md Obaid Ullah Khan",
                "meeting_no": "281st Commission Meeting",
                "decision_date": "2026-09-05",
                "subject": "অননুমোদিত ও লাইসেন্সবিহীন ইন্টারনেট নেটওয়ার্ক পরিচালনা বন্ধকরণ",
                "decision_summary": "লাইসেন্সবিহীন অবস্থায় এএসএন ও রাউটিং অবকাঠামো পরিচালনার দায়ে কার্যক্রম অবিলম্বে বন্ধের নির্দেশ এবং এনটিটিএন/আইআইজি সমূহকে সংযোগ বিচ্ছিন্নকরণের নির্দেশ।",
                "directive_issued": "এনফোর্সমেন্ট টিমকে স্পট ইন্সপেকশন ও সরঞ্জাম জব্দের নির্দেশ।",
                "compliance_status": "Non-Compliant",
                "remarks": "Not Licensee তালিকাভুক্ত।"
            }
        ]
        for d in samples_dec:
            add_commission_decision(d)

    if pen_count == 0:
        samples_pen = [
            {
                "asn": "AS133112",
                "company_name": "Spectra Technologies Limited",
                "violation_category": "Undeclared Upstream / BGP Leak",
                "letter_ref_no": "BTRC/LL/E&I/Audit/2026/894",
                "penalty_date": "2026-08-20",
                "penalty_amount_bdt": 200000.0,
                "payment_status": "Unpaid",
                "payment_receipt_no": "",
                "due_date": "2026-11-20",
                "remarks": "ডিআইএস পোর্টালে অবৈধ আপস্ট্রিম তথ্য গোপনের জন্য প্রশাসনিক জরিমানা।"
            },
            {
                "asn": "AS137810",
                "company_name": "Md Obaid Ullah Khan",
                "violation_category": "Unauthorized ISP Operation (No License)",
                "letter_ref_no": "BTRC/E&I/Enforce/Notice/2026/102",
                "penalty_date": "2026-09-10",
                "penalty_amount_bdt": 500000.0,
                "payment_status": "Unpaid",
                "payment_receipt_no": "",
                "due_date": "2026-10-10",
                "remarks": "লাইসেন্সবিহীন ইন্টারনেট বিতরণ।"
            },
            {
                "asn": "AS137453",
                "company_name": "Orange Bangladesh",
                "violation_category": "Late Renewal Fee Penalty",
                "letter_ref_no": "BTRC/Fin/ISP-Fine/2026/412",
                "penalty_date": "2026-06-25",
                "penalty_amount_bdt": 50000.0,
                "payment_status": "Paid",
                "payment_receipt_no": "TR-2026-67891",
                "due_date": "2026-07-25",
                "remarks": "বিলম্ব ফি পরিশোধিত।"
            }
        ]
        for p in samples_pen:
            add_penalty(p)

init_db()
seed_sample_records_if_empty()
