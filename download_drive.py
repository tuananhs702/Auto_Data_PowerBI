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

if os.path.exists(predictions_file) and os.path.exists(summary_file):
    df_predictions = pd.read_csv(predictions_file)
    df_summary = pd.read_csv(summary_file)

    # ✅ Đặt tên cột đầu tiên là "Date" nếu chưa có
    df_predictions.rename(columns={df_predictions.columns[0]: "Date"}, inplace=True)
    df_summary.rename(columns={df_summary.columns[0]: "Date"}, inplace=True)

    # 🔹 Tìm những ngày có trong predictions nhưng chưa có trong summary
    missing_dates = df_predictions[~df_predictions["Date"].isin(df_summary["Date"])]

    if not missing_dates.empty:
        # 🔹 Chỉ lấy các cột cần thiết từ predictions
        missing_data = missing_dates[["Date", "Fitting", "True_value"]].copy()

        # ✅ Đảm bảo 3 cột cuối có tên chính xác
        expected_columns = ["Predicted", "Upper_Bound", "Lower_Bound"]
        for i, col_name in enumerate(expected_columns, start=len(df_summary.columns) - 3):
            if i >= len(df_summary.columns):  
                df_summary[col_name] = None  # Thêm cột mới
            else:
                df_summary.rename(columns={df_summary.columns[i]: col_name}, inplace=True)

        # 🔹 Gộp dữ liệu vào summary
        df_summary = pd.concat([df_summary, missing_data], ignore_index=True)

        # ✅ Lưu lại file summary
        df_summary.to_csv(summary_file, index=False)
        print("✅ Đã cập nhật file summary_Br_daily.csv")
    else:
        print("⚡ Không có ngày mới cần thêm!")
else:
    print("❌ Không tìm thấy file predictions_table_BR_daily.csv hoặc summary_Br_daily.csv")
