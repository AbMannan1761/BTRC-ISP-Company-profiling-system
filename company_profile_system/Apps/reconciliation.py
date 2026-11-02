import re

def normalize_comp_name(s):
    if not s: return ""
    s = s.lower().replace("’", "'").replace("‘", "'").replace("`", "'")
    s = re.sub(r'[\.\,\(\)\/\\\-\_\'\"]', ' ', s)
    s = re.sub(r'\b(ltd|limited|llc|inc|bd|isp|pvt|co|corp|corporation|plc)\b', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def reconcile_upstreams(dis_declared_list, bgp_live_list):
    """
    Compares DIS declared upstreams with Live BGP upstreams.
    Returns audit status, discrepancy description, and comparison breakdown.
    """
    dis_clean = {normalize_comp_name(u): u for u in dis_declared_list if u}
    bgp_clean = {normalize_comp_name(u): u for u in bgp_live_list if u}
    
    matched = []
    undeclared_in_dis = []
    inactive_in_bgp = []
    
    for b_norm, b_orig in bgp_clean.items():
        found = False
        for d_norm in dis_clean.keys():
            if b_norm == d_norm or (len(b_norm) > 4 and b_norm in d_norm) or (len(d_norm) > 4 and d_norm in b_norm):
                matched.append(b_orig)
                found = True
                break
        if not found:
            undeclared_in_dis.append(b_orig)
            
    for d_norm, d_orig in dis_clean.items():
        found = False
        for b_norm in bgp_clean.keys():
            if d_norm == b_norm or (len(d_norm) > 4 and d_norm in b_norm) or (len(b_norm) > 4 and b_norm in d_norm):
                found = True
                break
        if not found:
            inactive_in_bgp.append(d_orig)

    d_count = len(dis_declared_list)
    b_count = len(bgp_live_list)
    
    if b_count == 0 and d_count == 0:
        status = "UNVERIFIED"
        desc = "কোনো সোর্সেই আপস্ট্রিম তথ্য নেই (No Upstream Recorded)"
    elif undeclared_in_dis:
        status = "MISMATCH"
        desc = f"⚠️ অডিট অসঙ্গতি: DIS-এ ঘোষিত {d_count}টি, কিন্তু লাইভ BGP-তে দৃশ্যমান {b_count}টি। অঘোষিত আপস্ট্রিম: {', '.join(undeclared_in_dis)}"
    elif inactive_in_bgp:
        status = "WARNING"
        desc = f"⚠️ সতর্কতা: DIS-এ ঘোষিত আপস্ট্রিম ({', '.join(inactive_in_bgp)}) লাইভ BGP-তে সক্রিয় দেখা যাচ্ছে না।"
    elif d_count == b_count and d_count > 0:
        status = "OK"
        desc = f"✅ শতভাগ মিল: DIS ঘোষণা ও লাইভ BGP আপস্ট্রিম সম্পূর্ণ সংগতিপূর্ণ ({', '.join(matched)})"
    else:
        status = "REVIEW"
        desc = f"DIS-এ ঘোষিত: {d_count}টি | লাইভ BGP-তে প্রাপ্ত: {b_count}টি"
        
    return {
        "audit_status": status,
        "discrepancy_desc": desc,
        "matched_upstreams": matched,
        "undeclared_live_upstreams": undeclared_in_dis,
        "inactive_declared_upstreams": inactive_in_bgp,
        "dis_count": d_count,
        "bgp_count": b_count
    }
