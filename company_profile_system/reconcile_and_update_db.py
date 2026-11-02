import sqlite3
import json
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.append('company_profile_system/Apps')
from reconciliation import reconcile_upstreams

DB_PATH = 'company_profile_system/Apps/company_master_profile.db'
CACHE_PATH = 'company_profile_system/dis_scraped_cache.json'

with open(CACHE_PATH, 'r', encoding='utf-8') as f:
    cache = json.load(f)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT * FROM company_profiles")
rows = cur.fetchall()

print(f"Total company profiles: {len(rows)}")

match_cnt = 0
mismatch_cnt = 0
unverified_cnt = 0

for r in rows:
    asn = r['asn']
    op_id = str(r['dis_operator_id']) if r['dis_operator_id'] else ''
    
    # 1. Update DIS declared if in cache
    dis_str = r['dis_declared_upstream'] or ''
    if op_id in cache and cache[op_id].get('iigs'):
        dis_str = '\n'.join(cache[op_id]['iigs'])
    
    dis_list = [x.strip() for x in dis_str.split('\n') if x.strip()]
    dis_cnt = len(dis_list)
    
    bgp_str = r['bgp_live_upstream'] or ''
    bgp_list = [x.strip() for x in bgp_str.split('\n') if x.strip()]
    bgp_cnt = len(bgp_list)
    
    # Run reconciliation
    res = reconcile_upstreams(dis_list, bgp_list)
    status = res['audit_status']
    
    # Normalize status for dashboard badges: MATCH, MISMATCH, UNVERIFIED
    if status in ['OK', 'MATCH']:
        badge_status = 'MATCH'
        match_cnt += 1
    elif status in ['MISMATCH', 'WARNING', 'REVIEW']:
        badge_status = 'MISMATCH'
        mismatch_cnt += 1
    else:
        badge_status = 'UNVERIFIED'
        unverified_cnt += 1
        
    desc = res['discrepancy_desc']
    
    cur.execute("""
        UPDATE company_profiles
        SET dis_declared_upstream = ?,
            dis_declared_upstream_count = ?,
            audit_status = ?,
            audit_discrepancy = ?
        WHERE asn = ?
    """, (dis_str, dis_cnt, badge_status, desc, asn))

conn.commit()
print("=== RECONCILIATION AUDIT COMPLETED ===")
print(f"MATCH (যাচাইকৃত সামঞ্জস্য): {match_cnt}")
print(f"MISMATCH (আপস্ট্রিম অসঙ্গতি): {mismatch_cnt}")
print(f"UNVERIFIED: {unverified_cnt}")

# Check Alo Communications
cur.execute("SELECT asn, canonical_name, dis_declared_upstream, dis_declared_upstream_count, bgp_live_upstream_count, audit_status, audit_discrepancy FROM company_profiles WHERE asn='AS23729'")
alo = cur.fetchone()
print("\n--- Alo Communications (AS23729) ---")
print("Name:", alo['canonical_name'])
print("DIS Declared:", repr(alo['dis_declared_upstream']))
print("Declared Count:", alo['dis_declared_upstream_count'])
print("BGP Live Count:", alo['bgp_live_upstream_count'])
print("Audit Status:", alo['audit_status'])
print("Discrepancy:", alo['audit_discrepancy'])

conn.close()
