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
summary_file = os.path.join(SAVE_PATH, "summary_Br_daily.csv")
predictions_file = os.path.join(SAVE_PATH, "predictions_table_BR_daily.csv")

if os.path.exists(summary_file) and os.path.exists(predictions_file):
    # 📌 Đọc dữ liệu
    df_summary = pd.read_csv(summary_file)
    df_predictions = pd.read_csv(predictions_file, header=None)

    # 📅 Lấy danh sách ngày mới từ file dự đoán
    new_dates = df_predictions.iloc[:, 0].dropna().astype(str).tolist()

    # 🌟 Thêm ngày mới vào summary nếu chưa có
    existing_dates = df_summary.iloc[:, 0].astype(str).tolist()  # Lấy cột ngày từ summary
    missing_dates = [date for date in new_dates if date not in existing_dates]

    if missing_dates:
        new_rows = pd.DataFrame({df_summary.columns[0]: missing_dates})  # Chỉ thêm cột ngày
        df_summary = pd.concat([df_summary, new_rows], ignore_index=True)

    # 📍 Thêm 3 cột trống nếu chưa có
    for col in ["Predicted", "Upper_Bound", "Lower_Bound"]:
        if col not in df_summary.columns:
            df_summary[col] = ""

    # 🛠️ Gán giá trị 0 cho tất cả các cột (trừ cột ngày)
    for col in df_summary.columns[1:]:  # Bỏ qua cột đầu tiên (ngày)
        df_summary[col].fillna(0, inplace=True)

    # 💾 Lưu lại file summary
    df_summary.to_csv(summary_file, index=False)
    print(f"✅ Đã cập nhật {summary_file}")
else:
    print("⚠️ Không tìm thấy cả 2 file summary_Br_daily.csv và predictions_table_BR_daily.csv!")
