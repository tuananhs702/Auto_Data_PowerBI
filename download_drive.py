from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import io
from googleapiclient.http import MediaIoBaseDownload
import json

# Lấy credentials từ GitHub Secrets
GDRIVE_CREDENTIALS = json.loads(os.getenv("GDRIVE_CREDENTIALS"))

# Kết nối với Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_info(GDRIVE_CREDENTIALS, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

# ID thư mục Google Drive cần tải về (THAY BẰNG ID CỦA BẠN)
FOLDER_ID = "1LyQOw0sTGUTGUxxmGZivAzB_aTBdlH6d"
SAVE_PATH = "downloads"

# ✅ Kiểm tra và tạo thư mục downloads nếu chưa tồn tại
if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)
    print(f"📂 Đã tạo thư mục: {SAVE_PATH}")

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
        file_path = os.path.join(SAVE_PATH, file_name)

        # Kiểm tra thư mục trước khi tải
        if not os.path.exists(SAVE_PATH):
            os.makedirs(SAVE_PATH)
            print(f"📂 Thư mục {SAVE_PATH} đã bị xóa, tạo lại...")

        # Tải file từ Google Drive
        request = service.files().get_media(fileId=file_id)
        with open(file_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        print(f"✅ Đã tải: {file_name}")
