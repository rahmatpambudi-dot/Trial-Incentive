# Trial-Incentive Dashboard

Dashboard monitoring harian **Biaya OT vs Insentif DP** untuk BU AHI.

## Struktur Repo

```
Trial-Incentive/
├── index.html                        # Dashboard utama (GitHub Pages)
├── data/
│   ├── lc_data.csv                   # Auto-update dari Google Sheets (H-1)
│   └── ot_data.csv                   # Upload manual saat narik data OT
├── scripts/
│   └── update_csv.py                 # Script pull data LC dari Google Sheets
└── .github/workflows/
    └── update-csv.yml                # GitHub Actions — auto-run tiap hari 07.00 WIB
```

## Setup

### 1. GitHub Secret
Tambahkan secret di repo → Settings → Secrets and variables → Actions:
- **Name:** `GOOGLE_CREDENTIALS`
- **Value:** isi JSON service account

### 2. Google Sheets
Share Sheets ke service account:
`dashboard-insentif@my-project-insentif.iam.gserviceaccount.com` (role: Viewer)

Lalu update `SPREADSHEET_ID` di `scripts/update_csv.py`.

### 3. GitHub Pages
Settings → Pages → Source: **Deploy from branch** → `main` → `/ (root)`

### 4. Upload OT Data
Saat narik data OT, export sebagai `ot_data.csv` dan upload ke folder `data/`.

Format kolom yang diperlukan:
```
Employee ID, Employee Name, OT Date, Day Name, Total OT Hour, Unnamed: 29, Status, Description
```

## Skenario Insentif

| Skenario | Rate | Keterangan |
|---|---|---|
| 1 | Rp 34.000/gap DP | Rate insentif saat ini |
| 2 | Rp 51.494/gap DP | Setara rate OT/jam AHI |

## Logic Pairing

1. **LC Number** → extract dari kolom Description OT `(LC: XXXXXXX)`
2. **NIK + Date** → fallback jika LC tidak ditemukan

## Standar DP

| Tipe | Area | Standar DP |
|---|---|---|
| Customer | Bekasi, Karawang Sel | 7 |
| Customer | Jakarta Timur | 6 |
| Customer | Jakarta Sel/Ut/Bar/Pus, Karawang Ut, Purwakarta | 5 |
| Customer | Depok, Bogor | 4 |
| Customer | Tangerang | 2 |
| Store (Kecil) | Bekasi, Karawang Sel | 4 |
| Store (Kecil) | Jakarta Tim/Sel/Bar/Pus, Karawang Ut, Purwakarta | 3 |
| Store (Kecil) | Jakarta Ut, Depok, Bogor | 2 |
| Store (Kecil) | Tangerang | 1 |
| Store (Besar) | Bekasi, Karawang Sel, Jakarta Tim | 2 |
| Store (Besar) | Lainnya | 1 |
