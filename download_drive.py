from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import io
import json
import pandas as pd
from googleapiclient.http import MediaIoBaseDownload

# Lấy credentials từ GitHub Secrets
GDRIVE_CREDENTIALS = json.loads(os.getenv("GDRIVE_CREDENTIALS"))

# Kết nối với Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_info(GDRIVE_CREDENTIALS, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

# ID thư mục Google Drive cần tải về (THAY BẰNG ID CỦA BẠN)
FOLDER_ID = "1LyQOw0sTGUTGUxxmGZivAzB_aTBdlH6d"
SAVE_PATH = "downloads"

# ✅ Đảm bảo thư mục downloads tồn tại
os.makedirs(SAVE_PATH, exist_ok=True)

# Lấy danh sách file trong thư mục Google Drive
query = f"'{FOLDER_ID}' in parents and trashed=false"
results = service.files().list(q=query, fields="files(id, name)").execute()
files = results.get('files', [])

if not files:
    print("⚠️ Không có file nào trong thư mục!")
else:
    for file in files:
        file_id = file['id']
        file_name = file['name']
        file_ext = os.path.splitext(file_name)[1].lower()  # Lấy phần mở rộng file

        file_path = os.path.join(SAVE_PATH, file_name)
        request = service.files().get_media(fileId=file_id)

        # Tải file về máy
        with open(file_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        print(f"✅ Đã tải: {file_name}")

        # 👉 Nếu là file Excel, chuyển sang CSV
        if file_ext in [".xlsx", ".xls"]:
            try:
                df = pd.read_excel(file_path)
                csv_path = file_path.replace(file_ext, ".csv")
                df.to_csv(csv_path, index=False)
                os.remove(file_path)  # Xóa file Excel gốc
                print(f"🔄 Đã chuyển đổi {file_name} -> {csv_path}")
            except Exception as e:
                print(f"❌ Lỗi khi chuyển đổi {file_name}: {e}")
