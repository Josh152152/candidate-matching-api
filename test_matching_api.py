import requests
import json

# Test the find_matches endpoint
url = "http://localhost:5000/find_matches"

# Test data - looking for matches for JOB_001 (Python developer)
test_data = {
    "job_id": "JOB_001",
    "top_k": 3
}

print("🧪 Testing candidate matching API...")
print(f"Job ID: {test_data['job_id']}")
print(f"Looking for top {test_data['top_k']} candidates")
print("-" * 50)

try:
    response = requests.post(url, json=test_data)
    
    if response.status_code == 200:
        result = response.json()
        
        if result['success']:
            print("✅ Matching successful!")
            print(f"Job: {result['data']['job_requirements']}")
            print("\n🎯 Top Matches:")
            
            for i, match in enumerate(result['data']['top_matches'], 1):
                print(f"\n{i}. {match['candidate_name']} (ID: {match['candidate_id']})")
                print(f"   Match Score: {match['score']:.3f}")
                print(f"   Location: {match['location']}")
                print(f"   Profile: {match['profile_details'][:100]}...")
            
            print(f"\n📊 Skills Analysis:")
            skills = result['data']['skills_analysis']
            print(f"   Skills sought: {skills['sought_skills']}")
            print(f"   Skills coverage: {skills['skills_coverage']:.1%}")
            
        else:
            print(f"❌ API Error: {result['error']}")
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Connection Error: {e}")
    print("Make sure your Flask server is running!")