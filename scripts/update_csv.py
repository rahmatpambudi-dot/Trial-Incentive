import gspread
import pandas as pd
import json
import os
from google.oauth2.service_account import Credentials

creds_json = os.environ['GOOGLE_CREDENTIALS']
creds_dict = json.loads(creds_json)

scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

SPREADSHEET_ID = '1Kilu8Sn6XQrOMxmpna6m7X6hPGCYagl5QxLUFhg8QmE'
spreadsheet = client.open_by_key(SPREADSHEET_ID)

# ── LC DATA ──────────────────────────────────────────────
LC_COLS = [
    'TRANSNO', 'PLANDELIVERYDATE', 'AREA', 'TIPE ARMADA', 'JALUR',
    'KATEGORI KIRIMAN', 'DriverId', 'DriverName',
    'DP (STOP)', 'Check Out', 'DP1', 'LastDP', 'Tiba di DC',
    'Travel Time ', '1st - Last DP', 'TAT'
]
print("Pulling LC data (tab: DATA)...")
ws_lc = spreadsheet.worksheet('DATA')
df_lc = pd.DataFrame(ws_lc.get_all_records())
lc_cols_exist = [c for c in LC_COLS if c in df_lc.columns]
df_lc = df_lc[lc_cols_exist]
df_lc.to_csv('data/lc_data.csv', index=False)
print(f"LC data: {len(df_lc)} rows, kolom: {list(df_lc.columns)}")

# ── OT DATA ──────────────────────────────────────────────
OT_COLS = [
    'Employee ID', 'Employee Name', 'OT Date', 'Day Name',
    'Total OT Hour', 'minute(s)', 'Status', 'Description', 'Location Name'
]
print("Pulling OT data (tab: Overtime)...")
ws_ot = spreadsheet.worksheet('Overtime')

# Ambil raw values untuk handle duplikat header
all_values = ws_ot.get_all_values()
if not all_values:
    raise Exception("Tab Overtime kosong")

# Pakai baris pertama sebagai header, deduplicate
raw_headers = all_values[0]
seen = {}
clean_headers = []
for h in raw_headers:
    h = h.strip()
    if h == '' or h in seen:
        seen[h] = seen.get(h, 0) + 1
        clean_headers.append(f"_col_{len(clean_headers)}")
    else:
        seen[h] = 1
        clean_headers.append(h)

df_ot_raw = pd.DataFrame(all_values[1:], columns=clean_headers)
df_ot_raw = df_ot_raw.replace('', None)

# Flexible mapping kolom menit
minute_col = None
for c in df_ot_raw.columns:
    cl = c.lower()
    if 'menit' in cl or 'minute' in cl or 'unnamed: 29' in cl:
        minute_col = c
        break

if minute_col and minute_col != 'minute(s)':
    df_ot_raw = df_ot_raw.rename(columns={minute_col: 'minute(s)'})

ot_cols_exist = [c for c in OT_COLS if c in df_ot_raw.columns]
df_ot = df_ot_raw[ot_cols_exist]
df_ot.to_csv('data/ot_data.csv', index=False)
print(f"OT data: {len(df_ot)} rows, kolom: {list(df_ot.columns)}")

print("Done.")
