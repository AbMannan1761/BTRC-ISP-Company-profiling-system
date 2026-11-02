import openpyxl
import json
from openpyxl.styles import Alignment

with open('company_profile_system/dis_scraped_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

wb = openpyxl.load_workbook('Network structure, Orange Communication_updated.xlsx')
ws = wb['Sheet2']

manual_op_map = {
    142: '5770', # Sustainable Development Networking Program -> SDNF
    215: '2947', # Bijoy Online
    292: '5540', # DDN-Media
    58: '4950',  # Today Vision
    29: '5056',  # SK Net City
    145: '3480', # Speed Touch
    155: '5057', # Airnet Broadband
    229: '3124', # SOL-BD
    232: '2959', # Innovative Online
    233: '2959', # Innovative Online
    254: '3478', # Ok Network
    270: '3148', # Bismillah Enterprise
    271: '3382', # Bengal Broadband
    282: '5988', # Cherry Enterprise
    295: '4810', # Cyber Link Communication
}

for r, op_id in manual_op_map.items():
    if op_id in cache and cache[op_id]['iigs']:
        iigs = cache[op_id]['iigs']
        ws.cell(r, 5).value = '\n'.join(iigs)
        ws.cell(r, 5).alignment = Alignment(wrap_text=True, vertical='top')
        name = ws.cell(r, 3).value
        print(f"Row {r}: {name} -> {iigs}")

wb.save('Network structure, Orange Communication_updated.xlsx')
print("\nExcel successfully updated and saved!")

