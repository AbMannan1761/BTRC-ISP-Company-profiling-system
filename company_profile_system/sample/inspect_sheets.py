import sys
import urllib.request
import re

sys.stdout.reconfigure(encoding='utf-8')

url = "https://docs.google.com/spreadsheets/d/14xfghrOlfgDNspFHYNaJanuTkDDx_bWLigBwXBGySrU/htmlview"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')

# Search for sheet names
for m in re.finditer(r'item-name">([^<]+)<', html):
    print("Item:", m.group(1))

# Also search around 'sheets' or tabs
items = re.findall(r'<li[^>]*id="sheet-button-([0-9]+)"[^>]*>[\s\S]*?<a[^>]*>([^<]+)</a>', html)
print("Sheet buttons:", items)

# If not found, let's search for sheetId in json or javascript
gids = re.findall(r'(\d+)', '1590013494, 1406070721, 2108297339, 297885144, 1504476267, 1268194833, 1029870126, 1276624078, 550550529, 270094407, 1015475416, 645114449, 1156038807, 1312735838, 2103364223, 381360063')

for gid in gids[:5]:
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/14xfghrOlfgDNspFHYNaJanuTkDDx_bWLigBwXBGySrU/export?format=csv&gid={gid}"
        req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
        csv_data = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        first_line = csv_data.splitlines()[0] if csv_data.splitlines() else ''
        second_line = csv_data.splitlines()[1] if len(csv_data.splitlines()) > 1 else ''
        print(f"GID {gid}: {first_line[:80]} | {second_line[:80]} ({len(csv_data)} bytes)")
    except Exception as e:
        print(f"GID {gid} error: {e}")
