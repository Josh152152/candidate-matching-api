# ==============================================================================
# FLASK SERVER FOR BUBBLE.IO - 100% FREE
# ==============================================================================
# This file creates a web API that Bubble.io can use for candidate matching

# STEP 1: Import all the libraries we need
from flask import Flask, request, jsonify  # For creating the web API
from flask_cors import CORS                # To allow Bubble.io to connect
import os                                  # To read environment variables
from dotenv import load_dotenv            # To load the .env file
from matching_system import FreeCandidateMatchingSystem  # Our FREE AI system!

# STEP 2: Load configuration from .env file
load_dotenv()  
print("✅ Environment variables loaded from .env file")

# STEP 3: Create the Flask application
app = Flask(__name__)
print("✅ Flask application created")

# STEP 4: Enable CORS for Bubble.io
CORS(app)
print("✅ CORS enabled - Bubble.io can now connect to our API")

# STEP 5: Initialize our AI matching system (100% FREE!)
try:
    matcher = FreeCandidateMatchingSystem(
        google_credentials_path=os.getenv('GOOGLE_CREDENTIALS_PATH')
    )
    print("✅ AI Matching System initialized successfully!")
    print("💰 No OpenAI costs - Completely FREE!")
except Exception as e:
    print(f"❌ Error initializing AI system: {e}")
    print("   Make sure your .env file and Google credentials are correct")

# ==============================================================================
# API ENDPOINTS (These are like "menu items" that Bubble.io can order from)
# ==============================================================================

# ENDPOINT 1: Health Check
@app.route('/health', methods=['GET'])
def health_check():
    """
    Simple endpoint to check if our API is running
    Visit: http://your-api-url.com/health
    You should see: {"status": "healthy", "message": "FREE AI matching system running!"}
    """
    return jsonify({
        'status': 'healthy', 
        'message': 'FREE AI matching system running!',
        'version': '1.0.0',
        'cost': 'FREE - No OpenAI charges!'
    })

# ENDPOINT 2: Find Matching Candidates (THE MAIN FEATURE!)
@app.route('/find_matches', methods=['POST'])
def find_matches():
    """
    Main endpoint that finds top matching candidates for a job
    
    Expected input from Bubble.io:
    {
        "job_id": "JOB_001",
        "top_k": 5
    }
    
    Returns:
    {
        "success": true,
        "data": {
            "job_id": "JOB_001",
            "top_matches": [...],
            "skills_analysis": {...}
        }
    }
    """
    try:
        print("🔍 New matching request received!")
        
        # STEP 1: Get the data that Bubble.io sent us
        data = request.json
        print(f"   Received data: {data}")
        
        # STEP 2: Extract the specific information we need
        job_id = data.get('job_id')        # Which job are we matching for?
        top_k = data.get('top_k', 5)       # How many top candidates? (default = 5)
        
        # STEP 3: Validate the input
        if not job_id:
            print("❌ Error: No job_id provided")
            return jsonify({
                'success': False,
                'error': 'job_id is required'
            }), 400  # 400 = Bad Request
        
        print(f"   🎯 Finding top {top_k} candidates for job: {job_id}")
        
        # STEP 4: Load all our data from Google Sheets
        print("   📊 Loading data from Google Sheets...")
        candidates_df, employers_df, companies_df = matcher.load_data_from_sheets(
            os.getenv('CANDIDATES_SHEET_ID'),     # Our candidates spreadsheet
            os.getenv('EMPLOYERS_SHEET_ID'),      # Our jobs spreadsheet  
            os.getenv('COMPANIES_SHEET_ID')       # Our company rankings spreadsheet
        )
        
        # STEP 5: Check if data loaded successfully
        if candidates_df is None:
            print("❌ Error: Could not load data from Google Sheets")
            return jsonify({
                'success': False,
                'error': 'Could not load data from Google Sheets. Check your sheet IDs and permissions.'
            }), 500  # 500 = Internal Server Error
        
        print(f"   ✅ Loaded {len(candidates_df)} candidates and {len(employers_df)} jobs")
        
        # STEP 6: Run our AI matching algorithm! 🤖
        print("   🤖 Running FREE AI matching algorithm...")
        results = matcher.find_top_matches(
            job_id=job_id,
            candidates_df=candidates_df, 
            employers_df=employers_df, 
            companies_df=companies_df, 
            top_k=top_k
        )
        
        print(f"   🎉 Found {len(results['top_matches'])} matching candidates!")
        print("   💰 Total cost: $0 - Completely FREE!")
        
        # STEP 7: Send the results back to Bubble.io
        return jsonify({
            'success': True,
            'data': results,
            'message': f'Successfully found {len(results["top_matches"])} candidates',
            'cost_info': '100% free processing - No OpenAI charges'
        })
        
    except Exception as e:
        # If anything goes wrong, send a helpful error message
        print(f"❌ Error in find_matches: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}',
            'help': 'Check your Google Sheets IDs and credentials'
        }), 500

# ENDPOINT 3: Get All Jobs (Helper endpoint)
@app.route('/get_jobs', methods=['GET'])
def get_jobs():
    """
    Returns a list of all available jobs
    Useful for Bubble.io to show a dropdown of job options
    """
    try:
        print("📋 Getting list of all jobs...")
        
        # Load employers data
        _, employers_df, _ = matcher.load_data_from_sheets(
            os.getenv('CANDIDATES_SHEET_ID'),
            os.getenv('EMPLOYERS_SHEET_ID'),
            os.getenv('COMPANIES_SHEET_ID')
        )
        
        if employers_df is None:
            return jsonify({
                'success': False,
                'error': 'Could not load jobs data'
            }), 500
        
        # Convert to a simple list for Bubble.io
        jobs_list = []
        for _, job in employers_df.iterrows():
            jobs_list.append({
                'id': job['id'],
                'company_name': job.get('company_name', 'Unknown'),
                'job_requirements': job['job_requirements'][:100] + '...'  # Truncate for display
            })
        
        return jsonify({
            'success': True,
            'jobs': jobs_list,
            'count': len(jobs_list),
            'message': 'Jobs list retrieved successfully'
        })
        
    except Exception as e:
        print(f"❌ Error in get_jobs: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ENDPOINT 4: Test Google Sheets Connection
@app.route('/test_sheets', methods=['GET'])
def test_sheets():
    """
    Test endpoint to verify Google Sheets connection
    Visit this URL to check if your sheets are accessible
    """
    try:
        print("🧪 Testing Google Sheets connection...")
        
        # Try to load just the first few rows
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
        return jsonify({
            'success': False,
            'error': f'Google Sheets connection failed: {str(e)}',
            'help': 'Check your credentials and sheet IDs in the .env file'
        }), 500

# ENDPOINT 5: Add New Job (Bonus feature)
@app.route('/add_job', methods=['POST'])
def add_job():
    """
    Add a new job to the employers sheet
    
    Expected input from Bubble.io:
    {
        "id": "JOB_003",
        "company_name": "TechCorp",
        "job_requirements": "Looking for Python developer with 5+ years experience",
        "location": "New York, NY"
    }
    """
    try:
        print("➕ New job addition request received!")
        
        # Get the job data from Bubble.io
        job_data = request.json
        print(f"   Job data received: {job_data}")
        
        # Validate required fields
        required_fields = ['id', 'company_name', 'job_requirements', 'location']
        for field in required_fields:
            if field not in job_data or not job_data[field]:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Open the employers sheet and add the new job
        employers_sheet = matcher.gc.open_by_key(os.getenv('EMPLOYERS_SHEET_ID')).sheet1
        
        # Prepare the row data
        new_row = [
            job_data['id'],
            job_data['company_name'],
            job_data['job_requirements'],
            job_data['location']
        ]
        
        # Add the new row to the sheet
        employers_sheet.append_row(new_row)
        
        print(f"   ✅ Job {job_data['id']} added successfully!")
        
        return jsonify({
            'success': True,
            'message': f'Job {job_data["id"]} added successfully',
            'job_id': job_data['id']
        })
        
    except Exception as e:
        print(f"❌ Error adding job: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to add job: {str(e)}'
        }), 500

# ENDPOINT 6: Get Candidate Details
@app.route('/get_candidate/<candidate_id>', methods=['GET'])
def get_candidate_details(candidate_id):
    """
    Get detailed information about a specific candidate
    URL: http://your-api-url.com/get_candidate/CAND_001
    """
    try:
        print(f"👤 Getting details for candidate: {candidate_id}")
        
        # Load candidates data
        candidates_df, _, _ = matcher.load_data_from_sheets(
            os.getenv('CANDIDATES_SHEET_ID'),
            os.getenv('EMPLOYERS_SHEET_ID'),
            os.getenv('COMPANIES_SHEET_ID')
        )
        
        if candidates_df is None:
            return jsonify({
                'success': False,
                'error': 'Could not load candidates data'
            }), 500
        
        # Find the specific candidate
        candidate_row = candidates_df[candidates_df['id'] == candidate_id]
        
        if candidate_row.empty:
            return jsonify({
                'success': False,
                'error': f'Candidate {candidate_id} not found'
            }), 404
        
        candidate = candidate_row.iloc[0]
        
        # Extract skills for this candidate
        candidate_dict = {
            'profile_details': candidate['profile_details'],
            'location': candidate['location'],
            'benefits_requirements': candidate['benefits_requirements'],
            'corporate_culture': candidate['corporate_culture']
        }
        
        skills_info = matcher.extract_skills_with_spacy(candidate['profile_details'])
        
        return jsonify({
            'success': True,
            'candidate': {
                'id': candidate['id'],
                'name': candidate.get('name', f'Candidate {candidate["id"]}'),
                'profile_details': candidate['profile_details'],
                'location': candidate['location'],
                'benefits_requirements': candidate['benefits_requirements'],
                'corporate_culture': candidate['corporate_culture'],
                'extracted_skills': skills_info['skills']
            }
        })
        
    except Exception as e:
        print(f"❌ Error getting candidate details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==============================================================================
# MAIN APPLICATION RUNNER
# ==============================================================================

if __name__ == '__main__':
    """
    This is where our application starts running
    Think of this as "opening the restaurant" - we start serving customers
    """
    print("\n" + "="*60)
    print("🚀 STARTING FREE AI CANDIDATE MATCHING API")
    print("="*60)
    
    # Print helpful information
    print("📋 Available endpoints:")
    print("   GET  /health           - Check if API is running")
    print("   POST /find_matches     - Find matching candidates")
    print("   GET  /get_jobs         - List all available jobs")  
    print("   GET  /test_sheets      - Test Google Sheets connection")
    print("   POST /add_job          - Add a new job")
    print("   GET  /get_candidate/<id> - Get candidate details")
    print("\n💡 For testing, visit: http://localhost:5000/health")
    print("🔗 For Bubble.io, use: http://your-deployed-url.com/find_matches")
    print("\n🎯 Ready to process candidate matches!")
    print("💰 100% FREE - No OpenAI costs!")
    print("="*60 + "\n")
    
    # Start the Flask application
    # debug=True means we get helpful error messages
    # host='0.0.0.0' means accessible from other computers
    # port=5000 means it runs on port 5000
    app.run(
        debug=True,           # Show detailed errors (turn off in production)
        host='0.0.0.0',       # Allow external connections
        port=5000             # Run on port 5000
    )