# BTRC ISP Company Profiling & Regulatory Audit System 🇧🇩
### Directorate of Engineering & Inspection (E&I), BTRC

🌐 **Live Interactive Dashboard:**  
👉 **[https://abmannan1761.github.io/BTRC-ISP-Company-profiling-system/](https://abmannan1761.github.io/BTRC-ISP-Company-profiling-system/)**

---

## 📌 Project Overview
The **BTRC ISP Company Profiling & Regulatory Audit System** is a unified analytics and compliance auditing platform for Bangladesh Telecommunication Regulatory Commission (BTRC). It correlates regulatory declarations from BTRC's **Data Information System (DIS)** with real-time routing tables from global **BGP routing registries** (bgp.tools / Hurricane Electric) to identify declared vs. live transit discrepancies.

## 🚀 Key Capabilities
1. **Automated DIS Upstream Synchronization:**
   - Real-time extraction of declared upstream IIG allocations from BTRC DIS.
   - Intelligent mapping matching Licensee Name, License Category, and ASN.
2. **BGP Live Routing Audit:**
   - Real-time verification of active BGP transit providers.
   - Automated detection of unapproved, undeclared, or missing upstreams.
3. **Regulatory History & Decision Tracking:**
   - Full history of Commission Meeting directives and compliance status.
   - Enforcement & penalty records tracking.
4. **Interactive Dashboard:**
   - Standalone, zero-dependency searchable dashboard deployed via GitHub Pages.
   - Streamlit multi-view analytical application with PDF and Excel export.

---

## 🛠️ Tech Stack & Architecture
- **Language & Engine:** Python 3.14, Streamlit
- **Database:** SQLite3 (`company_master_profile.db`)
- **Excel Automation:** OpenPyXL, Pandas
- **Web Frontend:** HTML5, CSS3 (Modern Glassmorphism & Responsive Table UI), Vanilla JS

---

## 💻 Local Setup & Running
1. **Run Standalone Dashboard:**
   Open `index.html` or `BTRC_Company_Profile_Dashboard.html` in any web browser.
2. **Run Streamlit Web App:**
   ```bash
   pip install -r requirements.txt
   streamlit run company_profile_system/Apps/web_dashboard.py
   ```

---
*© 2026 Bangladesh Telecommunication Regulatory Commission (BTRC). All Rights Reserved.*

