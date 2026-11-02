import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

from profile_manager import CompanyProfileManager

mgr = CompanyProfileManager()

# 1. Test City Online (AS149483)
print("\n--- 1. Testing Instant Cache Read for AS149483 (City Online) ---")
res = mgr.get_profile("AS149483", live_revalidate=False)
p = res["profile"]
print(f"Company: {p['canonical_name']} | Category: {p['license_status']} | Source: {res['source']}")
print(f"DIS Upstream: {p['dis_declared_upstream']}")
print(f"BGP Upstream: {p['bgp_live_upstream']}")
print(f"Audit: {p['audit_discrepancy']}")

# 2. Test Live Revalidate for Feni Cyber Link (AS150302)
print("\n--- 2. Testing Live Revalidation for AS150302 (Feni Cyber Link) ---")
res2 = mgr.get_profile("AS150302", live_revalidate=True)
p2 = res2["profile"]
print(f"Company: {p2['canonical_name']} | Category: {p2['license_status']} | Delta Updated: {res2['delta_updated']}")
print(f"Live BGP Upstreams: {p2['bgp_live_upstream']}")
print(f"DIS Declared Upstream: {p2['dis_declared_upstream']}")
print(f"Audit Verdict: {p2['audit_discrepancy']}")

# 3. Test Export for Feni Cyber Link
print("\n--- 3. Testing Excel Export ---")
file_path, prof = mgr.export_company("AS150302", live_first=False)
print(f"Exported successfully to: {file_path}")
print(f"File exists: {os.path.exists(file_path)}, Size: {os.path.getsize(file_path)} bytes")
