from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import uuid
from matching_system import CandidateMatchingSystem
from werkzeug.security import generate_password_hash

app = Flask(__name__)
CORS(app)

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/spreadsheets/']
SERVICE_ACCOUNT_FILE = 'google-credentials.json'

def get_google_client():
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return None

# Initialize matching system
matching_system = CandidateMatchingSystem()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Candidate Matching API is running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/add_candidate', methods=['POST'])
def add_candidate():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['full_name', 'email', 'phone', 'location', 'experience_years', 'skills', 'bio']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Generate unique ID
        candidate_id = str(uuid.uuid4())[:8]
        
        # Hash password if provided
        password_hash = ""
        if 'password' in data and data['password']:
            password_hash = generate_password_hash(data['password'])
        
        # Connect to Google Sheets
        client = get_google_client()
        if not client:
            return jsonify({"error": "Failed to connect to database"}), 500
        
        # Open candidates sheet
        candidates_sheet_id = os.getenv('CANDIDATES_SHEET_ID')
        sheet = client.open_by_key(candidates_sheet_id).sheet1
        
        # Prepare candidate data
        candidate_data = [
            candidate_id,
            data['full_name'],
            data['email'],
            data['phone'],
            data['location'],
            str(data['experience_years']),
            data['skills'],
            data['bio'],
            data.get('education', ''),
            data.get('certifications', ''),
            data.get('portfolio_url', ''),
            data.get('linkedin_url', ''),
            password_hash,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'active'
        ]
        
        # Add to sheet
        sheet.append_row(candidate_data)
        
        return jsonify({
            "success": True,
            "message": "Candidate registered successfully",
            "candidate_id": candidate_id
        }), 201
        
    except Exception as e:
        print(f"Error adding candidate: {e}")
        return jsonify({"error": "Failed to register candidate"}), 500

@app.route('/add_job', methods=['POST'])
def add_job():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['company_name', 'job_title', 'location', 'requirements', 'description']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())[:8]
        
        # Connect to Google Sheets
        client = get_google_client()
        if not client:
            return jsonify({"error": "Failed to connect to database"}), 500
        
        # Open employers sheet
        employers_sheet_id = os.getenv('EMPLOYERS_SHEET_ID')
        sheet = client.open_by_key(employers_sheet_id).sheet1
        
        # Prepare job data
        job_data = [
            job_id,
            data['company_name'],
            data['job_title'],
            data['location'],
            data['requirements'],
            data['description'],
            data.get('salary_range', ''),
            data.get('employment_type', 'Full-time'),
            data.get('contact_email', ''),
            data.get('company_website', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'active'
        ]
        
        # Add to sheet
        sheet.append_row(job_data)
        
        return jsonify({
            "success": True,
            "message": "Job posted successfully",
            "job_id": job_id
        }), 201
        
    except Exception as e:
        print(f"Error adding job: {e}")
        return jsonify({"error": "Failed to post job"}), 500

@app.route('/find_matches', methods=['POST'])
def find_matches():
    try:
        data = request.json
        job_requirements = data.get('job_requirements', '')
        location = data.get('location', '')
        
        if not job_requirements:
            return jsonify({"error": "Job requirements are required"}), 400
        
        # Get matches using the matching system
        matches = matching_system.find_matches(job_requirements, location)
        
        return jsonify({
            "success": True,
            "matches": matches,
            "total_matches": len(matches)
        })
        
    except Exception as e:
        print(f"Error finding matches: {e}")
        return jsonify({"error": "Failed to find matches"}), 500

@app.route('/get_jobs', methods=['GET'])
def get_jobs():
    try:
        client = get_google_client()
        if not client:
            return jsonify({"error": "Failed to connect to database"}), 500
        
        employers_sheet_id = os.getenv('EMPLOYERS_SHEET_ID')
        sheet = client.open_by_key(employers_sheet_id).sheet1
        
        # Get all records
        records = sheet.get_all_records()
        
        return jsonify({
            "success": True,
            "jobs": records,
            "total_jobs": len(records)
        })
        
    except Exception as e:
        print(f"Error getting jobs: {e}")
        return jsonify({"error": "Failed to retrieve jobs"}), 500

@app.route('/get_candidates', methods=['GET'])
def get_candidates():
    try:
        client = get_google_client()
        if not client:
            return jsonify({"error": "Failed to connect to database"}), 500
        
        candidates_sheet_id = os.getenv('CANDIDATES_SHEET_ID')
        sheet = client.open_by_key(candidates_sheet_id).sheet1
        
        # Get all records (excluding password hashes for security)
        records = sheet.get_all_records()
        
        # Remove sensitive data
        for record in records:
            if 'password_hash' in record:
                del record['password_hash']
        
        return jsonify({
            "success": True,
            "candidates": records,
            "total_candidates": len(records)
        })
        
    except Exception as e:
        print(f"Error getting candidates: {e}")
        return jsonify({"error": "Failed to retrieve candidates"}), 500

@app.route('/get_candidate/<candidate_id>', methods=['GET'])
def get_candidate(candidate_id):
    try:
        client = get_google_client()
        if not client:
            return jsonify({"error": "Failed to connect to database"}), 500
        
        candidates_sheet_id = os.getenv('CANDIDATES_SHEET_ID')
        sheet = client.open_by_key(candidates_sheet_id).sheet1
        
        # Find candidate by ID
        records = sheet.get_all_records()
        candidate = None
        
        for record in records:
            if record.get('id') == candidate_id:
                candidate = record
                break
        
        if not candidate:
            return jsonify({"error": "Candidate not found"}), 404
        
        # Remove sensitive data
        if 'password_hash' in candidate:
            del candidate['password_hash']
        
        return jsonify({
            "success": True,
            "candidate": candidate
        })
        
    except Exception as e:
        print(f"Error getting candidate: {e}")
        return jsonify({"error": "Failed to retrieve candidate"}), 500

@app.route('/test_sheets', methods=['GET'])
def test_sheets():
    try:
        client = get_google_client()
        if not client:
            return jsonify({"error": "Failed to connect to Google Sheets"}), 500
        
        # Test candidates sheet
        candidates_sheet_id = os.getenv('CANDIDATES_SHEET_ID')
        candidates_sheet = client.open_by_key(candidates_sheet_id).sheet1
        candidates = candidates_sheet.get_all_records()[:5]  # First 5 records
        
        # Test employers sheet
        employers_sheet_id = os.getenv('EMPLOYERS_SHEET_ID')
        employers_sheet = client.open_by_key(employers_sheet_id).sheet1
        jobs = employers_sheet.get_all_records()[:5]
        
        # Test companies sheet
        companies_sheet_id = os.getenv('COMPANIES_SHEET_ID')
        companies_sheet = client.open_by_key(companies_sheet_id).sheet1
        companies = companies_sheet.get_all_records()[:5]
        
        return jsonify({
            "success": True,
            "message": "Google Sheets connection successful",
            "data": {
                "candidates_count": len(candidates),
                "jobs_count": len(jobs),
                "companies_count": len(companies),
                "sample_candidates": candidates,
                "sample_jobs": jobs,
                "sample_companies": companies
            }
        })
        
    except Exception as e:
        print(f"Error testing sheets: {e}")
        return jsonify({"error": f"Failed to test sheets: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
