import sys
import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings()

sys.stdout.reconfigure(encoding='utf-8')

session = requests.Session()
session.verify = False

# Login
r = session.get("https://dis.btrc.gov.bd/login", timeout=12)
soup = BeautifulSoup(r.text, "html.parser")
tok = soup.find("input", {"name": "_token"}).get("value")
session.post(
    "https://dis.btrc.gov.bd/login",
    data={"_token": tok, "login": "sharmin@btrc.gov.bd", "password": "Btrce&idd1234"},
    timeout=15
)
print("Logged in!")

# Let's inspect isp-operator-wise-report form
r_page = session.get("https://dis.btrc.gov.bd/isp-operator-wise-report", timeout=12)
sp = BeautifulSoup(r_page.text, "html.parser")
tok2 = sp.find("input", {"name": "_token"}).get("value")
print("Report form action:", sp.find("form").get("action") if sp.find("form") else "No form")
print("Form inputs:", [(inp.get('name'), inp.get('type')) for inp in sp.find_all("input")])
print("Selects:", [s.get('name') for s in sp.find_all("select")])

# Let's post with operator 2944
payload = {
    "_token": tok2,
    "client_type": "",
    "client[]": ["2944"],
    "fmonth": "",
    "fyear": ""
}
r_post = session.post("https://dis.btrc.gov.bd/isp-operator-wise-report-get", data=payload, timeout=20)
print("Response code:", r_post.status_code)
print("Response text length:", len(r_post.text))
open("company_profile_system/sample/adn_dis_report.html", "w", encoding="utf-8").write(r_post.text)
print("Saved adn_dis_report.html")

# Parse tables
sp_res = BeautifulSoup(r_post.text, "html.parser")
tables = sp_res.find_all("table")
print("Tables found:", len(tables))
for i, t in enumerate(tables):
    print(f"\n--- Table {i} ---")
    for tr in t.find_all("tr")[:10]:
        print([td.text.strip().replace("\n", " ") for td in tr.find_all(["th", "td"])])
