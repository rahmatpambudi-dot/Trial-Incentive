import gspread
import pandas as pd
import json
import os
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
    """Convert Excel serial number to YYYY-MM-DD string.
    dayfirst controls parsing for string dates (not serial numbers)."""
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

def read_sheet_robust(worksheet):
    """Baca sheet pakai get_all_values - robust terhadap row/header kosong dan duplikat."""
    all_values = worksheet.get_all_values()
    if not all_values:
        raise Exception(f"Sheet {worksheet.title} kosong")

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

# ── LC DATA ──────────────────────────────────────────────
LC_COLS = [
    'TRANSNO', 'PLANDELIVERYDATE', 'AREA', 'TIPE ARMADA', 'JALUR',
    'KATEGORI KIRIMAN', 'DriverId', 'DriverName',
    'DP (STOP)', 'Check Out', 'DP1', 'LastDP', 'Tiba di DC',
    'Travel Time ', '1st - Last DP', 'TAT', 'Owner'
]
print("Pulling LC data (tab: DATA)...")
ws_lc = spreadsheet.worksheet('DATA')
df_lc_raw = read_sheet_robust(ws_lc)
lc_cols_exist = [c for c in LC_COLS if c in df_lc_raw.columns]
df_lc = df_lc_raw[lc_cols_exist].copy()

if 'TRANSNO' in df_lc.columns:
    df_lc = df_lc[df_lc['TRANSNO'].notna() & (df_lc['TRANSNO'] != '')]

if 'PLANDELIVERYDATE' in df_lc.columns:
    df_lc['PLANDELIVERYDATE'] = df_lc['PLANDELIVERYDATE'].apply(excel_serial_to_date)

df_lc.to_csv('data/lc_data.csv', index=False)
print(f"LC data: {len(df_lc)} rows, kolom: {list(df_lc.columns)}")

# ── OT DATA ──────────────────────────────────────────────
OT_COLS = [
    'Employee ID', 'Employee Name', 'OT Date', 'Day Name',
    'Total OT Hour', 'minute(s)', 'Status', 'Description', 'Location Name',
    'Organization Name', 'Site BU', 'Kategori Overtime'
]
print("Pulling OT data (tab: Overtime)...")
ws_ot = spreadsheet.worksheet('Overtime')
df_ot_raw = read_sheet_robust(ws_ot)

minute_col = None
for c in df_ot_raw.columns:
    cl = c.lower()
    if 'menit' in cl or 'minute' in cl or 'unnamed: 29' in cl:
        minute_col = c
        break
if minute_col and minute_col != 'minute(s)':
    df_ot_raw = df_ot_raw.rename(columns={minute_col: 'minute(s)'})

ot_cols_exist = [c for c in OT_COLS if c in df_ot_raw.columns]
df_ot = df_ot_raw[ot_cols_exist].copy()

if 'Employee ID' in df_ot.columns:
    df_ot = df_ot[df_ot['Employee ID'].notna() & (df_ot['Employee ID'] != '')]

if 'OT Date' in df_ot.columns:
    df_ot['OT Date'] = df_ot['OT Date'].apply(lambda v: excel_serial_to_date(v, dayfirst=False))
    print(f"Sample OT Date: {df_ot['OT Date'].head(3).tolist()}")

df_ot.to_csv('data/ot_data.csv', index=False)
print(f"OT data: {len(df_ot)} rows, kolom: {list(df_ot.columns)}")

# ── TARIKAN KLL (sumber OT alternatif kalau tab Overtime belum update) ──
print("Pulling Tarikan KLL data (tab: Tarikan KLL)...")
try:
    ws_kll = spreadsheet.worksheet('Tarikan KLL')
    df_kll_raw = read_sheet_robust(ws_kll)

    def parse_lama_lembur(val):
        """Convert H:MM ke jam desimal"""
        try:
            parts = str(val).strip().split(':')
            return int(parts[0]) + int(parts[1])/60
        except:
            return None

    # Mapping kolom Tarikan KLL → format OT dashboard
    df_kll = pd.DataFrame()
    df_kll['Employee ID'] = df_kll_raw['NIK'].astype(str).str.strip()
    df_kll['Employee Name'] = df_kll_raw['nama_karyawan'].astype(str).str.strip()
    df_kll['OT Date'] = df_kll_raw['Tanggal_Lembur'].apply(lambda v: excel_serial_to_date(v, dayfirst=False))
    
    # Parse LamaLemburKLL ke jam dan menit
    lama_jam = df_kll_raw['LamaLemburKLL'].apply(parse_lama_lembur)
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

    # Drop baris tanpa Employee ID
    df_kll = df_kll[df_kll['Employee ID'].notna() & (df_kll['Employee ID'] != '') & (df_kll['Employee ID'] != 'nan')]

    df_kll.to_csv('data/tarikan_kll_data.csv', index=False)
    print(f"Tarikan KLL: {len(df_kll)} rows saved")
except Exception as e:
    print(f"Tarikan KLL error: {e}")
    pd.DataFrame(columns=['Employee ID','Employee Name','OT Date','Day Name','Total OT Hour','minute(s)','Status','Description','Location Name','Organization Name','Site BU','Kategori Overtime']).to_csv('data/tarikan_kll_data.csv', index=False)

# ── KLS HO DATA (untuk fallback pairing LC khusus BU KLS) ──
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
        df_klsho['Tanggal'] = df_klsho['Tanggal'].apply(excel_serial_to_date)

    df_klsho.to_csv('data/kls_ho_data.csv', index=False)
    print(f"KLS HO data: {len(df_klsho)} rows, kolom: {list(df_klsho.columns)}")
except Exception as e:
    print(f"KLS HO tab tidak ditemukan atau error: {e}")
    pd.DataFrame(columns=KLS_HO_COLS).to_csv('data/kls_ho_data.csv', index=False)

print("Done.")
