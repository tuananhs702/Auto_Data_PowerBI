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

# 🔹 ID thư mục Google Drive cần tải
FOLDER_ID = "1LyQOw0sTGUTGUxxmGZivAzB_aTBdlH6d"
SAVE_PATH = "downloads"
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
        file_mime = file["mimeType"]
        file_path = os.path.join(SAVE_PATH, file_name)

        try:
            # 🔹 Kiểm tra nếu là Google Sheets -> Xuất CSV
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

            # 🔹 Nếu file là Excel, kiểm tra định dạng trước khi xử lý
            if file_name.endswith(('.xls', '.xlsx')):
                try:
                    # Kiểm tra MIME type hợp lệ
                    if file_mime not in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                         "application/vnd.ms-excel"]:
                        raise ValueError("⚠️ File không phải là Excel hợp lệ!")

                    csv_path = file_path.rsplit('.', 1)[0] + ".csv"
                    df = pd.read_excel(file_path, engine="openpyxl" if file_name.endswith(".xlsx") else "xlrd")
                    df.to_csv(csv_path, index=False)
                    os.remove(file_path)  # Xóa file gốc Excel
                    print(f"🔄 Đã chuyển {file_name} thành {os.path.basename(csv_path)}")

                    # Sắp xếp nếu có cột Date
                    df = pd.read_csv(csv_path)
                    if "Date" in df.columns:
                        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
                        df = df.sort_values(by="Date")
                        df.to_csv(csv_path, index=False)
                        print(f"📅 Đã sắp xếp {file_name} theo Date")

                except Exception as e:
                    print(f"❌ Không thể đọc file {file_name}. Lỗi: {e}")

        except Exception as error:
            print(f"❌ Lỗi khi tải {file_name}: {error}")

print("\n✅ Hoàn thành tải và sắp xếp tất cả các file CSV theo Date!")
