import gspread
import pandas as pd
import json
import os
import time
from datetime import date, timedelta
from google.oauth2.service_account import Credentials

creds_json = os.environ['GOOGLE_CREDENTIALS']
creds_dict = json.loads(creds_json)

scopes = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

SPREADSHEET_ID = '1Kilu8Sn6XQrOMxmpna6m7X6hPGCYagl5QxLUFhg8QmE'
spreadsheet = client.open_by_key(SPREADSHEET_ID)

def excel_serial_to_date(val, dayfirst=True):
    try:
        serial = int(float(str(val)))
        if serial > 40000:
            return (date(1899, 12, 30) + timedelta(days=serial)).strftime('%Y-%m-%d')
    except:
        pass
    try:
        return pd.to_datetime(str(val), dayfirst=dayfirst).strftime('%Y-%m-%d')
    except:
        return val

def read_sheet_robust(worksheet, max_retry=3):
    all_values = []
    for attempt in range(max_retry):
        all_values = worksheet.get_all_values()
        if all_values and len(all_values) > 1:
            break
        print(f"Sheet {worksheet.title} kosong/belum ready, retry {attempt+1}/{max_retry}...")
        time.sleep(5)
    if not all_values or len(all_values) <= 1:
        raise Exception(f"Sheet {worksheet.title} kosong setelah {max_retry} retry")

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

    df = pd.DataFrame(all_values[1:], columns=clean_headers)
    df = df.replace('', None)
    df = df.dropna(how='all')
    return df

# NOTE: LC data (tab DATA) tidak di-pull otomatis karena IMPORTRANGE issue.
# LC data di-update manual via scripts/upload_lc.py atau upload CSV langsung.
print("Skipping LC data pull (managed manually)")

# ── OT DATA ──────────────────────────────────────────────
OT_COLS = [
    'Employee ID', 'Employee Name', 'OT Date', 'Day Name',
    'Total OT Hour', 'minute(s)', 'Status', 'Description', 'Location Name',
    'Organization Name', 'Site BU', 'Kategori Overtime'
]
print("Pulling OT data (tab: Overtime)...")
ws_ot = spreadsheet.worksheet('Overtime')

# Tab Overtime punya 2 header rows - combine untuk dapat nama kolom yang benar
all_vals = ws_ot.get_all_values()
if not all_vals or len(all_vals) < 3:
    print("WARNING: OT tab terlalu sedikit data")
else:
    row1 = all_vals[0]  # header utama
    row2 = all_vals[1]  # sub-header

    # Combine row1 + row2 jadi nama kolom
    combined_headers = []
    seen = {}
    last_r1 = ''
    for i, (h1, h2) in enumerate(zip(row1, row2)):
        h1 = h1.strip()
        h2 = h2.strip()
        if h1:
            last_r1 = h1
        # Kalau ada sub-header, combine
        if h2 and h2 not in ['hour(s)', 'minute(s)', 'In', 'Out']:
            col_name = h2
        elif h2 in ['hour(s)', 'minute(s)']:
            col_name = f"{last_r1} {h2}"
        elif h1:
            col_name = h1
        else:
            col_name = f"_col_{i}"

        # Deduplicate
        if col_name in seen:
            seen[col_name] += 1
            col_name = f"{col_name}_{seen[col_name]}"
        else:
            seen[col_name] = 0
        combined_headers.append(col_name)

    df_ot_raw = pd.DataFrame(all_vals[2:], columns=combined_headers)
    df_ot_raw = df_ot_raw.replace('', None).dropna(how='all')

    print(f"OT columns sample: {combined_headers[:10]}")

    # Map ke nama standar dashboard
    # Cari kolom Total OT Hour hour(s) dan minute(s)
    hour_col = next((c for c in df_ot_raw.columns if 'Total OT Hour' in c and 'hour' in c.lower()), None)
    min_col  = next((c for c in df_ot_raw.columns if 'Total OT Hour' in c and 'minute' in c.lower()), None)

    if hour_col: df_ot_raw = df_ot_raw.rename(columns={hour_col: 'Total OT Hour'})
    if min_col:  df_ot_raw = df_ot_raw.rename(columns={min_col:  'minute(s)'})

    ot_cols_exist = [c for c in OT_COLS if c in df_ot_raw.columns]
    df_ot = df_ot_raw[ot_cols_exist].copy()
    if 'Employee ID' in df_ot.columns:
        df_ot = df_ot[df_ot['Employee ID'].notna() & (df_ot['Employee ID'].astype(str).str.strip() != '')]
    if 'OT Date' in df_ot.columns:
        df_ot['OT Date'] = df_ot['OT Date'].apply(lambda v: excel_serial_to_date(v, dayfirst=False))
    print(f"Sample minute(s): {df_ot['minute(s)'].head(5).tolist() if 'minute(s)' in df_ot.columns else 'NOT FOUND'}")

    if len(df_ot) > 0:
        df_ot.to_csv('data/ot_data.csv', index=False)
        print(f"OT data: {len(df_ot)} rows saved")
    else:
        print("WARNING: OT data kosong, skip overwrite")

# ── TARIKAN KLL ──────────────────────────────────────────
print("Pulling Tarikan KLL data (tab: Tarikan KLL)...")
try:
    ws_kll = spreadsheet.worksheet('Tarikan KLL')
    df_kll_raw = read_sheet_robust(ws_kll)

    def parse_lama_lembur(val):
        try:
            parts = str(val).strip().split(':')
            return int(parts[0]) + int(parts[1])/60
        except:
            return None

    df_kll = pd.DataFrame()
    df_kll['Employee ID'] = df_kll_raw['NIK'].astype(str).str.strip()
    df_kll['Employee Name'] = df_kll_raw['nama_karyawan'].astype(str).str.strip()
    df_kll['OT Date'] = df_kll_raw['Tanggal_Lembur'].apply(lambda v: excel_serial_to_date(v, dayfirst=False))
    lama_jam = df_kll_raw['Lama_Lembur_SPL'].apply(parse_lama_lembur)
    df_kll['Total OT Hour'] = lama_jam.apply(lambda x: int(x) if pd.notna(x) else 0)
    df_kll['minute(s)'] = lama_jam.apply(lambda x: round((x - int(x)) * 60) if pd.notna(x) else 0)
    df_kll['Status'] = 'Approved'
    df_kll['Description'] = df_kll_raw['Description'].fillna('')
    df_kll['Location Name'] = df_kll_raw['Facility'].apply(
        lambda x: 'DC CIKARANG JABABEKA (KLS)' if 'KLS' in str(x).upper() else 'DC CIKARANG JABABEKA (AHI)'
    )
    df_kll['Organization Name'] = df_kll_raw['Facility'].apply(
        lambda x: f"SLT-OPERATION-PROJECT (DC - {'KLS' if 'KLS' in str(x).upper() else 'AHI'})-DC JABABEKA"
    )
    df_kll['Site BU'] = df_kll_raw['Facility'].astype(str).str.strip()
    df_kll['Kategori Overtime'] = df_kll_raw['kategori_overtime'].astype(str).str.strip()
    df_kll = df_kll[df_kll['Employee ID'].notna() & (df_kll['Employee ID'] != '') & (df_kll['Employee ID'] != 'nan')]

    if len(df_kll) > 0:
        df_kll.to_csv('data/tarikan_kll_data.csv', index=False)
        print(f"Tarikan KLL: {len(df_kll)} rows saved")
    else:
        print("WARNING: Tarikan KLL kosong, skip overwrite")
except Exception as e:
    print(f"Tarikan KLL error: {e}")

# ── KLS HO DATA ──────────────────────────────────────────
KLS_HO_COLS = ['Tanggal', 'NIK', 'Nama', 'NO LC']
print("Pulling KLS HO data (tab: KLS HO)...")
try:
    ws_klsho = spreadsheet.worksheet('KLS HO')
    df_klsho_raw = read_sheet_robust(ws_klsho)
    klsho_cols_exist = [c for c in KLS_HO_COLS if c in df_klsho_raw.columns]
    df_klsho = df_klsho_raw[klsho_cols_exist].copy()
    if 'NIK' in df_klsho.columns:
        df_klsho = df_klsho[df_klsho['NIK'].notna() & (df_klsho['NIK'] != '')]
        df_klsho['NIK'] = df_klsho['NIK'].astype(str).str.replace(' ', '').str.strip()
    if 'Tanggal' in df_klsho.columns:
        df_klsho['Tanggal'] = df_klsho['Tanggal'].apply(lambda v: excel_serial_to_date(v, dayfirst=True))

    if len(df_klsho) > 0:
        df_klsho.to_csv('data/kls_ho_data.csv', index=False)
        print(f"KLS HO data: {len(df_klsho)} rows saved")
    else:
        print("WARNING: KLS HO kosong, skip overwrite")
except Exception as e:
    print(f"KLS HO error: {e}")

print("Done.")
