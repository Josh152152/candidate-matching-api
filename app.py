# ==============================================================================
# FLASK SERVER FOR AI RECRUITMENT PLATFORM - COMPLETE VERSION
# ==============================================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from matching_system import FreeCandidateMatchingSystem

# Load environment variables
load_dotenv()  
print("✅ Environment variables loaded from .env file")

# Create Flask application
app = Flask(__name__)
print("✅ Flask application created")

# Enable CORS
CORS(app)
print("✅ CORS enabled - Frontend can now connect to our API")

# Initialize AI matching system
try:
    matcher = FreeCandidateMatchingSystem(
        google_credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH')
    )
    print("✅ AI Matching System initialized successfully!")
    print("💰 No OpenAI costs - Completely FREE!")
except Exception as e:
    print(f"❌ Error initializing AI system: {e}")

# ENDPOINT 1: Health Check
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'message': 'FREE AI matching system running!',
        'version': '1.0.0',
        'cost': 'FREE - No OpenAI charges!'
    })

# ENDPOINT 2: Find Matching Candidates
@app.route('/find_matches', methods=['POST'])
def find_matches():
    try:
        print("🔍 New matching request received!")
        data = request.json
        job_id = data.get('job_id')
        top_k = data.get('top_k', 5)
        
        if not job_id:
            return jsonify({'success': False, 'error': 'job_id is required'}), 400
        
        print(f"   🎯 Finding top {top_k} candidates for job: {job_id}")
        
        candidates_df, employers_df, companies_df = matcher.load_data_from_sheets(
            os.getenv('CANDIDATES_SHEET_ID'),
            os.getenv('EMPLOYERS_SHEET_ID'),
            os.getenv('COMPANIES_SHEET_ID')
        )
        
        if candidates_df is None:
            return jsonify({'success': False, 'error': 'Could not load data from Google Sheets'}), 500
        
        results = matcher.find_top_matches(job_id, candidates_df, employers_df, companies_df, top_k)
        
        return jsonify({
            'success': True,
            'data': results,
            'message': f'Successfully found {len(results["top_matches"])} candidates'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ENDPOINT 3: Get All Jobs
@app.route('/get_jobs', methods=['GET'])
def get_jobs():
    try:
        _, employers_df, _ = matcher.load_data_from_sheets(
            os.getenv('CANDIDATES_SHEET_ID'),
            os.getenv('EMPLOYERS_SHEET_ID'),
            os.getenv('COMPANIES_SHEET_ID')
        )
        
        if employers_df is None:
            return jsonify({'success': False, 'error': 'Could not load jobs data'}), 500
        
        jobs_list = []
        for _, job in employers_df.iterrows():
            jobs_list.append({
                'id': job['id'],
                'company_name': job.get('company_name', 'Unknown'),
                'job_requirements': job['job_requirements']
            })
        
        return jsonify({
            'success': True,
            'jobs': jobs_list,
            'count': len(jobs_list),
            'message': 'Jobs list retrieved successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ENDPOINT 4: Test Google Sheets Connection
@app.route('/test_sheets', methods=['GET'])
def test_sheets():
    try:
        candidates_df, employers_df, companies_df = matcher.load_data_from_sheets(
            os.getenv('CANDIDATES_SHEET_ID'),
            os.getenv('EMPLOYERS_SHEET_ID'),
            os.getenv('COMPANIES_SHEET_ID')
        )
        
        return jsonify({
            'success': True,
            'message': 'Google Sheets connection successful!',
            'data': {
                'candidates_count': len(candidates_df) if candidates_df is not None else 0,
                'employers_count': len(employers_df) if employers_df is not None else 0,
                'companies_count': len(companies_df) if companies_df is not None else 0
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ENDPOINT 5: Add New Candidate (NEW!)
@app.route('/add_candidate', methods=['POST'])
def add_candidate():
    try:
        print("➕ New candidate registration request received!")
        candidate_data = request.json
        
        # Validate required fields
        required_fields = ['id', 'name', 'profile_details', 'location', 'benefits_requirements', 'corporate_culture']
        for field in required_fields:
            if field not in candidate_data or not candidate_data[field]:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Open candidates sheet
        candidates_sheet = matcher.gc.open_by_key(os.getenv('CANDIDATES_SHEET_ID')).sheet1
        
        # Check if candidate already exists
        existing_records = candidates_sheet.get_all_records()
        if any(record.get('id') == candidate_data['id'] for record in existing_records):
            return jsonify({'success': False, 'error': f'Candidate with ID {candidate_data["id"]} already exists'}), 400
        
        # Add new candidate
        new_row = [
            candidate_data['id'],
            candidate_data['name'],
            candidate_data['profile_details'],
            candidate_data['location'],
            candidate_data['benefits_requirements'],
            candidate_data['corporate_culture']
        ]
        
        candidates_sheet.append_row(new_row)
        print(f"   ✅ Candidate {candidate_data['id']} added successfully!")
        
        return jsonify({
            'success': True,
            'message': f'Candidate {candidate_data["id"]} added successfully',
            'candidate_id': candidate_data['id']
        })
        
    except Exception as e:
        print(f"❌ Error adding candidate: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to add candidate: {str(e)}'}), 500

# ENDPOINT 6: Add New Job (NEW!)
@app.route('/add_job', methods=['POST'])
def add_job():
    try:
        print("➕ New job posting request received!")
        job_data = request.json
        
        # Validate required fields
        required_fields = ['id', 'company_name', 'job_requirements', 'location']
        for field in required_fields:
            if field not in job_data or not job_data[field]:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Open employers sheet
        employers_sheet = matcher.gc.open_by_key(os.getenv('EMPLOYERS_SHEET_ID')).sheet1
        
        # Check if job already exists
        existing_records = employers_sheet.get_all_records()
        if any(record.get('id') == job_data['id'] for record in existing_records):
            return jsonify({'success': False, 'error': f'Job with ID {job_data["id"]} already exists'}), 400
        
        # Add new job
        new_row = [
            job_data['id'],
            job_data['company_name'],
            job_data['job_requirements'],
            job_data['location']
        ]
        
        employers_sheet.append_row(new_row)
        print(f"   ✅ Job {job_data['id']} added successfully!")
        
        return jsonify({
            'success': True,
            'message': f'Job {job_data["id"]} added successfully',
            'job_id': job_data['id']
        })
        
    except Exception as e:
        print(f"❌ Error adding job: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to add job: {str(e)}'}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 STARTING AI RECRUITMENT PLATFORM API")
    print("="*60)
    print("📋 Available endpoints:")
    print("   GET  /health              - Check if API is running")
    print("   POST /find_matches        - Find matching candidates (AI)")
    print("   GET  /get_jobs            - List all available jobs")  
    print("   GET  /test_sheets         - Test Google Sheets connection")
    print("   POST /add_candidate       - Register new candidate (NEW!)")
    print("   POST /add_job             - Post new job (NEW!)")
    print("\n🎯 Ready to process candidate matches!")
    print("💰 100% FREE - No OpenAI costs!")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
