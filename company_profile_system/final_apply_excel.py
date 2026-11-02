import json
import openpyxl
from openpyxl.styles import Alignment

EXCEL_PATH = 'Network structure, Orange Communication_updated.xlsx'
CACHE_PATH = 'company_profile_system/dis_scraped_cache.json'
SQLITE_DB = 'company_profile_system/Apps/company_master_profile.db'
MASTER_DB_XLSX = 'BTRC_DIS_Master_Database.xlsx'

with open(CACHE_PATH, 'r', encoding='utf-8') as f:
    cache = json.load(f)

wb_master = openpyxl.load_workbook(MASTER_DB_XLSX, data_only=True)
ws_master = wb_master['DIS & BGP Master Database']
master_by_asn = {}
for r in range(2, ws_master.max_row + 1):
    op_id = ws_master.cell(r, 1).value
    name = ws_master.cell(r, 2).value
    asn = ws_master.cell(r, 17).value
    if asn and str(asn).strip():
        master_by_asn[str(asn).strip()] = {
            'op_id': str(op_id).strip() if op_id else '',
            'name': str(name).strip() if name else ''
        }

import sqlite3
conn = sqlite3.connect(SQLITE_DB)
cur = conn.cursor()
cur.execute('SELECT asn, dis_operator_id, canonical_name FROM company_profiles WHERE dis_operator_id IS NOT NULL AND dis_operator_id != ""')
sqlite_by_asn = {row[0].strip(): str(row[1]).strip() for row in cur.fetchall() if row[0]}
conn.close()

MANUAL_OVERRIDES = {
    'AS134424': '3032', # Orange Communication
    'AS135341': '3032', # Orange Communication
    'AS137868': '3494', # Star Internet Service -> M/S Star Internet Services
    'AS147292': '3620', # Microwin Cyber Cafe -> M/s. Microwin Cyber Café
    'AS134971': '3379', # Md. Maniruzzaman Manir t/a Doly IT Corner -> M/s. Doly IT Corner
    'AS134798': '4160', # Hossain Ahmed Masum T/A Alicon Network -> Alicon Network
    'AS135410': '5833', # Voltz System and Solutions -> Voltz System & Solutions
    'AS150384': '5166', # Progresive Enterprise -> Progressive Enterprise
    'AS9825': '5770',   # Sustainable Development Networking Program -> SDNF
    'AS135353': '3500', # MD SHIRAJUL HAIDER T/A Cue Club Technology -> Cue Club Technology
    'AS134236': '3467', # Sheikh Mohammad Zulfiquer t/a Tetrasoft -> Tetrasoft
    'AS135578': '3586', # Muhammad Nasir t/a Dhaka Information Technology -> M/s. Dhaka Information Technology
    'AS24556': '2947',  # Bijoy Online Ltd. Multihome Internet Service Provider -> Bijoy Online Limited
    'AS134180': '3378', # Md. Shariful Islam T/A BRISK SYSTEMS -> Brisk Systems
    'AS135311': '3602', # Golam Mohammad T/A 29Communication -> M/s. 29 Communication
    'AS132092': '3400', # Mir Mosharrof Hossain t/a IT Base -> IT Base
    'AS136272': '3761', # MOHAMMAD ANOWER HOSSAIN t/a SUN ONLINE -> Sun Online
    'AS135604': '3592', # Sharmin Akter Shilpi t/a M/S. Saiba International -> M/s. Saiba International
    'AS137385': '3504', # Saddam Hossain t/a Asian Network -> M/s. Asian Network
    'AS138522': '4153', # Kazi Rajib Ferdous t/a Chocolate Broadband -> Chocolate Broadband
    'AS136732': '3526', # Yellow Net & Cyber Cafe -> Yellow Net
    'AS153432': '5041', # Tongi Online -> Tongi On Line
    'AS140237': '4159', # Speed Net BD -> Speed Net
    'AS149021': '4323', # City Network -> City Network
    'AS137186': '5025', # Universal Friends Communication Network -> Universal Friends Communication Network
    'AS136948': '4950', # Today Vision -> M/s. Today Vision Internet & Dish Network
    'AS149649': '3480', # Speed Touch Network and Technology -> Speed Touch Network & Technology
    'AS154828': '5057', # Airnet Broadband Internet Gateway -> Airnet Broadband Internet
    'AS133957': '3124', # SOL-BD -> M/s. SOL-BD
    'AS140544': '2959', # INNOVATIVE TECHNOLOGY & ENGINEERING -> Innovative Online Limited
    'AS140287': '3478', # OK Network and Communications -> Ok Network & Communications
    'AS138403': '3148', # Bismilla Enterprise -> Bismillah Enterprise
    'AS38256': '3382',  # Bengal Group Ltd. -> Bengal Broadband Ltd.
    'AS139672': '5988', # Cherry Enterprise -> Cherry Enterprice
    'AS149426': '5540', # DDN-Media -> DDN Communication
    'AS138981': '5056', # M/S. SK Net City -> Net City
    'AS38203': '2944',  # ADN Telecom Ltd.
}

wb = openpyxl.load_workbook(EXCEL_PATH)
ws = wb['Sheet2']

updated_count = 0
for r in range(2, ws.max_row + 1):
    asn = str(ws.cell(r, 2).value or '').strip()
    name = str(ws.cell(r, 3).value or '').strip()
    if not name and not asn:
        continue
        
    op_id = None
    if asn in MANUAL_OVERRIDES:
        op_id = MANUAL_OVERRIDES[asn]
    elif asn in master_by_asn:
        op_id = master_by_asn[asn]['op_id']
    elif asn in sqlite_by_asn:
        op_id = sqlite_by_asn[asn]
        
    if op_id and str(op_id) in cache and cache[str(op_id)]['iigs']:
        iigs = cache[str(op_id)]['iigs']
        ws.cell(r, 5).value = "\n".join(iigs)
        ws.cell(r, 5).alignment = Alignment(wrap_text=True, vertical='top')
        updated_count += 1

wb.save(EXCEL_PATH)
print(f"Excel Sheet2 updated! Total rows with Upstrim (DIS): {updated_count}")

