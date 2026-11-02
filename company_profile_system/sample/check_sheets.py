import sys
import urllib.request
import re

sys.stdout.reconfigure(encoding='utf-8')

url = "https://docs.google.com/spreadsheets/d/14xfghrOlfgDNspFHYNaJanuTkDDx_bWLigBwXBGySrU/htmlview"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
    print("Google Sheet htmlview length:", len(html))
    # find sheet tabs: items in <ul id="sheet-menu"> or sheetId
    matches = re.findall(r'id="sheet-button-([0-9]+)"[^>]*>([^<]+)<', html)
    print("Found sheet tabs:")
    for gid, name in matches:
        print(f"  - GID: {gid} -> {name}")
    
    if not matches:
        # try regex for name and gid
        gids = re.findall(r'gid=([0-9]+)', html)
        print("Unique GIDs:", set(gids))
except Exception as e:
    print("Error:", e)
