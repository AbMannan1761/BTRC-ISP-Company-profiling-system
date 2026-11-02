import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="BTRC Company Profile & Regulatory Audit Dashboard",
    page_icon="🇧🇩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import db_master
from profile_manager import CompanyProfileManager
from exporter import export_single_company, export_bulk_companies

def sync_html_cache():
    try:
        import build_html_dashboard
        build_html_dashboard.generate_html_dashboard()
    except Exception as e:
        pass

# Custom CSS for polished aesthetic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;600;700&family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', 'Hind Siliguri', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #0d3b66 0%, #001e3d 100%);
        padding: 10px 20px;
        border-radius: 8px;
        color: white;
        margin-bottom: 14px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        font-size: 18px;
        font-weight: 700;
        margin: 0;
        color: #ffffff;
    }
    .main-header p {
        margin: 3px 0 0 0;
        font-size: 12px;
        color: #b0c4de;
    }
    .stat-card {
        background: white;
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 3px solid #0d3b66;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .stat-number {
        font-size: 16px;
        font-weight: 700;
        color: #0d3b66;
    }
    .stat-label {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        letter-spacing: 0.3px;
    }
    .badge-mismatch {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
        display: inline-block;
    }
    .badge-match {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
        display: inline-block;
    }
    .badge-unverified {
        background-color: #fef3c7;
        color: #92400e;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
        display: inline-block;
    }
    .section-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 18px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Manager
@st.cache_resource
def get_manager():
    return CompanyProfileManager()

manager = get_manager()

# Header
st.markdown("""
<div class="main-header">
    <h1>🇧🇩 BTRC কোম্পানি মাস্টার প্রোফাইল ও রেগুলেটরি অডিট ড্যাশবোর্ড</h1>
    <p>DIS পোর্টাল, লোকাল ডাটাবেজ ও লাইভ BGP রাউটিং অডিট | কমিশনের সিদ্ধান্ত ও জরিমানা রেজিস্টার</p>
</div>
""", unsafe_allow_html=True)

# Refresh stats
stats = db_master.get_stats()
comp_stats = db_master.get_compliance_stats()

# Top KPI Row
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(f"""
    <div class="stat-card" style="border-left-color: #0284c7;">
        <div class="stat-label">মোট অপারেটর</div>
        <div class="stat-number">{stats['total']}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    mismatches = stats['by_audit'].get('MISMATCH', 0)
    st.markdown(f"""
    <div class="stat-card" style="border-left-color: #ef4444;">
        <div class="stat-label">আপস্ট্রিম অসঙ্গতি (Mismatch)</div>
        <div class="stat-number" style="color: #dc2626;">{mismatches}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    dec_total = sum(comp_stats['decisions_by_status'].values())
    st.markdown(f"""
    <div class="stat-card" style="border-left-color: #8b5cf6;">
        <div class="stat-label">কমিশন সিদ্ধান্ত</div>
        <div class="stat-number" style="color: #7c3aed;">{dec_total}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    tot_fine = comp_stats['total_penalty_bdt']
    st.markdown(f"""
    <div class="stat-card" style="border-left-color: #f59e0b;">
        <div class="stat-label">মোট আরোপিত জরিমানা</div>
        <div class="stat-number" style="color: #d97706;">৳ {tot_fine:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    unpaid_fine = comp_stats['unpaid_penalty_bdt']
    st.markdown(f"""
    <div class="stat-card" style="border-left-color: #dc2626;">
        <div class="stat-label">বকেয়া জরিমানা</div>
        <div class="stat-number" style="color: #dc2626;">৳ {unpaid_fine:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

# Navigation tabs
tab_profile, tab_table, tab_add_comp, tab_compliance, tab_analytics, tab_bulk = st.tabs([
    "🔍 কোম্পানি প্রোফাইল এক্সপ্লোরার",
    "📋 মাস্টার ডিরেক্টরি (টেবিল ভিউ)",
    "➕ নতুন অপারেটর নিবন্ধন",
    "⚖️ কমিশন সিদ্ধান্ত ও জরিমানা রেজিস্টার",
    "📊 অডিট ও কমপ্লায়েন্স অ্যানালিটিক্স",
    "📥 বাল্ক এক্সপোর্ট ও ডাটা ডাউনলোড"
])

# ================= TAB 1: Company Profile Explorer =================
with tab_profile:
    st.subheader("কোম্পানি প্রোফাইল ও অডিট বিবরণ")
    
    # Filter Row
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_query = st.text_input("কোম্পানির নাম অথবা ASN দিয়ে খুঁজুন (যেমন: Spectra, AS133112, Orange):", "")
    with f_col2:
        categories = ["All"] + sorted([k for k in stats['by_status'].keys() if k])
        selected_cat = st.selectbox("লাইসেন্স ক্যাটাগরি ফিল্টার:", categories)
    with f_col3:
        audit_filters = ["All", "MISMATCH", "UNVERIFIED", "MATCH"]
        selected_audit = st.selectbox("অডিট স্ট্যাটাস ফিল্টার:", audit_filters)

    # Get companies based on filter
    all_comps = db_master.get_all_companies(category=None if selected_cat == "All" else selected_cat)
    if search_query.strip():
        all_comps = [c for c in all_comps if search_query.lower() in c.get('canonical_name', '').lower() or search_query.upper() in c.get('asn', '').upper() or search_query.lower() in (c.get('dis_operator_name') or '').lower()]
    if selected_audit != "All":
        all_comps = [c for c in all_comps if c.get('audit_status') == selected_audit]

    if not all_comps:
        st.warning("কোনো অপারেটর খুঁজে পাওয়া যায়নি। অনুসন্ধানের শব্দ পরিবর্তন করুন।")
    else:
        # Selection dropdown
        options = {f"{c.get('canonical_name')} ({c.get('asn')}) - [{c.get('license_status')}]": c.get('asn') for c in all_comps}
        selected_display = st.selectbox("অপারেটর নির্বাচন করুন:", list(options.keys()))
        selected_asn = options[selected_display]

        # Fetch profile
        comp = db_master.get_company_by_asn(selected_asn)
        decisions = db_master.get_commission_decisions(selected_asn)
        penalties = db_master.get_penalties(selected_asn)

        # Company Header Card
        audit_st = comp.get('audit_status', 'UNVERIFIED')
        badge_html = f'<span class="badge-mismatch">⚠️ {audit_st}</span>' if audit_st == "MISMATCH" else (
            f'<span class="badge-match">✅ {audit_st}</span>' if audit_st == "MATCH" else f'<span class="badge-unverified">⏳ {audit_st}</span>'
        )

        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 20px; margin-top: 15px; margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin: 0 0 5px 0; color: #0f172a; font-size: 22px;">{comp.get('canonical_name')}</h2>
                    <p style="margin: 0; color: #64748b; font-size: 14px;">
                        <b>ASN:</b> {comp.get('asn')} | 
                        <b>ক্যাটাগরি:</b> {comp.get('license_status')} | 
                        <b>লাইসেন্স নং:</b> {comp.get('license_no') or 'N/A'} | 
                        <b>DIS আইডি:</b> {comp.get('dis_operator_id') or 'N/A'}
                    </p>
                </div>
                <div>{badge_html}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Action Buttons: Live Revalidate & Export Excel
        btn_col1, btn_col2, btn_col3 = st.columns([1.5, 1.5, 3])
        with btn_col1:
            if st.button("🔄 লাইভ ডাটা যাচাই (Live Revalidate)", key=f"revalidate_{selected_asn}"):
                with st.spinner("BGP ও DIS সার্ভার হতে লাইভ ডাটা রিফ্রেশ করা হচ্ছে..."):
                    updated = manager.get_profile(selected_asn, live_revalidate=True)
                    sync_html_cache()
                    st.success("লাইভ ডাটা সফলভাবে রিফ্রেশ ও লোকাল ক্যাশে সেভ করা হয়েছে!")
                    st.rerun()

        with btn_col2:
            excel_path = export_single_company(comp)
            with open(excel_path, "rb") as f:
                st.download_button(
                    label="📥 এক্সেল প্রোফাইল ডাউনলোড",
                    data=f.read(),
                    file_name=os.path.basename(excel_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_excel_{selected_asn}"
                )

        # 3-Pillar Comparison Section (DIS | bgp.tools | E-I Dashboard)
        st.markdown("### 🏛️ ত্রিমুখী নিরীক্ষা প্যানেল (DIS Portal vs bgp.tools vs E-I Dashboard)")
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            st.markdown(f"""
            <div style="background:#f0f9ff; border:1.5px solid #bae6fd; border-top:4px solid #0284c7; border-radius:10px; padding:14px; height:100%;">
                <h4 style="margin:0 0 4px 0; color:#0369a1;">📋 DIS পোর্টাল</h4>
                <p style="margin:0 0 10px 0; font-size:12px; color:#64748b;">ঘোষিত আপস্ট্রিম ও লাইসেন্স তথ্য</p>
                <div style="font-size:13px; line-height:1.6;">
                    <b>লাইসেন্স নং:</b> {comp.get('license_no') or 'N/A'}<br>
                    <b>অনুমোদিত ব্যান্ডউইডথ:</b> {comp.get('dis_bandwidth_mbps') or 'N/A'} Mbps<br>
                    <b>ঘোষিত আপস্ট্রিম:</b> {len(comp.get('dis_declared_upstream', '').splitlines()) if comp.get('dis_declared_upstream') else 0} টি<br>
                    <b>এনওসি ঠিকানা:</b> {comp.get('dis_noc_address') or 'তথ্য নেই'}<br>
                    <b>ফোকাল পার্সন:</b> {comp.get('dis_contact_person') or 'N/A'} ({comp.get('dis_contact_phone') or 'N/A'})
                </div>
                <div style="margin-top:12px;">
                    <a href="https://dis.btrc.gov.bd" target="_blank" style="text-decoration:none; color:#0284c7; font-weight:700; font-size:12px;">🔗 DIS পোর্টালে যান &rarr;</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with p_col2:
            st.markdown(f"""
            <div style="background:#faf5ff; border:1.5px solid #e9d5ff; border-top:4px solid #7c3aed; border-radius:10px; padding:14px; height:100%;">
                <h4 style="margin:0 0 4px 0; color:#6b21a8;">📡 bgp.tools</h4>
                <p style="margin:0 0 10px 0; font-size:12px; color:#64748b;">লাইভ BGP রাউটিং ও ট্রানজিট</p>
                <div style="font-size:13px; line-height:1.6;">
                    <b>ASN:</b> {comp.get('asn')}<br>
                    <b>রাউটিং স্ট্যাটাস:</b> {'🟢 সক্রিয়' if comp.get('bgp_live_upstream') else '⚪ বিজিপি রুটহীন'}<br>
                    <b>লাইভ আপস্ট্রিম:</b> {len(comp.get('bgp_live_upstream', '').splitlines()) if comp.get('bgp_live_upstream') else 0} টি<br>
                    <b>IPv4 প্রিফিক্স:</b> {comp.get('bgp_ipv4_prefixes') or ('সক্রিয়' if comp.get('bgp_live_upstream') else '0')}<br>
                    <b>নেটওয়ার্ক:</b> {comp.get('bgp_network_name') or comp.get('canonical_name')}
                </div>
                <div style="margin-top:12px;">
                    <a href="https://bgp.tools/as/{comp.get('asn')}" target="_blank" style="text-decoration:none; color:#7c3aed; font-weight:700; font-size:12px;">🌐 bgp.tools লাইভ রুট &rarr;</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with p_col3:
            dec_count = len(decisions)
            pen_count = len(penalties)
            pen_amt = sum(float(p.get("penalty_amount_bdt") or 0) for p in penalties)
            st.markdown(f"""
            <div style="background:#f0fdf4; border:1.5px solid #bbf7d0; border-top:4px solid #059669; border-radius:10px; padding:14px; height:100%;">
                <h4 style="margin:0 0 4px 0; color:#15803d;">⚖️ E-I ড্যাশবোর্ড</h4>
                <p style="margin:0 0 10px 0; font-size:12px; color:#64748b;">আইনি, অডিট ও সিদ্ধান্ত রেকর্ড</p>
                <div style="font-size:13px; line-height:1.6;">
                    <b>অডিট স্ট্যাটাস:</b> {audit_st}<br>
                    <b>কমিশন সিদ্ধান্ত:</b> {dec_count} টি<br>
                    <b>আরোপিত জরিমানা:</b> {pen_count} টি<br>
                    <b>মোট জরিমানা:</b> ৳ {pen_amt:,.0f}<br>
                    <b>রেগুলেটরি স্ট্যাটাস:</b> {'⚠️ পর্যবেক্ষণাধীন' if audit_st == 'MISMATCH' else '✅ নিয়মিত'}
                </div>
                <div style="margin-top:12px;">
                    <a href="https://abmannan1761.github.io/E-I-dashboard/" target="_blank" style="text-decoration:none; color:#059669; font-weight:700; font-size:12px;">🏛️ E-I সেন্ট্রাল ড্যাশবোর্ড &rarr;</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Detailed Sub-tabs for Company
        st_sub1, st_sub2, st_sub3, st_sub4, st_sub5 = st.tabs([
            "🌐 আপস্ট্রিম ও নেটওয়ার্ক অডিট",
            "⚖️ কমিশনের সিদ্ধান্ত",
            "💰 আরোপিত জরিমানা",
            "🏢 ডিআইএস যোগাযোগের তথ্য",
            "✏️ প্রোফাইল এডিট ও আপডেট"
        ])

        # Sub-tab 1: Upstream & Network Audit
        with st_sub1:
            st.markdown("### আপস্ট্রিম সংযোগ নিরীক্ষা (DIS Declared vs Live BGP)")
            if comp.get('audit_discrepancy'):
                if comp.get('audit_status') == "MISMATCH":
                    st.error(f"**অসঙ্গতির বিবরণ:** {comp.get('audit_discrepancy')}")
                else:
                    st.info(f"**অডিট পর্যবেক্ষণ:** {comp.get('audit_discrepancy')}")

            u_col1, u_col2 = st.columns(2)
            with u_col1:
                st.markdown("#### 📋 DIS পোর্টালে ঘোষিত আপস্ট্রিম")
                declared = comp.get('dis_declared_upstream', '')
                if declared:
                    for line in declared.split("\n"):
                        if line.strip():
                            st.markdown(f"- 🏢 **{line.strip()}**")
                else:
                    st.write("ডিআইএস পোর্টালে কোনো আপস্ট্রিম তথ্য ঘোষিত নেই।")

            with u_col2:
                st.markdown("#### 📡 লাইভ BGP রাউটিং আপস্ট্রিম (bgp.tools)")
                live = comp.get('bgp_live_upstream', '')
                if live:
                    for line in live.split("\n"):
                        if line.strip():
                            st.markdown(f"- ⚡ **{line.strip()}**")
                else:
                    st.write("লাইভ বিজিএম আপস্ট্রিম রেকর্ড পাওয়া যায়নি।")

            st.divider()
            st.markdown("#### গ্লোবাল ভিজিবিলিটি ও নেটওয়ার্ক স্ট্যাটাস")
            v_col1, v_col2, v_col3 = st.columns(3)
            v_col1.metric("IPv4 ভিজিবিলিটি", comp.get('bgp_visibility_v4') or "99.8%+")
            v_col2.metric("IPv6 ভিজিবিলিটি", comp.get('bgp_visibility_v6') or "N/A")
            v_col3.metric("সর্বশেষ অডিট", comp.get('last_cached_at') or "N/A")

        # Sub-tab 2: Commission Decisions
        with st_sub2:
            st.markdown(f"### {comp.get('canonical_name')} - কমিশনের সিদ্ধান্ত রেকর্ড")
            if decisions:
                for dec in decisions:
                    st_badge = "✅" if dec.get('compliance_status') == "Complied" else ("⚠️" if dec.get('compliance_status') == "Under Review" else "⏳")
                    with st.expander(f"{st_badge} {dec.get('meeting_no')} ({dec.get('decision_date')}) - {dec.get('subject')}", expanded=True):
                        st.markdown(f"**সিদ্ধান্ত:** {dec.get('decision_summary')}")
                        st.markdown(f"**প্রদত্ত নির্দেশনা:** {dec.get('directive_issued')}")
                        st.markdown(f"**কমপ্লায়েন্স স্ট্যাটাস:** `{dec.get('compliance_status')}`")
                        if dec.get('remarks'):
                            st.markdown(f"**মন্তব্য:** {dec.get('remarks')}")
            else:
                st.info("এই কোম্পানির জন্য কোনো কমিশনের সিদ্ধান্তের রেকর্ড পাওয়া যায়নি।")

            # Form to add new decision for this company
            with st.expander("➕ এই কোম্পানির জন্য নতুন কমিশন সিদ্ধান্ত যুক্ত করুন"):
                with st.form(f"form_add_dec_{selected_asn}"):
                    m_no = st.text_input("কমিশন সভা নম্বর:", "285th Commission Meeting")
                    d_date = st.date_input("সিদ্ধান্তের তারিখ:", datetime.today())
                    subj = st.text_input("বিষয়:", "আপস্ট্রিম অসঙ্গতি সংক্রান্ত নোটিশ")
                    summary = st.text_area("কমিশনের সিদ্ধান্ত / সারসংক্ষেপ:")
                    directive = st.text_area("প্রদত্ত নির্দেশনা:")
                    c_status = st.selectbox("কমপ্লায়েন্স স্ট্যাটাস:", ["Pending", "Under Review", "Complied", "Non-Compliant"])
                    rem = st.text_input("মন্তব্য:")
                    submit_dec = st.form_submit_button("কমিশন সিদ্ধান্ত সেভ করুন")
                    if submit_dec:
                        db_master.add_commission_decision({
                            "asn": selected_asn,
                            "company_name": comp.get('canonical_name'),
                            "meeting_no": m_no,
                            "decision_date": str(d_date),
                            "subject": subj,
                            "decision_summary": summary,
                            "directive_issued": directive,
                            "compliance_status": c_status,
                            "remarks": rem
                        })
                        sync_html_cache()
                        st.success("কমিশনের সিদ্ধান্ত সফলভাবে যুক্ত হয়েছে!")
                        st.rerun()

        # Sub-tab 3: Penalties
        with st_sub3:
            st.markdown(f"### {comp.get('canonical_name')} - প্রশাসনিক জরিমানা ও ডিসিপ্লিনারি রেকর্ড")
            if penalties:
                for pen in penalties:
                    p_badge = "🟢 পরিশোধিত" if pen.get('payment_status') == "Paid" else "🔴 বকেয়া"
                    with st.expander(f"{p_badge} | ৳ {pen.get('penalty_amount_bdt'):,.2f} - {pen.get('violation_category')}", expanded=True):
                        p1, p2 = st.columns(2)
                        with p1:
                            st.write(f"**স্মারক নং:** {pen.get('letter_ref_no')}")
                            st.write(f"**জরিমানার তারিখ:** {pen.get('penalty_date')}")
                            st.write(f"**পরিশোধের শেষ তারিখ:** {pen.get('due_date') or 'N/A'}")
                        with p2:
                            st.write(f"**স্ট্যাটাস:** `{pen.get('payment_status')}`")
                            st.write(f"**রশিদ নম্বর:** {pen.get('payment_receipt_no') or 'N/A'}")
                            st.write(f"**মন্তব্য:** {pen.get('remarks') or 'N/A'}")
                        
                        # Quick update status
                        if pen.get('payment_status') != "Paid":
                            with st.form(f"pay_form_{pen['id']}"):
                                rec_no = st.text_input("জরিমানা পরিশোধের চালান/রশিদ নং:")
                                pay_submit = st.form_submit_button("পরিশোধ নিশ্চিত করুন (Mark as Paid)")
                                if pay_submit and rec_no:
                                    db_master.update_penalty_status(pen['id'], "Paid", rec_no)
                                    st.success("জরিমানা পরিশোধ রেকর্ড আপডেট হয়েছে!")
                                    st.rerun()
            else:
                st.info("এই কোম্পানির বিরুদ্ধে কোনো জরিমানা বা শাস্তিমূলক রেকর্ড পাওয়া যায়নি।")

            # Form to add new penalty
            with st.expander("➕ এই কোম্পানির জন্য নতুন জরিমানা ধার্য করুন"):
                with st.form(f"form_add_pen_{selected_asn}"):
                    v_cat = st.selectbox("লঙ্ঘনের ধরণ (Violation Category):", [
                        "Undeclared Upstream / BGP Leak",
                        "Unauthorized ISP Operation (No License)",
                        "Late Renewal Fee Penalty",
                        "Non-reporting to DIS Portal",
                        "Unauthorized Sub-allocation / Illegal IP Routing",
                        "Other Regulatory Violation"
                    ])
                    ref_no = st.text_input("চিঠির স্মারক নম্বর:", "BTRC/LL/E&I/Audit/2026/")
                    p_date = st.date_input("জরিমানার তারিখ:", datetime.today())
                    amt = st.number_input("জরিমানার পরিমাণ (টাকা):", min_value=0.0, step=10000.0, value=100000.0)
                    due = st.date_input("পরিশোধের শেষ তারিখ:", datetime.today())
                    p_stat = st.selectbox("পরিশোধের স্ট্যাটাস:", ["Unpaid", "Paid", "Waived", "Challenged in Court"])
                    r_rem = st.text_input("মন্তব্য:")
                    submit_pen = st.form_submit_button("জরিমানা সেভ করুন")
                    if submit_pen:
                        db_master.add_penalty({
                            "asn": selected_asn,
                            "company_name": comp.get('canonical_name'),
                            "violation_category": v_cat,
                            "letter_ref_no": ref_no,
                            "penalty_date": str(p_date),
                            "penalty_amount_bdt": amt,
                            "payment_status": p_stat,
                            "due_date": str(due),
                            "remarks": r_rem
                        })
                        sync_html_cache()
                        st.success("নতুন জরিমানা সফলভাবে ধার্য ও সংরক্ষণ করা হয়েছে!")
                        st.rerun()

        # Sub-tab 4: DIS Official Details
        with st_sub4:
            st.markdown("### ডিআইএস পোর্টালে সংরক্ষিত প্রাতিষ্ঠানিক তথ্য")
            d1, d2 = st.columns(2)
            with d1:
                st.write(f"**এনওসি / কার্যালয়ের ঠিকানা:** {comp.get('dis_noc_address') or 'N/A'}")
                st.write(f"**অনুমোদিত আপস্ট্রিম ব্যান্ডউইডথ:** {comp.get('dis_bandwidth_mbps') or 'N/A'} Mbps")
            with d2:
                st.write(f"**যোগাযোগকারী ব্যক্তি:** {comp.get('dis_contact_person') or 'N/A'}")
                st.write(f"**টেলিফোন / মোবাইল:** {comp.get('dis_contact_phone') or 'N/A'}")
                st.write(f"**ইমেইল:** {comp.get('dis_contact_email') or 'N/A'}")

        # Sub-tab 5: Profile Edit & Update
        with st_sub5:
            st.markdown(f"### ✏️ {comp.get('canonical_name')} - প্রোফাইল তথ্য সম্পাদনা ও আপডেট")
            with st.form(f"form_edit_profile_{selected_asn}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_name = st.text_input("প্রতিষ্ঠানের নাম (Canonical Name):", value=comp.get('canonical_name', ''))
                    all_statuses = ["Nationwide", "Divisional", "District", "Thana or Upazilla", "IIG", "NTTN", "NIX", "Unclassified"]
                    curr_st = comp.get('license_status', 'Unclassified')
                    idx_st = all_statuses.index(curr_st) if curr_st in all_statuses else 0
                    e_status = st.selectbox("লাইসেন্স ক্যাটাগরি:", all_statuses, index=idx_st)
                    e_lic = st.text_input("লাইসেন্স নম্বর:", value=comp.get('license_no') or '')
                    e_bw = st.text_input("অনুমোদিত ব্যান্ডউইডথ (Mbps):", value=str(comp.get('dis_bandwidth_mbps') or ''))
                with ec2:
                    e_person = st.text_input("যোগাযোগকারী ব্যক্তি:", value=comp.get('dis_contact_person') or '')
                    e_phone = st.text_input("মোবাইল / ফোন নম্বর:", value=comp.get('dis_contact_phone') or '')
                    e_email = st.text_input("ইমেইল ঠিকানা:", value=comp.get('dis_contact_email') or '')
                    all_audits = ["MISMATCH", "MATCH", "UNVERIFIED"]
                    curr_aud = comp.get('audit_status', 'UNVERIFIED')
                    idx_aud = all_audits.index(curr_aud) if curr_aud in all_audits else 2
                    e_audit = st.selectbox("অডিট স্ট্যাটাস:", all_audits, index=idx_aud)

                e_address = st.text_area("এনওসি / কার্যালয়ের ঠিকানা:", value=comp.get('dis_noc_address') or '')
                e_dis_up = st.text_area("DIS ঘোষিত আপস্ট্রিম (প্রতি লাইনে একটি):", value=comp.get('dis_declared_upstream') or '')
                e_bgp_up = st.text_area("BGP লাইভ আপস্ট্রিম (প্রতি লাইনে একটি):", value=comp.get('bgp_live_upstream') or '')
                e_disc = st.text_area("অডিট অসঙ্গতি ও পর্যবেক্ষণ:", value=comp.get('audit_discrepancy') or '')
                e_notes = st.text_input("অভ্যন্তরীণ নোট:", value=comp.get('source_local_note') or '')

                if st.form_submit_button("💾 প্রোফাইল পরিবর্তন সেভ করুন"):
                    dis_up_lines = [l.strip() for l in e_dis_up.split('\n') if l.strip()]
                    bgp_up_lines = [l.strip() for l in e_bgp_up.split('\n') if l.strip()]
                    updated_data = {
                        "asn": selected_asn,
                        "canonical_name": e_name.strip(),
                        "license_status": e_status,
                        "license_no": e_lic.strip(),
                        "dis_operator_id": comp.get('dis_operator_id'),
                        "dis_operator_name": comp.get('dis_operator_name') or e_name.strip(),
                        "dis_declared_upstream": "\n".join(dis_up_lines),
                        "dis_declared_upstream_count": len(dis_up_lines),
                        "dis_bandwidth_mbps": e_bw.strip(),
                        "dis_noc_address": e_address.strip(),
                        "dis_contact_person": e_person.strip(),
                        "dis_contact_phone": e_phone.strip(),
                        "dis_contact_email": e_email.strip(),
                        "bgp_live_upstream": "\n".join(bgp_up_lines),
                        "bgp_live_upstream_count": len(bgp_up_lines),
                        "bgp_observed_asns": comp.get('bgp_observed_asns') or '',
                        "bgp_visibility_v4": comp.get('bgp_visibility_v4') or 'Active',
                        "bgp_visibility_v6": comp.get('bgp_visibility_v6') or '',
                        "audit_discrepancy": e_disc.strip(),
                        "audit_status": e_audit,
                        "source_local_note": e_notes.strip(),
                        "ei_dashboard_status": "Manual_Edited",
                        "last_cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "last_live_checked_at": comp.get('last_live_checked_at') or '',
                        "raw_json": comp.get('raw_json') or '{}'
                    }
                    db_master.save_or_update_company(updated_data)
                    sync_html_cache()
                    st.success("কোম্পানির প্রোফাইল সফলভাবে আপডেট করা হয়েছে!")
                    st.rerun()

# ================= TAB 2: Master Directory (Table View) =================
with tab_table:
    st.subheader("📋 সকল লাইসেন্সধারী প্রতিষ্ঠানের মাস্টার ডিরেক্টরি")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        tbl_search = st.text_input("টেবিলের মধ্যে খুঁজুন (নাম / ASN / লাইসেন্স নং):", "", key="tbl_search")
    with col_t2:
        tbl_cat = st.selectbox("ক্যাটাগরি ফিল্টার:", ["All"] + sorted([k for k in stats['by_status'].keys() if k]), key="tbl_cat")

    tbl_comps = db_master.get_all_companies(category=None if tbl_cat == "All" else tbl_cat)
    if tbl_search.strip():
        tbl_comps = [c for c in tbl_comps if tbl_search.lower() in c.get('canonical_name', '').lower() or tbl_search.upper() in c.get('asn', '').upper() or tbl_search.lower() in (c.get('license_no') or '').lower()]

    if tbl_comps:
        df_tbl = pd.DataFrame(tbl_comps)[["asn", "canonical_name", "license_status", "license_no", "dis_declared_upstream_count", "bgp_live_upstream_count", "audit_status", "last_cached_at"]]
        df_tbl.columns = ["ASN", "প্রতিষ্ঠানের নাম", "লাইসেন্স ধরণ", "লাইসেন্স নম্বর", "DIS আপস্ট্রিম সংখ্যা", "BGP আপস্ট্রিম সংখ্যা", "অডিট স্ট্যাটাস", "সর্বশেষ আপডেট"]
        
        st.dataframe(df_tbl, use_container_width=True, hide_index=True)
        st.caption(f"প্রদর্শিত মোট অপারেটর: {len(tbl_comps)} টি")
        
        csv_data = df_tbl.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 ফিল্টারকৃত ডিরেক্টরি CSV ডাউনলোড",
            data=csv_data,
            file_name=f"BTRC_Operators_Directory_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("কোনো অপারেটর মেলেনি।")

# ================= TAB 3: Add New Operator =================
with tab_add_comp:
    st.subheader("➕ নতুন লাইসেন্সধারী প্রতিষ্ঠান / অপারেটর নিবন্ধন")
    st.markdown("বিটিআরসি মাস্টার ডাটাবেজে নতুন আইএসপি বা টেলিকম অপারেটর যুক্ত করুন:")
    
    with st.form("form_register_new_comp"):
        nc1, nc2 = st.columns(2)
        with nc1:
            new_asn = st.text_input("Autonomous System Number (ASN)*:", placeholder="যেমন: AS137453")
            new_name = st.text_input("প্রতিষ্ঠানের নাম (Canonical Name)*:", placeholder="যেমন: Spectrum Network Ltd.")
            new_status = st.selectbox("লাইসেন্স ক্যাটাগরি:", ["Nationwide", "Divisional", "District", "Thana or Upazilla", "IIG", "NTTN", "NIX", "Other"])
            new_lic = st.text_input("লাইসেন্স নম্বর:", placeholder="BTRC/LL/ISP/...")
            new_bw = st.text_input("অনুমোদিত ব্যান্ডউইডথ (Mbps):", placeholder="1000")
        with nc2:
            new_person = st.text_input("যোগাযোগকারী কর্মকর্তা:")
            new_phone = st.text_input("মোবাইল / ফোন নম্বর:")
            new_email = st.text_input("ইমেইল:")
            new_address = st.text_area("অফিস / এনওসি ঠিকানা:")
            new_dis_up = st.text_area("DIS ঘোষিত আপস্ট্রিম (প্রতি লাইনে একটি):")
            new_bgp_up = st.text_area("BGP লাইভ আপস্ট্রিম (প্রতি লাইনে একটি):")
        
        new_submit = st.form_submit_button("✅ নতুন অপারেটর ডাটাবেজে যুক্ত করুন")
        if new_submit:
            if not new_asn.strip() or not new_name.strip():
                st.error("ASN এবং প্রতিষ্ঠানের নাম বাধ্যতামূলক!")
            else:
                asn_clean = new_asn.strip().upper()
                if not asn_clean.startswith("AS"):
                    asn_clean = f"AS{asn_clean}"
                
                dis_lines = [l.strip() for l in new_dis_up.split('\n') if l.strip()]
                bgp_lines = [l.strip() for l in new_bgp_up.split('\n') if l.strip()]
                
                new_record = {
                    "asn": asn_clean,
                    "canonical_name": new_name.strip(),
                    "license_status": new_status,
                    "license_no": new_lic.strip(),
                    "dis_operator_id": None,
                    "dis_operator_name": new_name.strip(),
                    "dis_declared_upstream": "\n".join(dis_lines),
                    "dis_declared_upstream_count": len(dis_lines),
                    "dis_bandwidth_mbps": new_bw.strip(),
                    "dis_noc_address": new_address.strip(),
                    "dis_contact_person": new_person.strip(),
                    "dis_contact_phone": new_phone.strip(),
                    "dis_contact_email": new_email.strip(),
                    "bgp_live_upstream": "\n".join(bgp_lines),
                    "bgp_live_upstream_count": len(bgp_lines),
                    "bgp_observed_asns": "",
                    "bgp_visibility_v4": "Active" if bgp_lines else "Inactive",
                    "bgp_visibility_v6": "",
                    "audit_discrepancy": "নতুন নিবন্ধিত অপারেটর - প্রাথমিক অডিট প্রয়োজন",
                    "audit_status": "UNVERIFIED",
                    "source_local_note": f"Manually Registered on {datetime.now().strftime('%Y-%m-%d')}",
                    "ei_dashboard_status": "Registered",
                    "last_cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_live_checked_at": "",
                    "raw_json": "{}"
                }
                
                db_master.save_or_update_company(new_record)
                sync_html_cache()
                st.success(f"{new_name.strip()} ({asn_clean}) সফলভাবে মাস্টার ডাটাবেজে সংরক্ষিত হয়েছে!")
                st.rerun()


# ================= TAB 2: Commission Decisions & Penalties Master Register =================
with tab_compliance:
    st.subheader("কমিশন সিদ্ধান্ত ও জরিমানা সেন্ট্রাল রেজিস্টার")
    
    col_reg1, col_reg2 = st.columns(2)
    
    with col_reg1:
        st.markdown("### ⚖️ সকল কমিশনের সিদ্ধান্তের তালিকা")
        all_decs = db_master.get_commission_decisions()
        if all_decs:
            df_dec = pd.DataFrame(all_decs)[["meeting_no", "company_name", "asn", "decision_date", "subject", "compliance_status"]]
            df_dec.columns = ["সভা নং", "কোম্পানি", "ASN", "তারিখ", "বিষয়", "স্ট্যাটাস"]
            st.dataframe(df_dec, use_container_width=True, hide_index=True)
        else:
            st.info("কোনো সিদ্ধান্ত পাওয়া যায়নি।")

    with col_reg2:
        st.markdown("### 💰 সকল আরোপিত জরিমানার তালিকা")
        all_pens = db_master.get_penalties()
        if all_pens:
            df_pen = pd.DataFrame(all_pens)[["company_name", "asn", "violation_category", "penalty_amount_bdt", "payment_status", "penalty_date"]]
            df_pen.columns = ["কোম্পানি", "ASN", "লঙ্ঘনের ধরণ", "পরিমাণ (টাকা)", "স্ট্যাটাস", "তারিখ"]
            st.dataframe(df_pen, use_container_width=True, hide_index=True)
        else:
            st.info("কোনো জরিমানা পাওয়া যায়নি।")

    st.divider()
    st.markdown("### ➕ সেন্ট্রাল এন্ট্রি ফরম: যেকোনো কোম্পানির জন্য নতুন সিদ্ধান্ত বা জরিমানা যুক্ত করুন")
    entry_choice = st.radio("এন্ট্রির ধরণ নির্বাচন করুন:", ["কমিশনের সিদ্ধান্ত", "প্রশাসনিক জরিমানা"], horizontal=True)
    
    # Auto-complete company selection
    company_asn_list = [f"{c['asn']} - {c['canonical_name']}" for c in db_master.get_all_companies()]
    target_comp_sel = st.selectbox("কোম্পানি নির্বাচন করুন:", company_asn_list, key="central_comp_sel")
    target_asn = target_comp_sel.split(" - ")[0]
    target_name = target_comp_sel.split(" - ")[1]
    
    if entry_choice == "কমিশনের সিদ্ধান্ত":
        with st.form("form_central_dec"):
            c1, c2 = st.columns(2)
            with c1:
                cm_no = st.text_input("কমিশন সভা নং:", "285th Commission Meeting")
                cm_date = st.date_input("তারিখ:", datetime.today(), key="cm_date_c")
                cm_subj = st.text_input("বিষয়:", "লাইসেন্স শর্ত ভায়োলেশন সংক্রান্ত")
            with c2:
                cm_status = st.selectbox("কমপ্লায়েন্স স্ট্যাটাস:", ["Pending", "Under Review", "Complied", "Non-Compliant"], key="cm_st_c")
                cm_rem = st.text_input("মন্তব্য:", key="cm_rem_c")
            cm_summary = st.text_area("সিদ্ধান্তের বিস্তারিত বিবরণ:")
            cm_dir = st.text_area("প্রদত্ত নির্দেশনা:")
            
            if st.form_submit_button("কমিশন সিদ্ধান্ত সংরক্ষণ করুন"):
                db_master.add_commission_decision({
                    "asn": target_asn,
                    "company_name": target_name,
                    "meeting_no": cm_no,
                    "decision_date": str(cm_date),
                    "subject": cm_subj,
                    "decision_summary": cm_summary,
                    "directive_issued": cm_dir,
                    "compliance_status": cm_status,
                    "remarks": cm_rem
                })
                sync_html_cache()
                st.success(f"{target_name} এর জন্য কমিশনের সিদ্ধান্ত সফলভাবে সংরক্ষিত হয়েছে!")
                st.rerun()

    else:
        with st.form("form_central_pen"):
            c1, c2 = st.columns(2)
            with c1:
                p_cat = st.selectbox("লঙ্ঘনের ধরণ:", [
                    "Undeclared Upstream / BGP Leak",
                    "Unauthorized ISP Operation (No License)",
                    "Late Renewal Fee Penalty",
                    "Non-reporting to DIS Portal",
                    "Unauthorized Sub-allocation / Illegal IP Routing",
                    "Other Regulatory Violation"
                ], key="p_cat_c")
                p_ref = st.text_input("চিঠির স্মারক নম্বর:", "BTRC/LL/E&I/Penalty/2026/", key="p_ref_c")
                p_date = st.date_input("জরিমানার তারিখ:", datetime.today(), key="p_date_c")
            with c2:
                p_amt = st.number_input("জরিমানার পরিমাণ (টাকা):", min_value=0.0, step=10000.0, value=100000.0, key="p_amt_c")
                p_due = st.date_input("পরিশোধের শেষ তারিখ:", datetime.today(), key="p_due_c")
                p_stat = st.selectbox("স্ট্যাটাস:", ["Unpaid", "Paid", "Waived", "Challenged in Court"], key="p_stat_c")
            p_rem = st.text_input("মন্তব্য / নোট:", key="p_rem_c")
            
            if st.form_submit_button("জরিমানা রেকর্ড সংরক্ষণ করুন"):
                db_master.add_penalty({
                    "asn": target_asn,
                    "company_name": target_name,
                    "violation_category": p_cat,
                    "letter_ref_no": p_ref,
                    "penalty_date": str(p_date),
                    "penalty_amount_bdt": p_amt,
                    "payment_status": p_stat,
                    "due_date": str(p_due),
                    "remarks": p_rem
                })
                sync_html_cache()
                st.success(f"{target_name} এর জন্য জরিমানা সফলভাবে সংরক্ষিত হয়েছে!")
                st.rerun()


# ================= TAB 3: Analytics & Visualizations =================
with tab_analytics:
    st.subheader("পরিসংখ্যান ও রেগুলেটরি অ্যানালিটিক্স")
    
    an_col1, an_col2 = st.columns(2)
    
    with an_col1:
        st.markdown("#### লাইসেন্স ক্যাটাগরি অনুযায়ী অপারেটর সংখ্যা")
        cat_df = pd.DataFrame(list(stats['by_status'].items()), columns=["ক্যাটাগরি", "অপারেটর সংখ্যা"]).sort_values("অপারেটর সংখ্যা", ascending=False)
        st.bar_chart(cat_df.set_index("ক্যাটাগরি"))

    with an_col2:
        st.markdown("#### আপস্ট্রিম অডিট স্ট্যাটাস অনুপাত")
        audit_df = pd.DataFrame(list(stats['by_audit'].items()), columns=["অডিট স্ট্যাটাস", "সংখ্যা"])
        st.bar_chart(audit_df.set_index("অডিট স্ট্যাটাস"))

    st.divider()
    st.markdown("#### 💰 জরিমানা আদায় বনাম বকেয়া পরিসংখ্যান")
    m1, m2, m3 = st.columns(3)
    m1.metric("মোট আরোপিত জরিমানা", f"৳ {comp_stats['total_penalty_bdt']:,.0f}")
    m2.metric("আদায়কৃত জরিমানা", f"৳ {comp_stats['paid_penalty_bdt']:,.0f}", delta="আদায় সম্পন্ন")
    m3.metric("বকেয়া জরিমানা", f"৳ {comp_stats['unpaid_penalty_bdt']:,.0f}", delta="-বকেয়া", delta_color="inverse")


# ================= TAB 4: Bulk Export & Backup =================
with tab_bulk:
    st.subheader("বাল্ক এক্সপোর্ট ও ডাটা ডাউনলোড")
    st.markdown("কমিশনের সকল কোম্পানির প্রোফাইল, অডিট হিস্ট্রি এবং আপস্ট্রিম তথ্য এক ক্লিকে এক্সেলে ডাউনলোড করুন।")
    
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        export_cat = st.selectbox("ডাউনলোড করার ক্যাটাগরি নির্বাচন করুন:", ["All"] + sorted([k for k in stats['by_status'].keys() if k]))
        
        if st.button("📊 মাস্টার এক্সেল ফাইল প্রস্তুত করুন", type="primary"):
            with st.spinner("এক্সেল ফাইল প্রস্তুত হচ্ছে..."):
                cat_filter = None if export_cat == "All" else export_cat
                filepath, count = manager.export_all(category=cat_filter)
                st.success(f"সফলভাবে {count}টি কোম্পানির মাস্টার অডিট রিপোর্ট তৈরি হয়েছে!")
                
                with open(filepath, "rb") as f:
                    st.download_button(
                        label=f"📥 ডাউনলোড করুন ({os.path.basename(filepath)})",
                        data=f.read(),
                        file_name=os.path.basename(filepath),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

    with b_col2:
        st.info("""
        **এক্সেল ফাইলে যা যা অন্তর্ভুক্ত থাকবে:**
        - প্রতিটি কোম্পানির লাইসেন্স ক্যাটাগরি ও নম্বর
        - DIS ঘোষিত আপস্ট্রিম বনাম লাইভ BGP আপস্ট্রিম
        - অডিট মিসম্যাচ ও অসঙ্গতি বিশ্লেষণ
        - কমিশনের সিদ্ধান্ত এবং জরিমানার সামগ্রিক রিপোর্ট
        - তারিখ ও সময়সহ স্বয়ংসম্পূর্ণ ফাইলের নাম
        """)
