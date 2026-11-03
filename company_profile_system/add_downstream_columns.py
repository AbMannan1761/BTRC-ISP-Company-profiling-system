import openpyxl, sqlite3, sys, os
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
sys.stdout.reconfigure(encoding='utf-8')

ORIG_EXCEL = 'BTRC_DIS_Master_Database.orig.xlsx'
OUTPUT_EXCEL = 'BTRC_DIS_Master_Database.xlsx'
DB_PATH = 'company_profile_system/Apps/company_master_profile.db'

print("Loading original excel and database...")
wb_orig = openpyxl.load_workbook(ORIG_EXCEL, data_only=True)
ws_orig = wb_orig.active

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Get all current clean upstreams and declared data from DB
c.execute('SELECT asn, bgp_live_upstream, bgp_live_upstream_count, bgp_observed_asns, dis_declared_upstream, dis_declared_upstream_count, audit_status, audit_discrepancy FROM company_profiles')
db_records = {}
for r in c.fetchall():
    asn, bgp_ups, bgp_cnt, bgp_asns, dis_ups, dis_cnt, status, disc = r
    if asn:
        db_records[asn] = {
            'bgp_ups': bgp_ups or '',
            'bgp_cnt': bgp_cnt or 0,
            'bgp_asns': bgp_asns or '',
            'dis_ups': dis_ups or '',
            'dis_cnt': dis_cnt or 0,
            'status': status or 'UNVERIFIED',
            'disc': disc or ''
        }

# Read original rows
orig_headers = [ws_orig.cell(row=1, column=col).value for col in range(1, ws_orig.max_column + 1)]
print(f"Original columns count: {len(orig_headers)}")

# Build new workbook with separate Upstream and Downstream columns
wb_new = openpyxl.Workbook()
ws_new = wb_new.active
ws_new.title = "DIS & BGP Master Database"

# New Header definition:
new_headers = [
    '[DIS] Operator ID',                      # 1
    '[DIS] Company Name (Licensee)',           # 2
    '[DIS] ISP Category',                      # 3
    '[DIS] License Number',                    # 4
    '[DIS] Contact Person',                    # 5
    '[DIS] Designation',                       # 6
    '[DIS] Contact Mobile / Phone',            # 7
    '[DIS] Contact Email',                     # 8
    '[DIS] Division',                          # 9
    '[DIS] District',                          # 10
    '[DIS] Thana / Upazilla',                  # 11
    '[DIS] NOC Full Address',                  # 12
    '[DIS] Approved Upstream (Mbps)',          # 13
    '[DIS] Buying Price (BDT)',                # 14
    '[DIS] IPv4 Declared',                     # 15
    '[DIS] IPv6 Declared',                     # 16
    '[DIS] Declared Upstream (DIS)',           # 17 (NEW DIS UPSTREAM COLUMN)
    '[BGP] Autonomous System (ASN)',           # 18
    '[BGP] AS Organization Name',              # 19
    '[BGP] AS Network Class',                  # 20
    '[BGP] Live Upstream Providers',           # 21 (CLEAN BGP UPSTREAM)
    '[BGP] Live Upstream Count',               # 22
    '[BGP] Live Upstream ASNs',                # 23
    '[BGP] Live Downstream Clients / Customers', # 24 (DEDICATED DOWNSTREAM COLUMN)
    '[BGP] Live Downstream Count',             # 25
    '[BGP] IPv4 Routing Visibility',           # 26
    '[BGP] IPv6 Routing Visibility',           # 27
    '[AUDIT] Reconciliation Status',           # 28
    '[AUDIT] Discrepancy Observation',         # 29
    '[SYS] Last Updated At'                    # 30
]

header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
thin_border = Border(
    left=Side(style='thin', color='E2E8F0'),
    right=Side(style='thin', color='E2E8F0'),
    top=Side(style='thin', color='E2E8F0'),
    bottom=Side(style='thin', color='E2E8F0')
)

for col_idx, h in enumerate(new_headers, 1):
    cell = ws_new.cell(row=1, column=col_idx, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

db_downstream_updates = []

for r in range(2, ws_orig.max_row + 1):
    op_id = ws_orig.cell(row=r, column=1).value
    comp_name = ws_orig.cell(row=r, column=2).value
    cat = ws_orig.cell(row=r, column=3).value
    lic_no = ws_orig.cell(row=r, column=4).value
    contact = ws_orig.cell(row=r, column=5).value
    desig = ws_orig.cell(row=r, column=6).value
    phone = ws_orig.cell(row=r, column=7).value
    email = ws_orig.cell(row=r, column=8).value
    division = ws_orig.cell(row=r, column=9).value
    district = ws_orig.cell(row=r, column=10).value
    thana = ws_orig.cell(row=r, column=11).value
    address = ws_orig.cell(row=r, column=12).value
    bw = ws_orig.cell(row=r, column=13).value
    price = ws_orig.cell(row=r, column=14).value
    ipv4_decl = ws_orig.cell(row=r, column=15).value
    ipv6_decl = ws_orig.cell(row=r, column=16).value
    asn = ws_orig.cell(row=r, column=17).value
    as_org = ws_orig.cell(row=r, column=18).value
    as_net_class = ws_orig.cell(row=r, column=19).value
    
    # Original BGP neighbours raw:
    orig_peers_raw = ws_orig.cell(row=r, column=20).value
    orig_peers = [x.strip() for x in str(orig_peers_raw or '').split(',') if x.strip()]
    
    # Defaults from DB
    rec = db_records.get(asn, {})
    dis_declared = rec.get('dis_ups', '')
    dis_decl_comma = ", ".join(dis_declared.split('\n')) if dis_declared else ""
    
    bgp_ups_clean = rec.get('bgp_ups', '')
    bgp_ups_list = [x.strip() for x in str(bgp_ups_clean or '').split('\n') if x.strip()]
    bgp_ups_comma = ", ".join(bgp_ups_list)
    bgp_ups_count = len(bgp_ups_list)
    bgp_asns = rec.get('bgp_asns', '')
    
    # Calculate Downstreams (items in orig_peers not in clean upstreams)
    clean_ups_lower = set([x.lower() for x in bgp_ups_list])
    downstreams = []
    for p in orig_peers:
        if not any(u in p.lower() or p.lower() in u for u in clean_ups_lower):
            downstreams.append(p)
            
    bgp_down_comma = ", ".join(downstreams)
    bgp_down_count = len(downstreams)
    
    v4_vis = ws_orig.cell(row=r, column=23).value
    v6_vis = ws_orig.cell(row=r, column=24).value
    status = rec.get('status', ws_orig.cell(row=r, column=25).value)
    disc = rec.get('disc', ws_orig.cell(row=r, column=26).value)
    updated_at = ws_orig.cell(row=r, column=27).value
    
    row_values = [
        op_id, comp_name, cat, lic_no, contact, desig, phone, email,
        division, district, thana, address, bw, price, ipv4_decl, ipv6_decl,
        dis_decl_comma, # 17: [DIS] Declared Upstream (DIS)
        asn, as_org, as_net_class,
        bgp_ups_comma,  # 21: [BGP] Live Upstream Providers
        bgp_ups_count,  # 22: [BGP] Live Upstream Count
        bgp_asns,       # 23: [BGP] Live Upstream ASNs
        bgp_down_comma, # 24: [BGP] Live Downstream Clients / Customers
        bgp_down_count, # 25: [BGP] Live Downstream Count
        v4_vis, v6_vis, status, disc, updated_at
    ]
    
    for c_idx, val in enumerate(row_values, 1):
        cell = ws_new.cell(row=r, column=c_idx, value=val)
        cell.border = thin_border
        if c_idx in [1, 13, 14, 22, 25]:
            cell.alignment = Alignment(horizontal="right", vertical="center")
        elif c_idx in [3, 15, 16, 18, 20, 26, 27, 28]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")
            
    # Save downstream to DB
    if asn:
        down_str_nl = "\n".join(downstreams)
        db_downstream_updates.append((down_str_nl, bgp_down_count, asn))

# Update DB with downstreams
for down_str, down_cnt, asn in db_downstream_updates:
    c.execute('''
        UPDATE company_profiles
        SET bgp_live_downstream = ?,
            bgp_live_downstream_count = ?
        WHERE asn = ?
    ''', (down_str, down_cnt, asn))

conn.commit()
print("Updated database with downstream records.")

# Set column widths
ws_new.column_dimensions['A'].width = 12
ws_new.column_dimensions['B'].width = 32
ws_new.column_dimensions['C'].width = 18
ws_new.column_dimensions['D'].width = 28
ws_new.column_dimensions['Q'].width = 36 # DIS Declared Upstream
ws_new.column_dimensions['R'].width = 14 # ASN
ws_new.column_dimensions['U'].width = 45 # BGP Live Upstream
ws_new.column_dimensions['V'].width = 14 # Upstream count
ws_new.column_dimensions['X'].width = 50 # BGP Live Downstream
ws_new.column_dimensions['Y'].width = 14 # Downstream count
ws_new.column_dimensions['AB'].width = 16 # Status
ws_new.column_dimensions['AC'].width = 55 # Discrepancy Observation

wb_new.save(OUTPUT_EXCEL)
print(f"Successfully saved updated {OUTPUT_EXCEL} with separate Upstream and Downstream columns!")
