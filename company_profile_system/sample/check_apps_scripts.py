import sys
import urllib.request
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

# Test penalty endpoint
penalty_url = "https://script.google.com/macros/s/AKfycbw51lYWAnGjvAyG4ub79zyHMkZ3K0fetP4I2e7P6N8HMdsFeeUT_wmUTefmd_ECl2eO/exec"
try:
    print("Fetching penalty endpoint...")
    req = urllib.request.Request(penalty_url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req, timeout=10)
    data = res.read().decode('utf-8')
    print("Penalty response length:", len(data))
    print("Penalty snippet:", data[:300])
except Exception as e:
    print("Penalty fetch error:", e)

# Test inspection endpoint
insp_url = "https://script.google.com/macros/s/AKfycbzFAonxM-nqbUH0m0JCnkk609L186DQSauW3rtSz5YQuUOiFTVZx7IWHU_WJ7KGpA/exec"
try:
    print("\nFetching inspection endpoint...")
    req = urllib.request.Request(insp_url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req, timeout=10)
    data = res.read().decode('utf-8')
    print("Inspection response length:", len(data))
    print("Inspection snippet:", data[:300])
except Exception as e:
    print("Inspection fetch error:", e)
