import requests
from bs4 import BeautifulSoup
import re
import urllib3
import time

urllib3.disable_warnings()

class DISClient:
    BASE_URL = "https://dis.btrc.gov.bd"
    
    def __init__(self, username="sharmin@btrc.gov.bd", password="Btrce&idd1234"):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.is_authenticated = False
        self._token = None
        self._cached_operators = None

    def login(self):
        try:
            r = self.session.get(f"{self.BASE_URL}/login", timeout=12)
            soup = BeautifulSoup(r.text, "html.parser")
            token_elem = soup.find("input", {"name": "_token"})
            if not token_elem:
                return False
            self._token = token_elem.get("value")
            
            resp = self.session.post(
                f"{self.BASE_URL}/login",
                data={
                    "_token": self._token,
                    "login": self.username,
                    "password": self.password
                },
                timeout=15,
                allow_redirects=True
            )
            if "dashboard" in resp.url.lower() or "logout" in resp.text.lower() or "DIS |" in resp.text:
                self.is_authenticated = True
                return True
        except Exception as e:
            print(f"[DISClient] Login error: {e}")
        return False

    def ensure_authenticated(self):
        if not self.is_authenticated:
            return self.login()
        return True

    def get_all_isps_by_type(self):
        """Fetches lightweight operator list across all ISP types (1=Nationwide, 2=Divisional, 3=District, 4=Thana)"""
        if not self.ensure_authenticated():
            return []
        
        type_names = {
            '1': 'Nationwide',
            '2': 'Divisional',
            '3': 'District',
            '4': 'Thana or Upazilla'
        }
        all_isps = []
        for tid, tname in type_names.items():
            try:
                res = self.session.get(f"{self.BASE_URL}/ispByType?id={tid}", timeout=15)
                for item in res.json():
                    all_isps.append({
                        'id': item['id'],
                        'name': item['licensee_name'].strip(),
                        'license_no': item.get('license_no', '').strip(),
                        'category': tname
                    })
            except Exception as e:
                print(f"[DISClient] Error fetching type {tid}: {e}")
        return all_isps

    def get_operator_live_details(self, operator_id):
        """
        Queries live details of a single operator from DIS with targets:
        isp_type, total_upstream, noc_address, contact_personnel, ip_information
        """
        if not self.ensure_authenticated():
            return None

        try:
            # 1. Fetch form token from report page
            r_page = self.session.get(f"{self.BASE_URL}/isp-operator-report", timeout=12)
            sp = BeautifulSoup(r_page.text, "html.parser")
            tok = sp.find("input", {"name": "_token"}).get("value")

            # 2. Submit report query for this specific operator
            payload = {
                "_token": tok,
                "type": "",
                "name[]": [str(operator_id)],
                "division_id": "",
                "district_id": "",
                "thana_id": "",
                "month": "",
                "year": "",
                "target[]": ["isp_type", "total_upstream", "noc_address", "contact_personnel", "ip_information"]
            }
            r_post = self.session.post(f"{self.BASE_URL}/isp-operator-report", data=payload, timeout=20)
            sp_res = BeautifulSoup(r_post.text, "html.parser")
            table = sp_res.find("table")
            if not table:
                return None

            headers = [th.text.strip() for th in table.find_all("th")]
            rows = table.find_all("tr")[1:]
            if not rows:
                return None

            cols = [td.text.strip() for td in rows[0].find_all("td")]
            data_dict = dict(zip(headers, cols))

            # 3. Also query operator-wise report for declared IIG Upstream names
            declared_iigs = self.get_operator_declared_iigs(operator_id)

            # Parse contact personnel details
            raw_contact = data_dict.get("Contact Personnel", "")
            m_name = re.search(r"Name:\s*([^\n\r]+)", raw_contact)
            m_phone = re.search(r"Mobile:\s*([^\n\r]+)", raw_contact)
            m_email = re.search(r"Email:\s*([^\n\r]+)", raw_contact)

            return {
                "dis_operator_id": operator_id,
                "licensee_info": data_dict.get("Licensee Info", "").replace("\n", " ").strip(),
                "license_no": data_dict.get("Licensee No", "").strip(),
                "isp_type": data_dict.get("ISP Type", "").strip(),
                "noc_address": data_dict.get("NOC Address", "").replace("\n", ", ").strip(),
                "contact_person": m_name.group(1).strip() if m_name else "",
                "contact_phone": m_phone.group(1).strip() if m_phone else "",
                "contact_email": m_email.group(1).strip() if m_email else "",
                "total_upstream_mbps": data_dict.get("Total Upstream", "").strip(),
                "buying_price_bdt": data_dict.get("Total Buying Price (BDT)", "").strip(),
                "ipv4_declared": data_dict.get("IPv4", "").strip(),
                "ipv6_declared": data_dict.get("IPv6", "").strip(),
                "declared_iigs": declared_iigs
            }
        except Exception as e:
            print(f"[DISClient] Error fetching details for operator {operator_id}: {e}")
            return None

    def get_operator_declared_iigs(self, operator_id):
        """Queries the Operator Wise Report for declared IIG upstreams"""
        try:
            r_page = self.session.get(f"{self.BASE_URL}/isp-operator-wise-report", timeout=12)
            sp = BeautifulSoup(r_page.text, "html.parser")
            tok = sp.find("input", {"name": "_token"}).get("value")
            
            payload = {
                "_token": tok,
                "client_type": "",
                "client[]": [str(operator_id)],
                "fmonth": "",
                "fyear": ""
            }
            r_post = self.session.post(f"{self.BASE_URL}/isp-operator-wise-report-get", data=payload, timeout=15)
            sp_res = BeautifulSoup(r_post.text, "html.parser")
            tables = sp_res.find_all("table")
            iigs = []
            if tables:
                t = tables[0]
                for tr in t.find_all("tr"):
                    tds = [td.text.strip() for td in tr.find_all("td")]
                    # Column 3 is usually 'Name of IIG'
                    if len(tds) >= 4:
                        iig_name = tds[3].strip()
                        if iig_name and iig_name not in ["No Data Available", "Name of IIG", ""]:
                            if iig_name not in iigs:
                                iigs.append(iig_name)
            return iigs
        except Exception:
            return []
