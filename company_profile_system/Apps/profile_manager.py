import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

import db_master
from dis_client import DISClient
from bgp_client import BGPClient
from reconciliation import reconcile_upstreams
from exporter import export_single_company, export_bulk_companies

class CompanyProfileManager:
    def __init__(self):
        self.dis = DISClient()
        self.bgp = BGPClient()

    def get_profile(self, query: str, live_revalidate: bool = False):
        """
        1. Checks local cache first (instant response).
        2. If live_revalidate is True, fetches live data from DIS & BGP.
        3. If delta/change is detected, updates local master cache and returns fresh data.
        """
        query = query.strip()
        cached = None
        
        # Check if query is ASN
        if query.upper().startswith("AS"):
            cached = db_master.get_company_by_asn(query.upper())
        else:
            # Search by name
            matches = db_master.search_companies(query)
            if matches:
                cached = matches[0]

        if not live_revalidate and cached:
            asn_val = cached.get("asn", "")
            decisions = db_master.get_commission_decisions(asn_val)
            penalties = db_master.get_penalties(asn_val)
            # Return cached immediately (0 sec load)
            return {
                "source": "local_cache",
                "profile": cached,
                "decisions": decisions,
                "penalties": penalties,
                "delta_updated": False
            }

        # If not in cache or live_revalidate requested
        asn = (cached.get("asn") if cached else (query if query.upper().startswith("AS") else "")).upper()
        if not asn:
            if cached:
                return {"source": "local_cache", "profile": cached, "delta_updated": False}
            return None

        # Fetch Live BGP Data
        bgp_data = self.bgp.get_live_bgp_profile(asn)
        live_upstreams = bgp_data.get("live_upstreams", []) if bgp_data else []
        
        # Fetch Live DIS Data (if operator ID exists or match)
        dis_declared_upstreams = []
        dis_info = None
        op_id = cached.get("dis_operator_id") if cached else None
        
        if op_id:
            dis_info = self.dis.get_operator_live_details(op_id)
            if dis_info and dis_info.get("declared_iigs"):
                dis_declared_upstreams = dis_info["declared_iigs"]
        elif cached and cached.get("dis_declared_upstream"):
            # fallback to existing declared
            dis_declared_upstreams = [u.strip() for u in cached["dis_declared_upstream"].split("\n") if u.strip()]

        # Reconcile & Audit
        audit = reconcile_upstreams(dis_declared_upstreams, live_upstreams)
        
        # Prepare merged profile
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated_data = dict(cached) if cached else {
            "asn": asn,
            "canonical_name": query,
            "license_status": "Unclassified",
            "license_no": ""
        }
        
        # Check for deltas
        old_bgp_up = updated_data.get("bgp_live_upstream", "")
        new_bgp_up = "\n".join(live_upstreams) if live_upstreams else ""
        delta_detected = (old_bgp_up != new_bgp_up)
        
        updated_data["bgp_live_upstream"] = new_bgp_up
        updated_data["bgp_live_upstream_count"] = len(live_upstreams)
        updated_data["bgp_observed_asns"] = ", ".join(bgp_data.get("upstream_asns", [])) if bgp_data else ""
        updated_data["bgp_visibility_v4"] = bgp_data.get("ipv4_visibility", "") if bgp_data else ""
        updated_data["bgp_visibility_v6"] = bgp_data.get("ipv6_visibility", "") if bgp_data else ""
        
        if dis_declared_upstreams:
            updated_data["dis_declared_upstream"] = "\n".join(dis_declared_upstreams)
            updated_data["dis_declared_upstream_count"] = len(dis_declared_upstreams)
            
        if dis_info:
            if dis_info.get("isp_type"):
                updated_data["license_status"] = dis_info["isp_type"]
            if dis_info.get("license_no"):
                updated_data["license_no"] = dis_info["license_no"]
            if dis_info.get("noc_address"):
                updated_data["dis_noc_address"] = dis_info["noc_address"]
            if dis_info.get("contact_person"):
                updated_data["dis_contact_person"] = dis_info["contact_person"]
            if dis_info.get("contact_phone"):
                updated_data["dis_contact_phone"] = dis_info["contact_phone"]
            if dis_info.get("contact_email"):
                updated_data["dis_contact_email"] = dis_info["contact_email"]
            if dis_info.get("total_upstream_mbps"):
                updated_data["dis_bandwidth_mbps"] = dis_info["total_upstream_mbps"]

        updated_data["audit_status"] = audit["audit_status"]
        updated_data["audit_discrepancy"] = audit["discrepancy_desc"]
        updated_data["last_live_checked_at"] = now_str
        
        # Save delta to local master cache immediately
        db_master.save_or_update_company(updated_data)

        # Fetch decisions and penalties
        decisions = db_master.get_commission_decisions(asn)
        penalties = db_master.get_penalties(asn)

        return {
            "source": "live_revalidated",
            "profile": updated_data,
            "decisions": decisions,
            "penalties": penalties,
            "delta_updated": delta_detected,
            "audit_breakdown": audit
        }

    def export_company(self, asn_or_name: str, live_first: bool = False, output_dir: str = None):
        res = self.get_profile(asn_or_name, live_revalidate=live_first)
        if not res or not res.get("profile"):
            return None, "Company profile not found."
        
        filepath = export_single_company(res["profile"], output_dir=output_dir)
        return filepath, res["profile"]

    def export_all(self, category: str = None, output_dir: str = None):
        companies = db_master.get_all_companies(category=category)
        group_name = f"All_Operators_{category}" if category else "All_Companies"
        filepath = export_bulk_companies(companies, output_dir=output_dir, group_name=group_name)
        return filepath, len(companies)
