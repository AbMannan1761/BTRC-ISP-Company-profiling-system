import sys
import urllib.request
import re
import json

sys.stdout.reconfigure(encoding='utf-8')

print("Fetching btrc-meeting-portal...")
try:
    req = urllib.request.Request('https://abmannan1761.github.io/btrc-meeting-portal/', headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    print("btrc-meeting-portal HTML length:", len(html))
    scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
    print("Scripts:", scripts)
    jsons = re.findall(r'[\w\./-]+\.json', html)
    print("JSON references:", jsons)
    # Check if there is embedded data in script tags
    script_texts = re.findall(r'<script>([\s\S]*?)</script>', html)
    print("Inline scripts count:", len(script_texts))
    for i, s in enumerate(script_texts):
        if 'decision' in s.lower() or 'meeting' in s.lower() or 'data' in s.lower():
            print(f"Script {i} snippet:", s[:300])
except Exception as e:
    print("Error:", e)
