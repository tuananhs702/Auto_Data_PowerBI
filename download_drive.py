from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import os
import json
import pandas as pd

# 🔹 Lấy credentials từ GitHub Secrets
GDRIVE_CREDENTIALS = json.loads(os.getenv("GDRIVE_CREDENTIALS"))

# 🔹 Kết nối với Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_info(GDRIVE_CREDENTIALS, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

# 🔹 Danh sách file cần tải (tên file và thư mục chứa file)
FILES_TO_DOWNLOAD = [
    {"name": "predictions_table_Br_daily.csv", "folder_id": "1LyQOw0sTGUTGUxxmGZivAzB_aTBdlH6d"},
    {"name": "predictions_table_US_daily.csv", "folder_id": "1LyQOw0sTGUTGUxxmGZivAzB_aTBdlH6d"},
    {"name": "summary_Br_daily.csv", "folder_id": "1LyQOw0sTGUTGUxxmGZivAzB_aTBdlH6d"},
    {"name": "summary_US_daily.csv", "folder_id": "1LyQOw0sTGUTGUxxmGZivAzB_aTBdlH6d"},
]

SAVE_PATH = "downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

for file_info in FILES_TO_DOWNLOAD:
    file_name = file_info["name"]
    folder_id = file_info["folder_id"]

    # 🔹 Kiểm tra xem file có tồn tại trong thư mục không
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])

    if not files:
        print(f"⚠️ Không tìm thấy {file_name} trong thư mục {folder_id}!")
        continue

    file_id = files[0]['id']
    file_mime = files[0]["mimeType"]
    file_path = os.path.join(SAVE_PATH, file_name)

    try:
        # 🔹 Nếu file là Google Sheets -> Xuất CSV
        if file_mime == "application/vnd.google-apps.spreadsheet":
            request = service.files().export_media(fileId=file_id, mimeType="text/csv")
            file_path = file_path.rsplit(".", 1)[0] + ".csv"
        else:
            request = service.files().get_media(fileId=file_id)

        # 🔹 Tải file từ Google Drive
        with open(file_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        print(f"✅ Đã tải: {file_name} ({file_mime})")

        # 🔹 Nếu file là Excel, chuyển sang CSV
        if file_name.endswith(('.xls', '.xlsx')):
            try:
                csv_path = file_path.rsplit('.', 1)[0] + ".csv"
                df = pd.read_excel(file_path, engine="openpyxl" if file_name.endswith(".xlsx") else "xlrd")
                df.to_csv(csv_path, index=False)
                os.remove(file_path)  # Xóa file gốc Excel
                file_path = csv_path
                print(f"🔄 Đã chuyển {file_name} thành {os.path.basename(csv_path)}")
            except Exception as e:
                print(f"❌ Không thể đọc file {file_name}. Lỗi: {e}")
                continue

        # 🔹 Đọc file CSV và đặt tên cột đầu tiên là 'Date'
        df = pd.read_csv(file_path)
        if not df.empty:
            df.columns.values[0] = "Date"  # Đặt lại tên cột đầu tiên thành 'Date'
            df.to_csv(file_path, index=False)
            print(f"📝 Đã cập nhật tên cột đầu tiên thành 'Date' cho {file_name}")

            # Sắp xếp nếu có cột Date hợp lệ
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
            df = df.sort_values(by="Date")
            df.to_csv(file_path, index=False)
            print(f"📅 Đã sắp xếp {file_name} theo Date")

    except Exception as error:
        print(f"❌ Lỗi khi tải {file_name}: {error}")

print("\n✅ Hoàn thành tải và xử lý tất cả các file được chỉ định!")
