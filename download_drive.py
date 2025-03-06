from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
import os
import io
import json
import pandas as pd

# 🔹 Lấy credentials từ GitHub Secrets
GDRIVE_CREDENTIALS = json.loads(os.getenv("GDRIVE_CREDENTIALS"))

# 🔹 Kết nối với Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_info(GDRIVE_CREDENTIALS, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

# 🔹 ID thư mục Google Drive cần tải
FOLDER_ID = "1LyQOw0sTGUTGUxxmGZivAzB_aTBdlH6d"
SAVE_PATH = "downloads"

# 🔹 Tạo thư mục downloads nếu chưa tồn tại
os.makedirs(SAVE_PATH, exist_ok=True)

# 🔹 Lấy danh sách file trong thư mục Google Drive
query = f"'{FOLDER_ID}' in parents and trashed=false"
results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
files = results.get('files', [])

if not files:
    print("⚠️ Không có file nào trong thư mục!")
else:
    for file in files:
        file_id = file['id']
        file_name = file['name']
        file_path = os.path.join(SAVE_PATH, file_name)

        try:
            # 🔹 Nếu là Google Sheets, xuất sang CSV
            if file["mimeType"] == "application/vnd.google-apps.spreadsheet":
                request = service.files().export_media(fileId=file_id, mimeType="text/csv")
                file_path = file_path.rsplit(".", 1)[0] + ".csv"  # Đổi tên thành CSV
            else:
                request = service.files().get_media(fileId=file_id)

            # 🔹 Tải file từ Google Drive
            with open(file_path, "wb") as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            print(f"✅ Đã tải: {file_name}")

            # 🔹 Nếu file là Excel, chuyển sang CSV
            if file_name.endswith(('.xls', '.xlsx')):
                csv_path = file_path.rsplit('.', 1)[0] + ".csv"
                try:
                    df = pd.read_excel(file_path, engine="openpyxl" if file_name.endswith(".xlsx") else "xlrd")
                    df.to_csv(csv_path, index=False)
                    os.remove(file_path)  # Xóa file gốc Excel
                    print(f"🔄 Đã chuyển {file_name} thành {os.path.basename(csv_path)}")
                    file_path = csv_path  # Cập nhật đường dẫn mới để xử lý tiếp
                except Exception as e:
                    print(f"❌ Không thể đọc file {file_name}. Lỗi: {e}")
                    continue  # Bỏ qua file này nếu lỗi

            # 🔹 Sắp xếp tất cả các file CSV theo Date
            if file_path.endswith('.csv'):
                try:
                    df = pd.read_csv(file_path)

                    # Kiểm tra và sắp xếp theo Date nếu có cột Date
                    if "Date" in df.columns:
                        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
                        df = df.sort_values(by="Date")
                        df.to_csv(file_path, index=False)
                        print(f"📅 Đã sắp xếp {file_name} theo Date")
                except Exception as e:
                    print(f"⚠️ Không thể sắp xếp {file_name}. Lỗi: {e}")

        except HttpError as error:
            print(f"❌ Lỗi khi tải {file_name}: {error}")

print("\n✅ Hoàn thành tải và sắp xếp tất cả các file CSV theo Date!")
