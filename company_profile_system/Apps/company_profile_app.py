import os
import sys

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))

import db_master
from profile_manager import CompanyProfileManager

def print_banner():
    print("=" * 72)
    print("  BTRC কোম্পানি প্রোফাইল ও নেটওয়ার্ক আপস্ট্রিম অডিট সিস্টেম (DIS & BGP)")
    print("  Directorate of Engineering & Inspection (E&I) - BTRC")
    print("=" * 72)

def format_profile_cli(profile: dict, source: str = "cache"):
    print("\n" + "-" * 72)
    print(f"  প্রতিষ্ঠানের নাম : {profile.get('canonical_name')}")
    print(f"  ASN             : {profile.get('asn')}")
    print(f"  লাইসেন্স ধরণ    : {profile.get('license_status')}")
    print(f"  লাইসেন্স নম্বর   : {profile.get('license_no') or 'N/A'}")
    print(f"  ডাটা সোর্স       : {'⚡ লোকাল মাস্টার ক্যাশ (০ সেকেন্ড)' if source == 'local_cache' else '🌐 লাইভ রিয়েল-টাইম রিভ্যালিডেটেড'}")
    print("-" * 72)
    
    print("\n  [আপস্ট্রিম তুলনামূলক অডিট চিত্র]")
    dis_up = profile.get('dis_declared_upstream', '').replace('\n', ', ') or 'কোনো ঘোষণা পাওয়া যায়নি'
    bgp_up = profile.get('bgp_live_upstream', '').replace('\n', ', ') or 'BGP-তে সক্রিয় দেখা যাচ্ছে না'
    
    print(f"  • DIS পোর্টালে ঘোষিত আপস্ট্রিম ({profile.get('dis_declared_upstream_count', 0)} টি):")
    print(f"    --> {dis_up}")
    print(f"  • bgp.tools / লাইভ BGP আপস্ট্রিম ({profile.get('bgp_live_upstream_count', 0)} টি):")
    print(f"    --> {bgp_up}")
    
    print("\n  [অডিট পর্যবেক্ষণ ও স্ট্যাটাস]")
    print(f"    {profile.get('audit_discrepancy')}")

    import db_master
    asn_key = profile.get('asn', '')
    decs = db_master.get_commission_decisions(asn_key)
    pens = db_master.get_penalties(asn_key)

    if decs:
        print("\n  [কমিশনের সিদ্ধান্ত]")
        for d in decs:
            print(f"  • {d.get('meeting_no')} ({d.get('decision_date')}): {d.get('subject')}")
            print(f"    নির্দেশনা: {d.get('directive_issued')} [স্ট্যাটাস: {d.get('compliance_status')}]")
    else:
        print("\n  [কমিশনের সিদ্ধান্ত]: কোনো রেকর্ড নেই")

    if pens:
        print("\n  [আরোপিত জরিমানা ও ডিসিপ্লিনারি রেকর্ড]")
        for p in pens:
            print(f"  • {p.get('violation_category')}: ৳ {p.get('penalty_amount_bdt', 0):,.2f} ({p.get('payment_status')})")
            print(f"    চিঠি স্মারক: {p.get('letter_ref_no')} | তারিখ: {p.get('penalty_date')}")
    else:
        print("\n  [আরোপিত জরিমানা]: কোনো রেকর্ড নেই")

    print("\n  [অন্যান্য তথ্য]")
    if profile.get('dis_bandwidth_mbps'):
        print(f"  • ঘোষিত ব্যান্ডউইথ : {profile.get('dis_bandwidth_mbps')} Mbps")
    if profile.get('dis_contact_person'):
        print(f"  • যোগাযোগ ব্যক্তি   : {profile.get('dis_contact_person')} ({profile.get('dis_contact_phone', '')})")
    if profile.get('dis_noc_address'):
        print(f"  • NOC ঠিকানা       : {profile.get('dis_noc_address')}")
    if profile.get('bgp_visibility_v4'):
        print(f"  • IPv4 BGP স্ট্যাটাস: {profile.get('bgp_visibility_v4')}")
    print("-" * 72)

def main():
    mgr = CompanyProfileManager()
    stats = db_master.get_stats()
    
    while True:
        print_banner()
        print(f"  মাস্টার ডাটাবেজে সংরক্ষিত কোম্পানি: {stats['total']} টি")
        print("  ১. কোম্পানি সার্চ করুন (নাম বা ASN দিয়ে)")
        print("  ২. সম্পূর্ণ মাস্টার অডিট রিপোর্ট এক্সেলে এক্সপোর্ট করুন (Bulk Export)")
        print("  ৩. ক্যাটাগরি অনুযায়ী এক্সপোর্ট (যেমন: District / Divisional / Nationwide)")
        print("  ৪. 🌐 লাইভ ওয়েব ড্যাশবোর্ড চালু করুন (Streamlit Web Dashboard)")
        print("  ৫. প্রস্থান (Exit)")
        print("-" * 72)
        
        choice = input("  আপনার পছন্দ লিখুন (১-৫): ").strip()
        
        if choice == "১":
            q = input("\n  কোম্পানির নাম বা ASN লিখুন (যেমন: Feni Cyber বা AS150302): ").strip()
            if not q:
                continue
                
            res = mgr.get_profile(q, live_revalidate=False)
            if not res or not res.get("profile"):
                print(f"\n  ❌ দুঃখিত! '{q}' নামে কোনো কোম্পানি খুঁজে পাওয়া যায়নি।")
                input("\n  এন্টার চাপুন...")
                continue
                
            p = res["profile"]
            format_profile_cli(p, source=res["source"])
            
            while True:
                print("\n  কার্যক্রম অপশন:")
                print("  [R] লাইভ DIS ও bgp.tools থেকে রিভ্যালিডেট ও অটো-আপডেট করুন")
                print("  [E] এই কোম্পানির প্রোফাইল এক্সেলে ডাউনলোড করুন")
                print("  [B] পেছনে ফিরে যান (Back)")
                sub = input("  সিলেক্ট করুন (R/E/B): ").strip().upper()
                
                if sub == "R":
                    print("\n  ⏳ লাইভ সার্ভারের সাথে সংযুক্ত হচ্ছে এবং যাচাই করা হচ্ছে...")
                    res_live = mgr.get_profile(p["asn"], live_revalidate=True)
                    p = res_live["profile"]
                    format_profile_cli(p, source="live")
                    if res_live.get("delta_updated"):
                        print("  ✨ লাইভ পরিবর্তনের কারণে লোকাল মাস্টার ফাইল স্বয়ংক্রিয়ভাবে আপডেট করা হয়েছে!")
                    else:
                        print("  ✅ নতুন কোনো পরিবর্তন নেই, লোকাল মাস্টার ফাইল ইতোমধ্যে আপ-টু-ডেট।")
                elif sub == "E":
                    fpath, _ = mgr.export_company(p["asn"], live_first=False)
                    print(f"\n  ✅ এক্সেল ডাউনলোড সম্পন্ন হয়েছে!")
                    print(f"  📁 ফাইল নাম: {os.path.basename(fpath)}")
                    print(f"  📍 ফাইল পাথ: {fpath}")
                elif sub == "B":
                    break
                    
        elif choice == "২":
            print("\n  ⏳ সমস্ত কোম্পানির মাস্টার অডিট ফাইল তৈরি হচ্ছে...")
            fpath, count = mgr.export_all()
            print(f"  ✅ সফলভাবে {count}টি কোম্পানির সমন্বিত অডিট ফাইল এক্সপোর্ট হয়েছে!")
            print(f"  📁 ফাইল নাম: {os.path.basename(fpath)}")
            print(f"  📍 ফাইল পাথ: {fpath}")
            input("\n  এন্টার চাপুন...")
            
        elif choice == "৩":
            print("\n  ক্যাটাগরি নির্বাচন করুন:")
            cats = ["Nationwide", "Divisional", "District", "Thana or Upazilla", "IIG", "NIX", "NTTN"]
            for idx, c in enumerate(cats, 1):
                print(f"  {idx}. {c}")
            c_idx = input("  নম্বর নির্বাচন করুন: ").strip()
            try:
                cat_name = cats[int(c_idx) - 1]
                print(f"\n  ⏳ '{cat_name}' ক্যাটাগরির অডিট ফাইল তৈরি হচ্ছে...")
                fpath, count = mgr.export_all(category=cat_name)
                print(f"  ✅ সফলভাবে {count}টি কোম্পানির অডিট ফাইল এক্সপোর্ট হয়েছে!")
                print(f"  📁 ফাইল নাম: {os.path.basename(fpath)}")
                print(f"  📍 ফাইল পাথ: {fpath}")
            except Exception:
                print("  ❌ সঠিক ক্যাটাগরি নির্বাচন করুন।")
            input("\n  এন্টার চাপুন...")
            
        elif choice == "৪":
            print("\n  🚀 ওয়েব ড্যাশবোর্ড চালু করা হচ্ছে...")
            import subprocess
            dash_path = os.path.join(os.path.dirname(__file__), "web_dashboard.py")
            subprocess.Popen([sys.executable, "-m", "streamlit", "run", dash_path])
            print("  🌐 আপনার ব্রাউজারে ড্যাশবোর্ড ওপেন হয়েছে। (http://localhost:8501)")
            input("\n  এন্টার চাপুন...")

        elif choice in ["৫", "exit", "quit", "q"]:
            print("\n  ধন্যবাদ! সিস্টেম বন্ধ করা হচ্ছে।")
            break

if __name__ == "__main__":
    main()
