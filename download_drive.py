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

# ✅ Nếu file summary chưa tồn tại, tạo file trống
if not os.path.exists(summary_file):
    pd.DataFrame(columns=["Date"]).to_csv(summary_file, index=False)

# ✅ Đọc dữ liệu từ file
df_summary = pd.read_csv(summary_file)
df_predictions = pd.read_csv(predictions_file)

# 🔹 Đảm bảo cột có đúng tiêu đề
df_predictions.columns = ["Date", "Predicted", "Upper_Bound", "Lower_Bound"]
df_predictions["Date"] = df_predictions["Date"].astype(str)

# 🔹 Đổi tên cột đầu tiên thành "Date" nếu chưa đúng
if df_summary.columns[0] != "Date":
    df_summary.rename(columns={df_summary.columns[0]: "Date"}, inplace=True)

# 🛠️ Loại bỏ dòng tiêu đề bị chèn nhầm
df_predictions = df_predictions[df_predictions["Date"] != "Predicted"]

# 📌 Lấy danh sách ngày đã có trong summary
existing_dates = df_summary["Date"].astype(str).tolist()

# 🔄 Thêm dữ liệu mới từ df_predictions vào summary nếu ngày đó chưa có
df_new = df_predictions[~df_predictions["Date"].isin(existing_dates)]
df_summary = pd.concat([df_summary, df_new], ignore_index=True)

# 💾 Lưu lại file summary
df_summary.to_csv(summary_file, index=False)
print(f"✅ Đã cập nhật {summary_file} mà không chèn sai tiêu đề!")
