import sqlite3
import openpyxl

# 1. Update SQLite DB
db_path = r'company_profile_system/Apps/company_master_profile.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

declared_upstreams = (
    "ADN International Gateway Limited (40,000 Mbps)\n"
    "Summit Communications Ltd (20,000 Mbps)\n"
    "Fiber@Home Global Limited (10,000 Mbps)\n"
    "Bangladesh Submarine Cable Company Limited (BSCCL) (5,000 Mbps)\n"
    "EARTH TELECOMMUNICATION (Pvt) LTD. (870 Mbps)"
)

live_upstreams = (
    "ADN International Gateway Limited (AS59378)\n"
    "Bangladesh Submarine Cable Company Limited - BSCCL (AS132602)\n"
    "Summit Communications Ltd (AS58717)\n"
    "Fiber@Home Global Limited (AS10075)\n"
    "EARTH TELECOMMUNICATION (Pvt) LTD. (AS58715)\n"
    "EXABYTE LTD (AS150178)"
)

obs = "ডিআইএস-এ ঘোষিত ৫টি প্রধান আইআইজি আপস্ট্রিমই লাইভ বিজিপিতে সক্রিয় রয়েছে এবং অতিরিক্ত ১টি সক্রিয় ব্যাকআপ ট্রানজিট (EXABYTE LTD - AS150178) রয়েছে।"

cur.execute("""
UPDATE company_profiles
SET 
    dis_declared_upstream = ?,
    dis_declared_upstream_count = 5,
    bgp_live_upstream = ?,
    bgp_live_upstream_count = 6,
    audit_status = 'MATCH',
    audit_discrepancy = ?
WHERE canonical_name LIKE '%ADN Telecom%' OR asn = 'AS38203'
""", (declared_upstreams, live_upstreams, obs))

conn.commit()
print(f"Updated {cur.rowcount} row(s) in SQLite.")

cur.execute("SELECT canonical_name, asn, dis_declared_upstream_count, bgp_live_upstream_count, audit_status, audit_discrepancy FROM company_profiles WHERE asn = 'AS38203'")
rec = cur.fetchone()
print(f"DB Record updated: {rec[0]} | ASN: {rec[1]} | Declared: {rec[2]} | Live: {rec[3]} | Status: {rec[4]}")
conn.close()

# 2. Update Excel if file exists
excel_path = "BTRC_DIS_Master_Database.xlsx"
try:
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active
    
    # find row for ADN Telecom
    for row in range(2, ws.max_row + 1):
        c_name = str(ws.cell(row=row, column=3).value or "") # Operator Name usually col 3
        if "ADN Telecom" in c_name:
            print(f"Found ADN Telecom in Excel at row {row}")
            # check headers
            # let's set declared and live upstream if columns exist
            for col in range(1, ws.max_column + 1):
                header = str(ws.cell(row=1, column=col).value or "").lower()
                if "declared" in header or "ডিসেম্বর" in header or "ঘোষিত" in header:
                    ws.cell(row=row, column=col).value = declared_upstreams
                elif "live" in header or "লাইভ" in header or "bgp" in header and "upstream" in header:
                    ws.cell(row=row, column=col).value = live_upstreams
                elif "audit" in header or "স্ট্যাটাস" in header:
                    ws.cell(row=row, column=col).value = "MATCH"
    wb.save(excel_path)
    print("Excel updated successfully.")
except Exception as e:
    print(f"Excel update note: {e}")
