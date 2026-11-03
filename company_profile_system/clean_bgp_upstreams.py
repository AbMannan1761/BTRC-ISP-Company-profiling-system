import sqlite3, openpyxl, urllib.request, re, json, time, sys, os
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'company_profile_system/Apps/company_master_profile.db'
EXCEL_PATH = 'BTRC_DIS_Master_Database.xlsx'
CACHE_PATH = 'company_profile_system/bgp_clean_cache.json'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

cache = {}
if os.path.exists(CACHE_PATH):
    try:
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    except Exception as e:
        print("Cache load error:", e, flush=True)

def save_cache():
    try:
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        pass

def fetch_clean_upstreams_he(asn_str):
    m = re.match(r'^(AS\d+)', asn_str.strip(), re.I)
    if not m:
        return None
    asn_clean = m.group(1).upper()
    
    if asn_clean in cache:
        return cache[asn_clean]
    
    url = f'https://bgp.he.net/{asn_clean}'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8')
            m_table = re.search(r'<thead><tr><th>ASN</th><th>Name</th></tr></thead>\s*<tbody>(.*?)</tbody>', html, re.DOTALL)
            if m_table:
                tbody = m_table.group(1)
                rows = re.findall(r'<tr>\s*<td><a[^>]*>(AS\d+)</a></td>\s*<td><a[^>]*>(.*?)</a></td>\s*</tr>', tbody, re.DOTALL)
                res = []
                for a, name in rows:
                    name_clean = re.sub(r'<[^>]+>', '', name).strip()
                    res.append((a, name_clean))
                cache[asn_clean] = res
                save_cache()
                return res
            cache[asn_clean] = []
            save_cache()
            return []
    except Exception as e:
        print(f"Error fetching {asn_clean} from HE: {e}", flush=True)
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT DISTINCT asn, canonical_name, bgp_live_upstream_count, bgp_live_upstream, dis_declared_upstream
        FROM company_profiles
        WHERE bgp_live_upstream IS NOT NULL AND bgp_live_upstream != ''
    ''')
    profiles = c.fetchall()
    
    targets = []
    for r in profiles:
        asn, name, count, bgp_raw, dis_decl = r
        if not asn or not asn.startswith('AS'):
            continue
        # Specific customer pollutants: Bank, bKash, ASA, BRAC, AS64, AS65, or count > 4
        is_suspicious = count > 4 or any(w in (bgp_raw or '') for w in ['Bank', 'bKash', 'ASA', 'BRAC', 'AS64', 'AS65', 'Telecom Operator'])
        if is_suspicious:
            targets.append((asn, name, count, bgp_raw, dis_decl))
            
    print(f"Total polluted ASN profiles identified: {len(targets)}", flush=True)
    
    updated_count = 0
    for idx, (asn, name, old_count, old_bgp, dis_decl) in enumerate(targets, 1):
        print(f"[{idx}/{len(targets)}] Cleaning {asn} ({name}) - old count: {old_count}...", flush=True)
        peers = fetch_clean_upstreams_he(asn)
        if peers is not None:
            new_count = len(peers)
            if new_count > 0:
                new_bgp_str = "\n".join([p[1] for p in peers])
                new_asns_str = ", ".join([p[0] for p in peers])
            else:
                new_bgp_str = ""
                new_asns_str = ""
                
            decl_set = set([x.strip().lower() for x in (dis_decl or '').split('\n') if x.strip()])
            bgp_set = set([x.strip().lower() for x in (new_bgp_str or '').split('\n') if x.strip()])
            
            if not decl_set and not bgp_set:
                new_status = 'MATCH'
                disc = 'কোনো সক্রিয় আপস্ট্রিম নেই।'
            elif not decl_set:
                new_status = 'MISMATCH'
                disc = f"⚠️ অডিট অসঙ্গতি: DIS পোর্টালে কোনো আপস্ট্রিম ঘোষণা নেই (0টি), কিন্তু লাইভ BGP-তে {new_count}টি সক্রিয় আইআইজি আপস্ট্রিম দৃশ্যমান: {new_asns_str}"
            elif decl_set == bgp_set or all(any(d in b or b in d for b in bgp_set) for d in decl_set):
                new_status = 'MATCH'
                disc = f"DIS পোর্টালে ঘোষিত আপস্ট্রিমসমূহ লাইভ BGP রাউটিংয়ের সাথে সম্পূর্ণ সামঞ্জস্যপূর্ণ।"
            else:
                new_status = 'MISMATCH'
                disc = f"⚠️ অডিট অসঙ্গতি: DIS-এ ঘোষিত {len(decl_set)}টি, কিন্তু লাইভ BGP-তে দৃশ্যমান {new_count}টি।"

            c.execute('''
                UPDATE company_profiles
                SET bgp_live_upstream = ?,
                    bgp_live_upstream_count = ?,
                    bgp_observed_asns = ?,
                    audit_status = ?,
                    audit_discrepancy = ?
                WHERE asn = ?
            ''', (new_bgp_str, new_count, new_asns_str, new_status, disc, asn))
            conn.commit()
            updated_count += 1
            print(f"   -> Result: {new_count} true upstreams: {[p[1] for p in peers]}", flush=True)
        time.sleep(0.3)
        
    print(f"\nAll {updated_count} polluted ASN profiles successfully cleaned and committed!", flush=True)

if __name__ == '__main__':
    main()
