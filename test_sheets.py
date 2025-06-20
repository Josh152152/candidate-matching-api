import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

print("🧪 Testing Google Sheets connection...")

try:
    # Load credentials
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(
        os.getenv('GOOGLE_CREDENTIALS_PATH'), 
        scopes=scope
    )
    gc = gspread.authorize(creds)
    
    print("✅ Credentials loaded successfully")
    
    # Test each sheet
    sheets = {
        'Candidates': os.getenv('CANDIDATES_SHEET_ID'),
        'Employers': os.getenv('EMPLOYERS_SHEET_ID'),
        'Companies': os.getenv('COMPANIES_SHEET_ID')
    }
    
    for name, sheet_id in sheets.items():
        try:
            sheet = gc.open_by_key(sheet_id).sheet1
            data = sheet.get_all_records()
            print(f"✅ {name}: {len(data)} rows")
        except Exception as e:
            print(f"❌ {name}: {e}")
            
except Exception as e:
    print(f"❌ General error: {e}")
    print("💡 Check your .env file and google-credentials.json")