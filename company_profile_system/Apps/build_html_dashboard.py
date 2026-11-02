import os
import sys
import json
import sqlite3
from datetime import datetime

# Path to database
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "company_master_profile.db")
ROOT_DIR = os.path.dirname(os.path.dirname(APP_DIR))
OUTPUT_HTML = os.path.join(ROOT_DIR, "BTRC_Company_Profile_Dashboard.html")

def generate_html_dashboard():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Fetch all companies
    cur.execute("SELECT * FROM company_profiles ORDER BY canonical_name ASC")
    companies = [dict(r) for r in cur.fetchall()]

    # 2. Fetch all commission decisions
    cur.execute("SELECT * FROM commission_decisions ORDER BY decision_date DESC, id DESC")
    decisions = [dict(r) for r in cur.fetchall()]

    # 3. Fetch all penalties
    cur.execute("SELECT * FROM company_penalties ORDER BY penalty_date DESC, id DESC")
    penalties = [dict(r) for r in cur.fetchall()]

    conn.close()

    def clean_name_key(s):
        if not s:
            return ""
        import re
        s = s.strip().lower()
        for drop in ["limited", "ltd.", "ltd", "private", "pvt.", "pvt", "online", "communication", "communications", "internet", "network", "networks", "broadband", "cyber", "technology", "technologies", "tel", "telecom", "it", "link"]:
            s = re.sub(rf'\b{drop}\b', '', s)
        return re.sub(r'[^a-z0-9]', '', s)

    # Group decisions and penalties by ASN & cleaned company name
    decisions_by_asn = {}
    decisions_by_name = {}
    for d in decisions:
        asn = (d.get("asn") or "").strip().upper()
        cname = clean_name_key(d.get("company_name"))
        if asn and asn != "GENERAL":
            decisions_by_asn.setdefault(asn, []).append(d)
        if cname and cname != "general":
            decisions_by_name.setdefault(cname, []).append(d)

    penalties_by_asn = {}
    penalties_by_name = {}
    for p in penalties:
        asn = (p.get("asn") or "").strip().upper()
        cname = clean_name_key(p.get("company_name"))
        if asn and not asn.startswith("NO_ASN"):
            penalties_by_asn.setdefault(asn, []).append(p)
        if cname:
            penalties_by_name.setdefault(cname, []).append(p)

    # Attach to company objects
    for c in companies:
        asn = (c.get("asn") or "").strip().upper()
        cname = clean_name_key(c.get("canonical_name"))
        c_dec = decisions_by_asn.get(asn, [])
        if not c_dec and cname in decisions_by_name:
            c_dec = decisions_by_name[cname]
        c_pen = penalties_by_asn.get(asn, [])
        if not c_pen and cname in penalties_by_name:
            c_pen = penalties_by_name[cname]

        c["decisions"] = c_dec
        c["penalties"] = c_pen

    # Stats calculation
    total_companies = len(companies)
    mismatch_count = sum(1 for c in companies if c.get("audit_status") == "MISMATCH")
    match_count = sum(1 for c in companies if c.get("audit_status") == "MATCH")
    unverified_count = sum(1 for c in companies if c.get("audit_status") == "UNVERIFIED")
    
    total_penalty_bdt = sum(float(p.get("penalty_amount_bdt") or 0) for p in penalties)
    unpaid_penalty_bdt = sum(float(p.get("penalty_amount_bdt") or 0) for p in penalties if p.get("payment_status") != "Paid")
    total_decisions = len(decisions)

    # Serialize to JSON safely
    companies_json = json.dumps(companies, ensure_ascii=False)
    
    # HTML Template
    html_content = f"""<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BTRC কোম্পানি প্রোফাইল ও আপস্ট্রিম অডিট ড্যাশবোর্ড</title>
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a1128;
            --bg-secondary: #001f54;
            --bg-surface: #ffffff;
            --bg-subtle: #f8fafc;
            --border-color: #e2e8f0;
            --border-hover: #cbd5e1;
            
            --brand-primary: #0d3b66;
            --brand-accent: #0077b6;
            --brand-gradient: linear-gradient(135deg, #0a192f 0%, #0d3b66 100%);
            
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #64748b;
            --text-white: #ffffff;
            
            --badge-mismatch-bg: #fee2e2;
            --badge-mismatch-text: #b91c1c;
            --badge-match-bg: #dcfce7;
            --badge-match-text: #15803d;
            --badge-unverified-bg: #fef3c7;
            --badge-unverified-text: #b45309;
            
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', 'Hind Siliguri', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f1f5f9;
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}

        /* Top Header - Slim & Compact */
        header.top-header {{
            background: var(--brand-gradient);
            color: var(--text-white);
            padding: 8px 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 50;
        }}

        .header-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .brand-logo-badge {{
            width: 34px;
            height: 34px;
            background: #ffffff;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        }}

        .brand-title h1 {{
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.2px;
            margin-bottom: 1px;
            color: #ffffff;
        }}

        .brand-title p {{
            font-size: 11px;
            color: #94a3b8;
            font-weight: 500;
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .btn-header {{
            background: rgba(255, 255, 255, 0.12);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.25);
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            text-decoration: none;
        }}

        .btn-header:hover {{
            background: rgba(255, 255, 255, 0.22);
            border-color: rgba(255, 255, 255, 0.4);
        }}

        /* KPI Stats Ribbon - Slim & Elegant Row */
        .kpi-ribbon {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 10px;
            padding: 8px 24px;
            background: #ffffff;
            border-bottom: 1px solid var(--border-color);
        }}

        .kpi-card {{
            background: var(--bg-subtle);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 6px 12px;
            border-left: 3px solid var(--brand-accent);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            transition: all 0.15s ease;
        }}

        .kpi-card:hover {{
            transform: translateY(-1px);
            background: #ffffff;
            box-shadow: var(--shadow-sm);
        }}

        .kpi-label {{
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            letter-spacing: 0.2px;
            line-height: 1.2;
        }}

        .kpi-val {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-primary);
            white-space: nowrap;
        }}

        /* Search & Filter Controls - Compact */
        .controls-bar {{
            padding: 8px 24px;
            background: #ffffff;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .search-box-row {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}

        .search-input-wrapper {{
            position: relative;
            flex: 1;
        }}

        .search-input-wrapper svg {{
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: #94a3b8;
            width: 15px;
            height: 15px;
        }}

        .search-input {{
            width: 100%;
            padding: 8px 12px 8px 34px;
            border-radius: 7px;
            border: 1px solid var(--border-color);
            background: var(--bg-subtle);
            font-size: 13px;
            font-family: inherit;
            color: var(--text-primary);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s, background-color 0.2s;
        }}

        .search-input:focus {{
            border-color: var(--brand-accent);
            background-color: #ffffff;
            box-shadow: 0 0 0 3px rgba(0, 119, 182, 0.12);
        }}

        .view-toggle-group {{
            display: flex;
            background: #e2e8f0;
            padding: 2px;
            border-radius: 6px;
            gap: 2px;
        }}

        .view-btn {{
            border: none;
            background: transparent;
            padding: 5px 12px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }}

        .view-btn.active {{
            background: #ffffff;
            color: var(--brand-primary);
            box-shadow: var(--shadow-sm);
        }}

        .filter-chips-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            align-items: center;
        }}

        .filter-label {{
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            margin-right: 2px;
        }}

        .chip {{
            border: 1px solid var(--border-color);
            background: #ffffff;
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 14px;
            cursor: pointer;
            transition: all 0.15s;
        }}

        .chip:hover {{
            border-color: var(--brand-accent);
            color: var(--brand-accent);
        }}

        .chip.active {{
            background: var(--brand-primary);
            border-color: var(--brand-primary);
            color: #ffffff;
        }}

        /* Main Workspace Content */
        .workspace {{
            flex: 1;
            padding: 12px 24px;
            display: grid;
            gap: 14px;
        }}

        /* Split View Layout */
        .split-layout {{
            display: grid;
            grid-template-columns: 340px 1fr;
            gap: 14px;
            align-items: start;
        }}

        /* Sidebar Company List */
        .company-list-pane {{
            background: #ffffff;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
            display: flex;
            flex-direction: column;
            max-height: calc(100vh - 190px);
            position: sticky;
            top: 75px;
        }}

        .list-header {{
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-subtle);
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
        }}

        .list-header h3 {{
            font-size: 13px;
            font-weight: 700;
            color: var(--text-secondary);
        }}

        .company-mini-card {{
            padding: 8px 10px;
            border-radius: 6px;
            border: 1px solid transparent;
            background: var(--bg-subtle);
            cursor: pointer;
            transition: all 0.15s ease;
            position: relative;
        }}

        .list-header span.badge-count {{
            font-size: 12px;
            font-weight: 700;
            background: #e2e8f0;
            color: var(--text-primary);
            padding: 2px 8px;
            border-radius: 12px;
        }}

        .company-cards-scroll {{
            overflow-y: auto;
            padding: 10px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .company-mini-card {{
            padding: 12px 14px;
            border-radius: 8px;
            border: 1px solid transparent;
            background: var(--bg-subtle);
            cursor: pointer;
            transition: all 0.15s ease;
            position: relative;
        }}

        .company-mini-card:hover {{
            background: #f1f5f9;
            border-color: var(--border-hover);
        }}

        .company-mini-card.active {{
            background: #eff6ff;
            border-color: #3b82f6;
            box-shadow: 0 0 0 1px #3b82f6;
        }}

        .card-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 4px;
        }}

        .mini-card-name {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.3;
            max-width: 250px;
        }}

        .card-badges {{
            display: flex;
            gap: 4px;
        }}

        .badge-status {{
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }}

        .badge-MISMATCH {{
            background: var(--badge-mismatch-bg);
            color: var(--badge-mismatch-text);
        }}

        .badge-MATCH {{
            background: var(--badge-match-bg);
            color: var(--badge-match-text);
        }}

        .badge-UNVERIFIED {{
            background: var(--badge-unverified-bg);
            color: var(--badge-unverified-text);
        }}

        .card-meta {{
            font-size: 12px;
            color: var(--text-muted);
            display: flex;
            gap: 10px;
            align-items: center;
        }}

        .asn-tag {{
            font-family: monospace;
            font-weight: 700;
            color: var(--brand-accent);
        }}

        /* Detail Dossier Pane */
        .detail-pane {{
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .dossier-hero {{
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}

        .dossier-title-area h2 {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 6px;
        }}

        .dossier-meta-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            font-size: 13px;
            color: var(--text-secondary);
        }}

        .tag-pill {{
            background: var(--bg-subtle);
            border: 1px solid var(--border-color);
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 600;
        }}

        .dossier-actions {{
            display: flex;
            gap: 6px;
            align-items: flex-start;
            flex-shrink: 0;
            white-space: nowrap;
        }}

        .btn-action {{
            padding: 4px 9px;
            border-radius: 5px;
            border: 1px solid var(--border-color);
            background: #ffffff;
            font-size: 11.5px;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            white-space: nowrap;
            height: 28px;
            line-height: 1;
            text-decoration: none;
            box-sizing: border-box;
            flex-shrink: 0;
        }}

        .btn-action:hover {{
            background: var(--bg-subtle);
            color: var(--brand-primary);
            border-color: var(--brand-accent);
        }}

        .btn-action.btn-primary {{
            background: var(--brand-primary);
            color: #ffffff;
            border-color: var(--brand-primary);
        }}

        .btn-action.btn-primary:hover {{
            background: #001f54;
        }}

        /* Section Layouts */
        .section-block {{
            background: var(--bg-subtle);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 18px 20px;
        }}

        .section-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--brand-primary);
            margin-bottom: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        /* 3-Pillar Comparison Grid (DIS | bgp.tools | E-I Dashboard) */
        .three-pillar-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            align-items: stretch;
        }}

        @media (max-width: 1150px) {{
            .three-pillar-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .pillar-card {{
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .pillar-card:hover {{
            box-shadow: 0 6px 16px -2px rgba(0, 0, 0, 0.08);
        }}

        .pillar-dis {{
            border-top: 4px solid #0284c7;
        }}

        .pillar-bgp {{
            border-top: 4px solid #7c3aed;
        }}

        .pillar-ei {{
            border-top: 4px solid #059669;
        }}

        .pillar-header {{
            padding: 10px 14px;
            background: #f8fafc;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .pillar-title {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .pillar-icon {{
            font-size: 18px;
        }}

        .pillar-title h3 {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.2;
            margin: 0;
        }}

        .pillar-subtitle {{
            font-size: 11px;
            color: var(--text-muted);
            margin: 0;
        }}

        .pillar-tag {{
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            white-space: nowrap;
        }}

        .tag-blue {{
            background: #e0f2fe;
            color: #0369a1;
            border: 1px solid #bae6fd;
        }}

        .tag-purple {{
            background: #f3e8ff;
            color: #6b21a8;
            border: 1px solid #e9d5ff;
        }}

        .tag-green {{
            background: #dcfce7;
            color: #15803d;
            border: 1px solid #bbf7d0;
        }}

        .tag-red {{
            background: #fee2e2;
            color: #b91c1c;
            border: 1px solid #fecaca;
        }}

        .tag-amber {{
            background: #fef3c7;
            color: #b45309;
            border: 1px solid #fde68a;
        }}

        .pillar-body {{
            padding: 12px 14px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .sub-block {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px 12px;
        }}

        .sub-block-title {{
            font-size: 12px;
            font-weight: 700;
            color: #334155;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .count-pill {{
            font-size: 11px;
            font-weight: 700;
            padding: 1px 7px;
            border-radius: 10px;
        }}

        .pill-blue {{ background: #bae6fd; color: #0284c7; }}
        .pill-purple {{ background: #e9d5ff; color: #7c3aed; }}
        .pill-green {{ background: #bbf7d0; color: #059669; }}
        .pill-red {{ background: #fecaca; color: #dc2626; }}

        .pillar-info-list {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}

        .p-info-row {{
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            padding: 3px 0;
            border-bottom: 1px dashed #e2e8f0;
            gap: 8px;
        }}

        .p-info-row:last-child {{
            border-bottom: none;
        }}

        .p-info-lbl {{
            color: var(--text-muted);
            font-weight: 600;
            flex-shrink: 0;
        }}

        .p-info-val {{
            color: var(--text-primary);
            font-weight: 600;
            text-align: right;
            word-break: break-word;
        }}

        .upstream-list {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 6px;
            max-height: 180px;
            overflow-y: auto;
        }}

        .upstream-list li {{
            font-size: 12px;
            padding: 6px 10px;
            border-radius: 6px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .upstream-list li.match-peer {{
            border-left: 3px solid #16a34a;
            color: #14532d;
        }}

        .upstream-list li.unannounced-peer {{
            border-left: 3px solid #7c3aed;
            background: #faf5ff;
            color: #581c87;
        }}

        .ei-records-scroll {{
            max-height: 180px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .ei-record-item {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 11.5px;
            line-height: 1.35;
        }}

        .pillar-footer {{
            padding: 8px 14px;
            background: #f8fafc;
            border-top: 1px solid var(--border-color);
            display: flex;
            justify-content: center;
        }}

        .pillar-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            width: 100%;
            padding: 7px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            text-decoration: none;
            transition: all 0.2s;
        }}

        .btn-dis {{
            background: #0284c7;
            color: #ffffff;
        }}

        .btn-dis:hover {{
            background: #0369a1;
        }}

        .btn-bgp {{
            background: #7c3aed;
            color: #ffffff;
        }}

        .btn-bgp:hover {{
            background: #6d28d9;
        }}

        .btn-ei {{
            background: #059669;
            color: #ffffff;
        }}

        .btn-ei:hover {{
            background: #047857;
        }}

        .audit-alert-box {{
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
            line-height: 1.5;
        }}

        .alert-MISMATCH {{
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #991b1b;
        }}

        .alert-MATCH {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            color: #166534;
        }}

        .alert-UNVERIFIED {{
            background: #fffbeb;
            border: 1px solid #fde68a;
            color: #92400e;
        }}

        /* Table view */
        .table-container {{
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }}

        table.master-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 13px;
        }}

        table.master-table th {{
            background: #f8fafc;
            color: var(--text-secondary);
            font-weight: 700;
            padding: 12px 16px;
            border-bottom: 2px solid var(--border-color);
            position: sticky;
            top: 0;
        }}

        table.master-table td {{
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-primary);
        }}

        table.master-table tr:hover {{
            background: #f1f5f9;
            cursor: pointer;
        }}

        /* Print Dossier Formatting */
        @media print {{
            header.top-header, .kpi-ribbon, .controls-bar, .company-list-pane, .dossier-actions, .view-toggle-group {{
                display: none !important;
            }}
            body, .workspace, .split-layout {{
                background: white !important;
                padding: 0 !important;
                display: block !important;
            }}
            .detail-pane {{
                border: none !important;
                box-shadow: none !important;
                padding: 0 !important;
            }}
            .section-block {{
                border: 1px solid #ccc !important;
                break-inside: avoid;
            }}
        }}

        /* Empty State */
        .empty-placeholder {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }}

        .empty-placeholder svg {{
            margin-bottom: 12px;
            color: #cbd5e1;
        }}
    </style>
</head>
<body>

    <!-- Header -->
    <header class="top-header">
        <div class="header-brand">
            <div class="brand-logo-badge">🇧🇩</div>
            <div class="brand-title">
                <h1>BTRC কোম্পানি মাস্টার প্রোফাইল ও আপস্ট্রিম অডিট ড্যাশবোর্ড</h1>
                <p>Directorate of Engineering & Inspection (E&I) | বিটিআরসি লাইসেন্সধারী প্রতিষ্ঠান পোর্টাল</p>
            </div>
        </div>
        <div class="header-actions">
            <button class="btn-header" onclick="window.print()">
                🖨️ সম্পূর্ণ রিপোর্ট প্রিন্ট / PDF
            </button>
            <a href="javascript:void(0)" onclick="exportAllCSV()" class="btn-header">
                📥 এক্সেল / CSV ডাউনলোড
            </a>
        </div>
    </header>

    <!-- Top KPI Ribbon -->
    <section class="kpi-ribbon">
        <div class="kpi-card" style="border-left-color: #0284c7;">
            <div class="kpi-label">মোট অপারেটর</div>
            <div class="kpi-val">{total_companies} টি</div>
        </div>
        <div class="kpi-card" style="border-left-color: #ef4444;">
            <div class="kpi-label">আপস্ট্রিম অসঙ্গতি (Mismatch)</div>
            <div class="kpi-val" style="color: #dc2626;">{mismatch_count} টি</div>
        </div>
        <div class="kpi-card" style="border-left-color: #10b981;">
            <div class="kpi-label">যাচাইকৃত সামঞ্জস্য (Match)</div>
            <div class="kpi-val" style="color: #16a34a;">{match_count} টি</div>
        </div>
        <div class="kpi-card" style="border-left-color: #8b5cf6;">
            <div class="kpi-label">কমিশন সিদ্ধান্ত রেকর্ড</div>
            <div class="kpi-val" style="color: #7c3aed;">{total_decisions} টি</div>
        </div>
        <div class="kpi-card" style="border-left-color: #f59e0b;">
            <div class="kpi-label">মোট আরোপিত জরিমানা</div>
            <div class="kpi-val" style="color: #d97706;">৳ {total_penalty_bdt:,.0f}</div>
        </div>
        <div class="kpi-card" style="border-left-color: #dc2626;">
            <div class="kpi-label">বকেয়া জরিমানা</div>
            <div class="kpi-val" style="color: #dc2626;">৳ {unpaid_penalty_bdt:,.0f}</div>
        </div>
    </section>

    <!-- Search & Control Bar -->
    <section class="controls-bar">
        <div class="search-box-row">
            <div class="search-input-wrapper">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input type="text" id="searchInput" class="search-input" placeholder="কোম্পানির নাম, ASN (যেমন: AS137453), লাইসেন্স নম্বর, অথবা আপস্ট্রিম লিখে সার্চ করুন..." oninput="handleSearch()">
            </div>
            <div class="view-toggle-group">
                <button id="btnViewSplit" class="view-btn active" onclick="setViewMode('split')">🔲 প্রোফাইল ভিউ</button>
                <button id="btnViewTable" class="view-btn" onclick="setViewMode('table')">📋 ফুল টেবিল ভিউ</button>
            </div>
        </div>

        <div class="filter-chips-row">
            <span class="filter-label">ক্যাটাগরি:</span>
            <button class="chip active" data-cat="all" onclick="filterCategory('all', this)">সকল ({total_companies})</button>
            <button class="chip" data-cat="Nationwide" onclick="filterCategory('Nationwide', this)">Nationwide</button>
            <button class="chip" data-cat="Divisional" onclick="filterCategory('Divisional', this)">Divisional</button>
            <button class="chip" data-cat="District" onclick="filterCategory('District', this)">District</button>
            <button class="chip" data-cat="Thana or Upazilla" onclick="filterCategory('Thana or Upazilla', this)">Thana/Upazilla</button>
            <button class="chip" data-cat="IIG" onclick="filterCategory('IIG', this)">IIG</button>
            
            <span class="filter-label" style="margin-left: 12px;">অডিট স্ট্যাটাস:</span>
            <button class="chip" data-audit="MISMATCH" onclick="filterAudit('MISMATCH', this)">⚠️ Mismatch ({mismatch_count})</button>
            <button class="chip" data-audit="MATCH" onclick="filterAudit('MATCH', this)">✅ Match ({match_count})</button>
            <button class="chip" data-audit="UNVERIFIED" onclick="filterAudit('UNVERIFIED', this)">⏳ Unverified ({unverified_count})</button>
            <button class="chip" data-audit="all" onclick="filterAudit('all', this)" style="display:none;" id="resetAuditChip">অডিট ফিল্টার রিসেট</button>
        </div>
    </section>

    <!-- Main Workspace -->
    <main class="workspace">
        
        <!-- View 1: Split Dossier View -->
        <div id="splitViewContainer" class="split-layout">
            
            <!-- Left Company Cards List -->
            <aside class="company-list-pane">
                <div class="list-header">
                    <h3>অপারেটর তালিকা</h3>
                    <span id="filteredCountBadge" class="badge-count">{total_companies} টি</span>
                </div>
                <div id="companyCardsScroll" class="company-cards-scroll">
                    <!-- Dynamic mini cards rendered via JS -->
                </div>
            </aside>

            <!-- Right Detail Dossier -->
            <article id="detailPane" class="detail-pane">
                <!-- Dynamic active profile rendered via JS -->
            </article>

        </div>

        <!-- View 2: Full Master Table View -->
        <div id="tableViewContainer" class="table-container" style="display: none;">
            <table class="master-table">
                <thead>
                    <tr>
                        <th>ASN</th>
                        <th>প্রতিষ্ঠানের নাম</th>
                        <th>লাইসেন্স ধরণ</th>
                        <th>লাইসেন্স নম্বর</th>
                        <th>DIS আপস্ট্রিম</th>
                        <th>লাইভ BGP আপস্ট্রিম</th>
                        <th>অডিট স্ট্যাটাস</th>
                        <th>কমিশন সিদ্ধান্ত</th>
                        <th>জরিমানা</th>
                    </tr>
                </thead>
                <tbody id="masterTableBody">
                    <!-- Dynamic Table Rows rendered via JS -->
                </tbody>
            </table>
        </div>

    </main>

    <!-- Embedded Master Data -->
    <script>
        const ALL_COMPANIES = {companies_json};
        let currentFiltered = [...ALL_COMPANIES];
        let activeAsn = ALL_COMPANIES.length > 0 ? ALL_COMPANIES[0].asn : null;
        let selectedCategory = 'all';
        let selectedAudit = 'all';
        let currentSearchQuery = '';

        // Initialize on load
        document.addEventListener('DOMContentLoaded', () => {{
            renderCardsList();
            if (activeAsn) {{
                selectCompany(activeAsn);
            }}
        }});

        function setViewMode(mode) {{
            const splitCont = document.getElementById('splitViewContainer');
            const tableCont = document.getElementById('tableViewContainer');
            const btnSplit = document.getElementById('btnViewSplit');
            const btnTable = document.getElementById('btnViewTable');

            if (mode === 'table') {{
                splitCont.style.display = 'none';
                tableCont.style.display = 'block';
                btnSplit.classList.remove('active');
                btnTable.classList.add('active');
                renderMasterTable();
            }} else {{
                splitCont.style.display = 'grid';
                tableCont.style.display = 'none';
                btnSplit.classList.add('active');
                btnTable.classList.remove('active');
            }}
        }}

        function handleSearch() {{
            currentSearchQuery = document.getElementById('searchInput').value.trim().toLowerCase();
            applyFilters();
        }}

        function filterCategory(cat, element) {{
            document.querySelectorAll('.filter-chips-row button[data-cat]').forEach(b => b.classList.remove('active'));
            element.classList.add('active');
            selectedCategory = cat;
            applyFilters();
        }}

        function filterAudit(audit, element) {{
            if (selectedAudit === audit && audit !== 'all') {{
                selectedAudit = 'all';
                element.classList.remove('active');
                document.getElementById('resetAuditChip').style.display = 'none';
            }} else {{
                document.querySelectorAll('.filter-chips-row button[data-audit]').forEach(b => b.classList.remove('active'));
                element.classList.add('active');
                selectedAudit = audit;
                if (audit !== 'all') {{
                    document.getElementById('resetAuditChip').style.display = 'inline-block';
                }}
            }}
            applyFilters();
        }}

        function applyFilters() {{
            currentFiltered = ALL_COMPANIES.filter(c => {{
                // Comprehensive instant search query match
                const name = (c.canonical_name || '').toLowerCase();
                const asn = (c.asn || '').toLowerCase();
                const lic = (c.license_no || '').toLowerCase();
                const disId = String(c.dis_operator_id || '').toLowerCase();
                const disUp = (c.dis_declared_upstream || '').toLowerCase();
                const bgpUp = (c.bgp_live_upstream || '').toLowerCase();
                const addr = (c.dis_noc_address || '').toLowerCase();
                const contact = (c.dis_contact_person || '').toLowerCase();
                const penaltiesText = (c.penalties || []).map(p => (p.violation_category || '') + ' ' + (p.remarks || '') + ' ' + (p.letter_ref_no || '')).join(' ').toLowerCase();
                const decisionsText = (c.decisions || []).map(d => (d.subject || '') + ' ' + (d.decision_summary || '') + ' ' + (d.meeting_no || '')).join(' ').toLowerCase();

                const matchQuery = !currentSearchQuery || 
                    name.includes(currentSearchQuery) || 
                    asn.includes(currentSearchQuery) || 
                    lic.includes(currentSearchQuery) ||
                    disId.includes(currentSearchQuery) ||
                    disUp.includes(currentSearchQuery) ||
                    bgpUp.includes(currentSearchQuery) ||
                    addr.includes(currentSearchQuery) ||
                    contact.includes(currentSearchQuery) ||
                    penaltiesText.includes(currentSearchQuery) ||
                    decisionsText.includes(currentSearchQuery);

                // Category match
                const matchCat = selectedCategory === 'all' || (c.license_status || '').toLowerCase() === selectedCategory.toLowerCase();

                // Audit match
                const matchAudit = selectedAudit === 'all' || (c.audit_status || '') === selectedAudit;

                return matchQuery && matchCat && matchAudit;
            }});

            document.getElementById('filteredCountBadge').textContent = `${{currentFiltered.length}} টি`;
            renderCardsList();

            // Auto-select first in list if previous active is filtered out
            if (currentFiltered.length > 0) {{
                const exists = currentFiltered.some(c => c.asn === activeAsn);
                if (!exists) {{
                    selectCompany(currentFiltered[0].asn);
                }}
            }} else {{
                renderEmptyDossier();
            }}

            if (document.getElementById('tableViewContainer').style.display !== 'none') {{
                renderMasterTable();
            }}
        }}

        function renderCardsList() {{
            const listEl = document.getElementById('companyCardsScroll');
            if (currentFiltered.length === 0) {{
                listEl.innerHTML = `<div class="empty-placeholder"><p>কোনো অপারেটর মেলেনি</p></div>`;
                return;
            }}

            let html = '';
            currentFiltered.forEach(c => {{
                const isActive = c.asn === activeAsn ? 'active' : '';
                const auditClass = `badge-${{c.audit_status || 'UNVERIFIED'}}`;
                const auditIcon = c.audit_status === 'MISMATCH' ? '⚠️' : (c.audit_status === 'MATCH' ? '✅' : '⏳');

                html += `
                <div class="company-mini-card ${{isActive}}" onclick="selectCompany('${{c.asn}}')">
                    <div class="card-top">
                        <div class="mini-card-name">${{escapeHtml(c.canonical_name)}}</div>
                        <span class="badge-status ${{auditClass}}">${{auditIcon}} ${{c.audit_status}}</span>
                    </div>
                    <div class="card-meta">
                        <span class="asn-tag">${{c.asn || 'N/A'}}</span>
                        <span>•</span>
                        <span>${{escapeHtml(c.license_status || 'Unclassified')}}</span>
                    </div>
                </div>
                `;
            }});
            listEl.innerHTML = html;
        }}

        function selectCompany(asn) {{
            activeAsn = asn;
            const comp = ALL_COMPANIES.find(c => c.asn === asn);
            if (!comp) return;

            // Highlight in list
            document.querySelectorAll('.company-mini-card').forEach(el => el.classList.remove('active'));
            // Re-render dossier
            renderDossier(comp);

            // Add active class to selected mini-card
            const activeCard = Array.from(document.querySelectorAll('.company-mini-card')).find(el => el.textContent.includes(asn));
            if (activeCard) activeCard.classList.add('active');
        }}

        function renderDossier(c) {{
            const pane = document.getElementById('detailPane');
            const auditBadgeClass = `badge-${{c.audit_status || 'UNVERIFIED'}}`;
            const auditIcon = c.audit_status === 'MISMATCH' ? '⚠️' : (c.audit_status === 'MATCH' ? '✅' : '⏳');

            // Format upstreams
            const disList = (c.dis_declared_upstream || '').split('\\n').filter(s => s.trim());
            const bgpList = (c.bgp_live_upstream || '').split('\\n').filter(s => s.trim());

            let disItemsHtml = disList.length > 0 ? 
                disList.map(u => `<li class="match-peer">🏢 <b>${{escapeHtml(u)}}</b></li>`).join('') :
                `<li style="color:#94a3b8; font-style:italic;">ডিআইএস পোর্টালে কোনো আপস্ট্রিম ঘোষণা নেই</li>`;

            let bgpItemsHtml = bgpList.length > 0 ? 
                bgpList.map(u => `<li class="unannounced-peer">📡 <b>${{escapeHtml(u)}}</b></li>`).join('') :
                `<li style="color:#94a3b8; font-style:italic;">লাইভ BGP তে কোনো সক্রিয় রুট পাওয়া যায়নি</li>`;

            // Decisions HTML
            let decisionsHtml = '';
            if (c.decisions && c.decisions.length > 0) {{
                decisionsHtml = c.decisions.map(d => `
                    <div class="ei-record-item">
                        <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                            <span style="font-weight:700; color:#0f172a;">${{escapeHtml(d.meeting_no || 'কমিশন সভা')}} (${{d.decision_date || 'N/A'}})</span>
                            <span style="background:#dcfce7; color:#15803d; padding:1px 6px; border-radius:4px; font-weight:700; font-size:10px;">${{d.compliance_status || 'গৃহীত'}}</span>
                        </div>
                        <div style="color:#1e293b; font-weight:600; margin-bottom:2px;">বিষয়: ${{escapeHtml(d.subject || 'N/A')}}</div>
                        <div style="color:#475569; font-size:11px;"><b>সিদ্ধান্ত:</b> ${{escapeHtml(d.decision_summary || d.directive_issued || 'N/A')}}</div>
                    </div>
                `).join('');
            }} else {{
                decisionsHtml = `<p style="font-size:12px; color:#94a3b8; padding:6px 0; font-style:italic;">এই প্রতিষ্ঠানের জন্য কমিশন সভার কোনো সিদ্ধান্তের রেকর্ড নেই।</p>`;
            }}

            // Penalties HTML
            let penaltiesHtml = '';
            if (c.penalties && c.penalties.length > 0) {{
                penaltiesHtml = c.penalties.map(p => `
                    <div class="ei-record-item">
                        <div style="display:flex; justify-content:space-between; margin-bottom:3px;">
                            <span style="font-weight:700; color:#dc2626; font-size:12px;">৳ ${{Number(p.penalty_amount_bdt || 0).toLocaleString()}}</span>
                            <span style="background:${{p.payment_status === 'Paid' ? '#dcfce7' : '#fee2e2'}}; color:${{p.payment_status === 'Paid' ? '#166534' : '#991b1b'}}; padding:1px 6px; border-radius:4px; font-weight:700; font-size:10px;">${{p.payment_status || 'বকেয়া'}}</span>
                        </div>
                        <div style="color:#1e293b; font-weight:600; margin-bottom:2px;">লঙ্ঘন: ${{escapeHtml(p.violation_category || 'প্রশাসনিক জরিমানা')}}</div>
                        <div style="color:#64748b; font-size:11px;">তারিখ/সভা: ${{p.penalty_date || 'N/A'}} | সূত্র: ${{escapeHtml(p.letter_ref_no || 'E-I ড্যাশবোর্ড')}}</div>
                    </div>
                `).join('');
            }} else {{
                penaltiesHtml = `<p style="font-size:12px; color:#94a3b8; padding:6px 0; font-style:italic;">এই প্রতিষ্ঠানের বিরুদ্ধে কোনো জরিমানা বা শাস্তিমূলক রেকর্ড নেই।</p>`;
            }}

            pane.innerHTML = `
                <!-- Dossier Hero Header -->
                <div class="dossier-hero">
                    <div class="dossier-title-area">
                        <h2>${{escapeHtml(c.canonical_name)}}</h2>
                        <div class="dossier-meta-tags">
                            <span class="tag-pill" style="color:#0284c7; font-weight:700;">ASN: ${{c.asn || 'N/A'}}</span>
                            <span class="tag-pill">ক্যাটাগরি: ${{escapeHtml(c.license_status || 'N/A')}}</span>
                            <span class="tag-pill">লাইসেন্স নং: ${{escapeHtml(c.license_no || 'N/A')}}</span>
                            <span class="tag-pill">DIS আইডি: ${{c.dis_operator_id || 'N/A'}}</span>
                            <span class="badge-status ${{auditBadgeClass}}" style="font-size:12px; padding:4px 10px;">${{auditIcon}} ${{c.audit_status}}</span>
                        </div>
                    </div>
                    <div class="dossier-actions">
                        <button class="btn-action btn-primary" onclick="window.print()">🖨️ ডসিয়ার প্রিন্ট</button>
                        <a href="https://bgp.tools/as/${{c.asn}}" target="_blank" class="btn-action">🌐 bgp.tools</a>
                    </div>
                </div>

                <!-- 3-Pillar Side-by-Side Comparison Grid (DIS | bgp.tools | E-I Dashboard) -->
                <div class="three-pillar-grid">

                    <!-- PILLAR 1: DIS Portal (Left Box) -->
                    <div class="pillar-card pillar-dis">
                        <div class="pillar-header">
                            <div class="pillar-title">
                                <span class="pillar-icon">📋</span>
                                <div>
                                    <h3>DIS পোর্টাল</h3>
                                    <p class="pillar-subtitle">ঘোষিত আপস্ট্রিম ও লাইসেন্স তথ্য</p>
                                </div>
                            </div>
                            <span class="pillar-tag tag-blue">DIS ID: ${{c.dis_operator_id || 'N/A'}}</span>
                        </div>
                        <div class="pillar-body">
                            <div class="sub-block">
                                <div class="sub-block-title">
                                    <span>ঘোষিত আপস্ট্রিম তালিকা</span>
                                    <span class="count-pill pill-blue">${{disList.length}} টি</span>
                                </div>
                                <ul class="upstream-list">
                                    ${{disItemsHtml}}
                                </ul>
                            </div>
                            <div class="sub-block">
                                <div class="sub-block-title">প্রাতিষ্ঠানিক ও লাইসেন্স প্রোফাইল</div>
                                <div class="pillar-info-list">
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">লাইসেন্স নম্বর:</span>
                                        <span class="p-info-val">${{escapeHtml(c.license_no || 'N/A')}}</span>
                                    </div>
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">অনুমোদিত ব্যান্ডউইডথ:</span>
                                        <span class="p-info-val">${{c.dis_bandwidth_mbps ? c.dis_bandwidth_mbps + ' Mbps' : 'N/A'}}</span>
                                    </div>
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">এনওসি / অফিস ঠিকানা:</span>
                                        <span class="p-info-val">${{escapeHtml(c.dis_noc_address || 'তথ্য সংরক্ষিত নেই')}}</span>
                                    </div>
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">ফোকাল পার্সন:</span>
                                        <span class="p-info-val">${{escapeHtml(c.dis_contact_person || 'N/A')}}</span>
                                    </div>
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">মোবাইল / ফোন:</span>
                                        <span class="p-info-val">${{escapeHtml(c.dis_contact_phone || 'N/A')}}</span>
                                    </div>
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">ইমেইল:</span>
                                        <span class="p-info-val">${{escapeHtml(c.dis_contact_email || 'N/A')}}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="pillar-footer">
                            <a href="https://dis.btrc.gov.bd" target="_blank" class="pillar-btn btn-dis">
                                <span>🔗 DIS পোর্টালে যান</span>
                            </a>
                        </div>
                    </div>

                    <!-- PILLAR 2: bgp.tools (Middle Box) -->
                    <div class="pillar-card pillar-bgp">
                        <div class="pillar-header">
                            <div class="pillar-title">
                                <span class="pillar-icon">📡</span>
                                <div>
                                    <h3>bgp.tools</h3>
                                    <p class="pillar-subtitle">লাইভ BGP রাউটিং ও ট্রানজিট</p>
                                </div>
                            </div>
                            <span class="pillar-tag tag-purple">ASN: ${{c.asn || 'N/A'}}</span>
                        </div>
                        <div class="pillar-body">
                            <div class="sub-block">
                                <div class="sub-block-title">
                                    <span>লাইভ BGP আপস্ট্রিম প্রভাইডার</span>
                                    <span class="count-pill pill-purple">${{bgpList.length}} টি</span>
                                </div>
                                <ul class="upstream-list">
                                    ${{bgpItemsHtml}}
                                </ul>
                            </div>
                            <div class="sub-block">
                                <div class="sub-block-title">BGP রাউটিং ও নেটওয়ার্ক স্ট্যাটাস</div>
                                <div class="pillar-info-list">
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">রাউটিং অবস্থা:</span>
                                        <span class="p-info-val">${{bgpList.length > 0 ? '<span style="color:#16a34a; font-weight:700;">🟢 লাইভ সক্রিয়</span>' : '<span style="color:#94a3b8;">⚪ বিজিপি রুটহীন</span>'}}</span>
                                    </div>
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">IPv4 প্রিফিক্স:</span>
                                        <span class="p-info-val">${{c.bgp_ipv4_prefixes !== undefined ? c.bgp_ipv4_prefixes : (bgpList.length > 0 ? 'সক্রিয়' : '0')}} টি</span>
                                    </div>
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">IPv6 প্রিফিক্স:</span>
                                        <span class="p-info-val">${{c.bgp_ipv6_prefixes || '0'}} টি</span>
                                    </div>
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">অটোনোমাস নেটওয়ার্ক:</span>
                                        <span class="p-info-val">${{escapeHtml(c.bgp_network_name || c.canonical_name || 'N/A')}}</span>
                                    </div>
                                    <div class="p-info-row">
                                        <span class="p-info-lbl">সর্বশেষ BGP স্ক্যান:</span>
                                        <span class="p-info-val">${{c.last_cached_at ? c.last_cached_at.split('T')[0] : 'আজকের লাইভ'}}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="pillar-footer">
                            <a href="https://bgp.tools/as/${{c.asn}}" target="_blank" class="pillar-btn btn-bgp">
                                <span>🌐 bgp.tools লাইভ রুট দেখুন</span>
                            </a>
                        </div>
                    </div>

                    <!-- PILLAR 3: E-I Dashboard (Right Box) -->
                    <div class="pillar-card pillar-ei">
                        <div class="pillar-header">
                            <div class="pillar-title">
                                <span class="pillar-icon">⚖️</span>
                                <div>
                                    <h3>E-I ড্যাশবোর্ড</h3>
                                    <p class="pillar-subtitle">আইনি, অডিট ও সিদ্ধান্ত রেকর্ড</p>
                                </div>
                            </div>
                            <span class="pillar-tag ${{c.audit_status === 'MATCH' ? 'tag-green' : (c.audit_status === 'MISMATCH' ? 'tag-red' : 'tag-amber')}}">
                                ${{auditIcon}} ${{c.audit_status || 'UNVERIFIED'}}
                            </span>
                        </div>
                        <div class="pillar-body">
                            <div class="sub-block">
                                <div class="sub-block-title">
                                    <span>কমিশন সভার সিদ্ধান্তসমূহ</span>
                                    <span class="count-pill pill-green">${{c.decisions ? c.decisions.length : 0}} টি</span>
                                </div>
                                <div class="ei-records-scroll">
                                    ${{decisionsHtml}}
                                </div>
                            </div>
                            <div class="sub-block">
                                <div class="sub-block-title">
                                    <span>আরোপিত প্রশাসনিক জরিমানা</span>
                                    <span class="count-pill pill-red">${{c.penalties ? c.penalties.length : 0}} টি</span>
                                </div>
                                <div class="ei-records-scroll">
                                    ${{penaltiesHtml}}
                                </div>
                            </div>
                        </div>
                        <div class="pillar-footer">
                            <a href="https://abmannan1761.github.io/E-I-dashboard/" target="_blank" class="pillar-btn btn-ei">
                                <span>🏛️ E-I সেন্ট্রাল ড্যাশবোর্ড খুলুন</span>
                            </a>
                        </div>
                    </div>

                </div>

                <!-- Overall Audit Summary Bar -->
                <div class="audit-alert-box alert-${{c.audit_status || 'UNVERIFIED'}}" style="margin-top:16px;">
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                        <span style="font-size:18px;">${{auditIcon}}</span>
                        <span style="font-size:14px; font-weight:700;">সামগ্রিক আপস্ট্রিম নিরীক্ষা সারসংক্ষেপ (BTRC E&I Audit Summary)</span>
                    </div>
                    <div style="font-size:12.5px; margin-left:26px;">
                        <b>পর্যবেক্ষণ:</b> ${{escapeHtml(c.audit_discrepancy || 'DIS ঘোষিত আপস্ট্রিম এবং bgp.tools লাইভ BGP আপস্ট্রিমের মধ্যে কোনো অসঙ্গতি নেই।')}}
                    </div>
                </div>
            `;
        }}

        function renderEmptyDossier() {{
            document.getElementById('detailPane').innerHTML = `
                <div class="empty-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="8" y1="12" x2="16" y2="12"></line>
                    </svg>
                    <h3>কোনো অপারেটর নির্বাচিত নেই</h3>
                    <p>অনুসন্ধানের শব্দ পরিবর্তন করুন বা অন্য কোনো ক্যাটাগরি ফিল্টার করুন।</p>
                </div>
            `;
        }}

        function renderMasterTable() {{
            const tbody = document.getElementById('masterTableBody');
            if (currentFiltered.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:30px; color:#94a3b8;">কোনো ডাটা পাওয়া যায়নি</td></tr>`;
                return;
            }}

            let html = '';
            currentFiltered.forEach(c => {{
                const auditBadge = `<span class="badge-status badge-${{c.audit_status || 'UNVERIFIED'}}">${{c.audit_status || 'UNVERIFIED'}}</span>`;
                const decCount = c.decisions ? c.decisions.length : 0;
                const penCount = c.penalties ? c.penalties.length : 0;

                html += `
                <tr onclick="selectCompanyAndSwitch('${{c.asn}}')">
                    <td><b style="color:#0284c7; font-family:monospace;">${{c.asn || 'N/A'}}</b></td>
                    <td><b>${{escapeHtml(c.canonical_name)}}</b></td>
                    <td>${{escapeHtml(c.license_status || '')}}</td>
                    <td>${{escapeHtml(c.license_no || 'N/A')}}</td>
                    <td>${{c.dis_declared_upstream_count || 0}} টি</td>
                    <td>${{c.bgp_live_upstream_count || 0}} টি</td>
                    <td>${{auditBadge}}</td>
                    <td>${{decCount > 0 ? `<b style="color:#7c3aed;">${{decCount}} টি</b>` : '-'}}</td>
                    <td>${{penCount > 0 ? `<b style="color:#dc2626;">${{penCount}} টি</b>` : '-'}}</td>
                </tr>
                `;
            }});
            tbody.innerHTML = html;
        }}

        function selectCompanyAndSwitch(asn) {{
            setViewMode('split');
            selectCompany(asn);
        }}

        function exportAllCSV() {{
            let csv = "ASN,Company Name,License Status,License No,DIS Upstream Count,BGP Upstream Count,Audit Status\\n";
            currentFiltered.forEach(c => {{
                csv += `"${{c.asn || ''}}","${{(c.canonical_name || '').replace(/"/g, '""')}}","${{c.license_status || ''}}","${{c.license_no || ''}}",${{c.dis_declared_upstream_count || 0}},${{c.bgp_live_upstream_count || 0}},"${{c.audit_status || ''}}"\\n`;
            }});

            const blob = new Blob(["\\uFEFF" + csv], {{ type: 'text/csv;charset=utf-8;' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `BTRC_Operators_Export_${{new Date().toISOString().slice(0,10)}}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }}

        function escapeHtml(str) {{
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }}
    </script>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Standalone HTML Dashboard successfully generated: {OUTPUT_HTML} ({len(html_content)} bytes)")

if __name__ == "__main__":
    generate_html_dashboard()
