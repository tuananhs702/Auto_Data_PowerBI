from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import io
import json
import pandas as pd
from googleapiclient.http import MediaIoBaseDownload

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
results = service.files().list(q=query, fields="files(id, name)").execute()
files = results.get('files', [])

if not files:
    print("⚠️ Không có file nào trong thư mục!")
else:
    for file in files:
        file_id = file['id']
        file_name = file['name']
        file_path = os.path.join(SAVE_PATH, file_name)

        # 🔹 Tải file từ Google Drive
        request = service.files().get_media(fileId=file_id)
        with open(file_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        print(f"✅ Đã tải: {file_name}")

        # 🔹 Nếu file là Excel, chuyển sang CSV
        if file_name.endswith(('.xls', '.xlsx')):
            csv_path = file_path.rsplit('.', 1)[0] + ".csv"
            df = pd.read_excel(file_path)
            df.to_csv(csv_path, index=False)
            os.remove(file_path)  # Xóa file gốc Excel
            print(f"🔄 Đã chuyển {file_name} thành {os.path.basename(csv_path)}")

# 🔹 Cập nhật summary_Br_daily.csv từ predictions_table_BR_daily.csv
predictions_file = os.path.join(SAVE_PATH, "predictions_table_BR_daily.csv")
summary_file = os.path.join(SAVE_PATH, "summary_Br_daily.csv")

# Kiểm tra nếu cả hai file tồn tại
if os.path.exists(predictions_file) and os.path.exists(summary_file):
    # Đọc file predictions (chỉ lấy cột đầu tiên là ngày)
    df_pred = pd.read_csv(predictions_file, header=None, usecols=[0], names=['date'])

    # Đọc file summary (giữ nguyên tất cả các cột)
    df_summary = pd.read_csv(summary_file, header=None)

    # Giả sử cột ngày là cột đầu tiên trong summary
    df_summary.columns = ['date'] + [f'col_{i}' for i in range(1, df_summary.shape[1])]

    # Gộp dữ liệu ngày từ predictions, không làm mất dữ liệu cũ
    df_summary = pd.concat([df_summary, df_pred], ignore_index=True).drop_duplicates(subset=['date'])

    # Lưu lại file summary với tất cả các cột
    df_summary.to_csv(summary_file, index=False, header=False)
    print(f"✅ Đã cập nhật ngày từ {predictions_file} vào {summary_file}")
else:
    print("⚠️ Một trong hai file không tồn tại!")
