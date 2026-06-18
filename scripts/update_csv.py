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

# Spreadsheet ID dari URL Google Sheets
# Contoh: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
SPREADSHEET_ID = '1Kilu8Sn6XQrOMxmpna6m7X6hPGCYagl5QxLUFhg8QmE'

spreadsheet = client.open_by_key(SPREADSHEET_ID)

# Pull sheet DATA (LC data)
print("Pulling LC data...")
ws_lc = spreadsheet.worksheet('DATA')  # sesuaikan nama tab
data_lc = ws_lc.get_all_records()
df_lc = pd.DataFrame(data_lc)
df_lc.to_csv('data/lc_data.csv', index=False)
print(f"LC data: {len(df_lc)} rows saved to data/lc_data.csv")

# Pull sheet OT jika ada di Sheets
# ws_ot = spreadsheet.worksheet('Overtime')
# data_ot = ws_ot.get_all_records()
# df_ot = pd.DataFrame(data_ot)
# df_ot.to_csv('data/ot_data.csv', index=False)
# print(f"OT data: {len(df_ot)} rows saved to data/ot_data.csv")

print("Done.")
