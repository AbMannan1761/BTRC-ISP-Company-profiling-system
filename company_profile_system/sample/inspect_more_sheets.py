import sys
import urllib.request
import re

sys.stdout.reconfigure(encoding='utf-8')

gids = ['1590013494', '1406070721', '2108297339', '297885144', '1504476267', '1268194833', '1029870126', '1276624078', '550550529', '270094407', '1015475416', '645114449', '1156038807', '1312735838', '2103364223', '381360063']

for gid in gids[5:]:
    try:
        csv_url = f"https://docs.google.com/spreadsheets/d/14xfghrOlfgDNspFHYNaJanuTkDDx_bWLigBwXBGySrU/export?format=csv&gid={gid}"
        req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
        csv_data = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        lines = [l.strip() for l in csv_data.splitlines() if l.strip()]
        header = lines[0] if lines else ''
        sub = lines[1] if len(lines) > 1 else ''
        print(f"GID {gid}: {len(csv_data)} bytes | {header[:60]} | {sub[:60]}")
    except Exception as e:
        print(f"GID {gid} error: {e}")
