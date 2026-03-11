import os
import json
import gspread
from google.oauth2.service_account import Credentials

def check_my_sheet():
    print("🕵️ جاري فحص الشيت كشفاً للمستور...")
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info).with_scopes(["https://www.googleapis.com/auth/spreadsheets"])
    client = gspread.authorize(creds)
    
    sheet_id = os.getenv("SPREADSHEET_ID")
    sheet = client.open_by_key(sheet_id).worksheet("Products")
    
    all_rows = sheet.get_all_values()
    print(f"📄 اسم الملف: {client.open_by_key(sheet_id).title}")
    print(f"📊 عدد الصفوف الكلي: {len(all_rows)}")
    
    if len(all_rows) > 1:
        print("💡 محتوى الصف الثاني:")
        print(f"   العمود A: {all_rows[1][0] if len(all_rows[1]) > 0 else 'فارغ'}")
        print(f"   العمود B (الرابط): {all_rows[1][1] if len(all_rows[1]) > 1 else 'فارغ'}")
        print(f"   العمود C (الحالة): '{all_rows[1][2] if len(all_rows[1]) > 2 else 'فارغ'}'")
    else:
        print("⚠️ الشيت فارغ أو يحتوي على العناوين فقط!")

if __name__ == "__main__":
    check_my_sheet()
