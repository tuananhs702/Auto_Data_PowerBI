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

            # 🔹 Kiểm tra nếu file có dung lượng bất thường
            if os.path.getsize(file_path) < 100:  # File quá nhỏ có thể bị lỗi
                print(f"⚠️ File {file_name} có thể bị lỗi, dung lượng quá nhỏ!")
                continue

            # 🔹 Nếu file là Excel, chuyển sang CSV
            if file_name.endswith(('.xls', '.xlsx')):
                csv_path = file_path.rsplit('.', 1)[0] + ".csv"
                try:
                    df = pd.read_excel(file_path, engine="openpyxl" if file_name.endswith(".xlsx") else "xlrd")
                    df.to_csv(csv_path, index=False)
                    os.remove(file_path)  # Xóa file gốc Excel
                    print(f"🔄 Đã chuyển {file_name} thành {os.path.basename(csv_path)}")
                except Exception as e:
                    print(f"❌ Không thể đọc file {file_name}. Lỗi: {e}")

        except HttpError as error:
            print(f"❌ Lỗi khi tải {file_name}: {error}")

# 🔹 Cập nhật summary_Br_daily.csv từ predictions_table_BR_daily.csv
summary_file = os.path.join(SAVE_PATH, "summary_Br_daily.csv")
predictions_file = os.path.join(SAVE_PATH, "predictions_table_BR_daily.csv")

# Đọc file summary (nếu có)
try:
    summary_df = pd.read_csv(summary_file)
except FileNotFoundError:
    summary_df = pd.DataFrame(columns=["Date", "Fitting", "True_value"])  # Tạo dataframe trống nếu file không tồn tại

# Đọc file predictions
try:
    predictions_df = pd.read_csv(predictions_file)

    # Đảm bảo cột Date có tiêu đề đúng
    summary_df.rename(columns={summary_df.columns[0]: "Date"}, inplace=True)
    predictions_df.rename(columns={predictions_df.columns[0]: "Date"}, inplace=True)

    # Chỉ lấy các cột cần thiết từ predictions
    predictions_df = predictions_df[["Date", "Predicted", "Upper_Bound", "Lower_Bound"]]

    # Merge dữ liệu: Giữ nguyên dữ liệu cũ, thêm ngày mới và cập nhật giá trị dự đoán
    merged_df = pd.merge(summary_df, predictions_df, on="Date", how="outer")

    # Ghi đè file cũ
    merged_df.to_csv(summary_file, index=False)
    print("✅ File summary_Br_daily.csv đã được cập nhật thành công!")

except FileNotFoundError:
    print("⚠️ Không tìm thấy file predictions_table_BR_daily.csv, không thể cập nhật summary_Br_daily.csv.")
