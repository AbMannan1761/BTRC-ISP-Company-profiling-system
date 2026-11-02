import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
data = open('company_profile_system/sample/check_apps_scripts.py', 'r').read()

# Let's save penalty HTML to a file and inspect it
import urllib.request
req = urllib.request.Request("https://script.google.com/macros/s/AKfycbw51lYWAnGjvAyG4ub79zyHMkZ3K0fetP4I2e7P6N8HMdsFeeUT_wmUTefmd_ECl2eO/exec", headers={'User-Agent': 'Mozilla/5.0'})
content = urllib.request.urlopen(req).read().decode('utf-8')
open('company_profile_system/sample/penalty_app.html', 'w', encoding='utf-8').write(content)

print("Saved penalty_app.html, size:", len(content))
# Find variables, tables, or JSON
for m in re.finditer(r'(?:var|const|let)\s+([a-zA-Z0-9_]+)\s*=\s*(\[|\{)', content):
    var_name = m.group(1)
    print("Found JS variable:", var_name, "at pos", m.start())
