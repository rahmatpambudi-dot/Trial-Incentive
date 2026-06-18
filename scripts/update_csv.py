import gspread
import pandas as pd
import json
import os
from google.oauth2.service_account import Credentials

# Load credentials dari GitHub Secret
creds_json = os.environ['GOOGLE_CREDENTIALS']
creds_dict = json.loads(creds_json)

# Auth
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
# Ambil hanya kolom yang ada
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
df_ot_raw = pd.DataFrame(ws_ot.get_all_records())

# Flexible mapping — cari kolom menit (bisa beda nama)
minute_col = None
for c in df_ot_raw.columns:
    if 'menit' in c.lower() or 'minute' in c.lower() or 'unnamed: 29' in c.lower():
        minute_col = c
        break

if minute_col and minute_col != 'minute(s)':
    df_ot_raw = df_ot_raw.rename(columns={minute_col: 'minute(s)'})

ot_cols_exist = [c for c in OT_COLS if c in df_ot_raw.columns]
df_ot = df_ot_raw[ot_cols_exist]
df_ot.to_csv('data/ot_data.csv', index=False)
print(f"OT data: {len(df_ot)} rows, kolom: {list(df_ot.columns)}")

print("Done.")
