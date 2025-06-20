import pandas as pd
import numpy as np
try:
    import spacy
except ImportError:
    spacy = None
import re
import json
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import gspread
from google.oauth2.service_account import Credentials
import os
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

class FreeCandidateMatchingSystem:
    def __init__(self, google_credentials_path: str):
        """
        Initialize the matching system with lightweight alternatives
        
        Args:
            google_credentials_path: Path to Google service account credentials JSON
        """
        # Load spaCy model for NLP (optional)
        if spacy:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                print("spaCy English model not available, using fallback method")
                self.nlp = None
        else:
            self.nlp = None
            
        self.geolocator = Nominatim(user_agent="candidate_matcher")
        
        # Initialize Google Sheets connection
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        
        # Handle both file path and JSON string
        if google_credentials_path and os.path.exists(google_credentials_path):
            creds = Credentials.from_service_account_file(google_credentials_path, scopes=scope)
        else:
            # Try to get from environment variable (for production)
            import json as json_lib
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                creds_data = json_lib.loads(creds_json)
                creds = Credentials.from_service_account_info(creds_data, scopes=scope)
            else:
                raise ValueError("Google credentials not found")
        
        self.gc = gspread.authorize(creds)
        
        # Pre-defined skill keywords for extraction
        self.tech_skills = {
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js', 'django', 
            'flask', 'fastapi', 'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'aws', 
            'azure', 'gcp', 'docker', 'kubernetes', 'git', 'jenkins', 'terraform', 'ansible',
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
            'data science', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'tableau', 'powerbi',
            'html', 'css', 'bootstrap', 'sass', 'webpack', 'babel', 'typescript', 'graphql',
            'rest api', 'microservices', 'agile', 'scrum', 'devops', 'ci/cd', 'testing',
            'selenium', 'junit', 'pytest', 'cypress', 'linux', 'unix', 'bash', 'powershell'
        }
        
        self.position_levels = {
            'intern': 1, 'junior': 2, 'associate': 3, 'mid-level': 4, 'senior': 5,
            'lead': 6, 'principal': 7, 'manager': 8, 'director': 9, 'vp': 10, 'cto': 10, 'ceo': 10
        }
        
    def load_data_from_sheets(self, candidates_sheet_id: str, employers_sheet_id: str, 
                             companies_sheet_id: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Load data from Google Sheets
        """
        try:
            # Load candidates data
            candidates_sheet = self.gc.open_by_key(candidates_sheet_id).sheet1
            candidates_data = candidates_sheet.get_all_records()
            candidates_df = pd.DataFrame(candidates_data)
            
            # Load employers data
            employers_sheet = self.gc.open_by_key(employers_sheet_id).sheet1
            employers_data = employers_sheet.get_all_records()
            employers_df = pd.DataFrame(employers_data)
            
            # Load companies ranking data
            companies_sheet = self.gc.open_by_key(companies_sheet_id).sheet1
            companies_data = companies_sheet.get_all_records()
            companies_df = pd.DataFrame(companies_data)
            
            return candidates_df, employers_df, companies_df
            
        except Exception as e:
            print(f"Error loading data from sheets: {e}")
            return None, None, None
    
    def extract_years_of_experience(self, text: str) -> Dict[str, int]:
        """
        Extract years of experience using regex patterns
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with skills and their years of experience
        """
        text_lower = text.lower()
        skills_years = {}
        
        # Pattern to match "X years of [skill]" or "[skill] for X years"
        patterns = [
            r'(\d+)\s+years?\s+(?:of\s+)?(?:experience\s+(?:in\s+|with\s+)?)?([a-zA-Z\s\-\.]+)',
            r'([a-zA-Z\s\-\.]+)\s+for\s+(\d+)\s+years?',
            r'(\d+)\+?\s+years?\s+([a-zA-Z\s\-\.]+)',
            r'([a-zA-Z\s\-\.]+)\s+(\d+)\+?\s+years?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if len(match) == 2:
                    if match[0].isdigit():
                        years, skill = int(match[0]), match[1].strip()
                    else:
                        skill, years = match[0].strip(), int(match[1])
                    
                    # Check if it's a known tech skill
                    skill_clean = skill.strip()
                    for tech_skill in self.tech_skills:
                        if tech_skill in skill_clean or skill_clean in tech_skill:
                            skills_years[tech_skill] = max(skills_years.get(tech_skill, 0), years)
        
        return skills_years
    
    def extract_skills_with_spacy(self, text: str) -> Dict:
        """
        Extract structured information using spaCy or fallback method
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with extracted skills, years, companies, positions
        """
        if self.nlp:
            return self._extract_with_spacy(text)
        else:
            return self.extract_skills_basic(text)
    
    def _extract_with_spacy(self, text: str) -> Dict:
        """
        Extract using spaCy (when available)
        """
        doc = self.nlp(text)
        
        # Extract skills years
        skills_years = self.extract_years_of_experience(text)
        
        # Extract companies (organizations)
        companies = [ent.text for ent in doc.ents if ent.label_ in ["ORG"]]
        
        # Extract positions using common job title patterns
        positions = []
        job_keywords = ['engineer', 'developer', 'manager', 'analyst', 'specialist', 
                       'coordinator', 'director', 'lead', 'senior', 'junior', 'intern']
        
        for token in doc:
            if token.text.lower() in job_keywords:
                # Get surrounding context
                start = max(0, token.i - 2)
                end = min(len(doc), token.i + 3)
                position = doc[start:end].text
                positions.append(position)
        
        # Extract skills from predefined list
        found_skills = []
        text_lower = text.lower()
        for skill in self.tech_skills:
            if skill in text_lower:
                found_skills.append({
                    "skill": skill,
                    "years": skills_years.get(skill),
                    "company": companies[0] if companies else None,
                    "position": positions[0] if positions else None
                })
        
        return {"skills": found_skills}
    
    def extract_skills_basic(self, text: str) -> Dict:
        """
        Basic skill extraction using regex (fallback method)
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with extracted skills information
        """
        text_lower = text.lower()
        skills_years = self.extract_years_of_experience(text)
        
        # Extract companies using simple patterns
        company_patterns = [
            r'(?:at|@|with)\s+([A-Z][a-zA-Z\s&\.]+?)(?:\s|,|\.|\n)',
            r'([A-Z][a-zA-Z\s&\.]{2,})\s+(?:inc|corp|llc|ltd)',
        ]
        
        companies = []
        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            companies.extend([match.strip() for match in matches if len(match.strip()) > 2])
        
        # Extract positions
        position_keywords = ['engineer', 'developer', 'manager', 'analyst', 'specialist', 
                           'coordinator', 'director', 'lead', 'senior', 'junior']
        positions = []
        
        for keyword in position_keywords:
            pattern = rf'([a-zA-Z\s]*{keyword}[a-zA-Z\s]*)'
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            positions.extend([match.strip() for match in matches])
        
        # Find skills
        found_skills = []
        for skill in self.tech_skills:
            if skill in text_lower:
                found_skills.append({
                    "skill": skill,
                    "years": skills_years.get(skill),
                    "company": companies[0] if companies else None,
                    "position": positions[0] if positions else None
                })
        
        return {"skills": found_skills}
    
    def get_coordinates(self, location: str) -> Tuple[float, float]:
        """
        Get latitude and longitude for a location
        """
        try:
            location_obj = self.geolocator.geocode(location)
            if location_obj:
                return location_obj.latitude, location_obj.longitude
            else:
                return None, None
        except Exception as e:
            print(f"Error geocoding {location}: {e}")
            return None, None
    
    def calculate_distance(self, loc1: str, loc2: str) -> float:
        """
        Calculate distance between two locations in miles
        """
        coords1 = self.get_coordinates(loc1)
        coords2 = self.get_coordinates(loc2)
        
        if coords1[0] and coords2[0]:
            return geodesic(coords1, coords2).miles
        else:
            return float('inf')
    
    def get_company_ranking(self, company_name: str, companies_df: pd.DataFrame) -> int:
        """
        Get company ranking from the companies dataframe
        """
        if companies_df is None or company_name is None:
            return 1
            
        company_name_clean = company_name.lower().strip()
        for _, row in companies_df.iterrows():
            if company_name_clean in row['company_name'].lower():
                return row['ranking']
        
        return 1
    
    def calculate_position_score(self, positions: List[str]) -> float:
        """
        Calculate position seniority score
        """
        if not positions:
            return 1.0
            
        max_score = 1.0
        for position in positions:
            position_lower = position.lower() if position else ""
            for level, score in self.position_levels.items():
                if level in position_lower:
                    max_score = max(max_score, score / 10.0)  # Normalize to 0-1
        
        return max_score
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple text similarity using word overlap
        """
        # Convert to lowercase and split into words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0
    
    def create_candidate_features(self, candidate: Dict, companies_df: pd.DataFrame) -> Dict:
        """
        Create feature representation for a candidate
        """
        # Extract skills information
        skills_info = self.extract_skills_with_spacy(candidate['profile_details'])
        
        # Calculate aggregate metrics
        avg_years_experience = 0
        max_company_ranking = 1
        position_score = 1.0
        skill_count = len(skills_info['skills'])
        
        if skills_info['skills']:
            years_list = [s['years'] for s in skills_info['skills'] if s['years'] is not None]
            if years_list:
                avg_years_experience = np.mean(years_list)
            
            # Get maximum company ranking
            companies = [s['company'] for s in skills_info['skills'] if s['company']]
            if companies:
                rankings = [self.get_company_ranking(comp, companies_df) for comp in companies]
                max_company_ranking = max(rankings) if rankings else 1
            
            # Calculate position score
            positions = [s['position'] for s in skills_info['skills'] if s['position']]
            position_score = self.calculate_position_score(positions)
        
        return {
            'profile_text': candidate['profile_details'],
            'location': candidate['location'],
            'benefits_requirements': candidate['benefits_requirements'],
            'corporate_culture': candidate['corporate_culture'],
            'avg_years_experience': avg_years_experience,
            'max_company_ranking': max_company_ranking,
            'position_score': position_score,
            'skill_count': skill_count,
            'skills': skills_info['skills']
        }
    
    def create_job_features(self, job: Dict) -> Dict:
        """
        Create feature representation for a job
        """
        # Extract requirements
        requirements_info = self.extract_skills_with_spacy(job['job_requirements'])
        
        # Calculate required metrics
        required_years = 0
        required_seniority = 1.0
        required_skill_count = len(requirements_info['skills'])
        
        if requirements_info['skills']:
            years_list = [s['years'] for s in requirements_info['skills'] if s['years'] is not None]
            if years_list:
                required_years = np.mean(years_list)
        
        # Check for seniority requirements
        job_text_lower = job['job_requirements'].lower()
        for level, score in self.position_levels.items():
            if level in job_text_lower:
                required_seniority = max(required_seniority, score / 10.0)
        
        return {
            'job_requirements': job['job_requirements'],
            'location': job.get('location', 'Unknown'),
            'required_years': required_years,
            'required_seniority': required_seniority,
            'required_skill_count': required_skill_count,
            'skills': requirements_info['skills']
        }
    
    def calculate_matching_score(self, candidate_features: Dict, job_features: Dict) -> float:
        """
        Calculate matching score between candidate and job
        """
        # Text similarity (40% weight)
        text_similarity = self.calculate_text_similarity(
            candidate_features['profile_text'],
            job_features['job_requirements']
        )
        
        # Skills overlap (30% weight)
        candidate_skills = set(s['skill'] for s in candidate_features['skills'])
        job_skills = set(s['skill'] for s in job_features['skills'])
        
        if job_skills:
            skills_overlap = len(candidate_skills.intersection(job_skills)) / len(job_skills)
        else:
            skills_overlap = 0.5  # Neutral score if no specific skills mentioned
        
        # Experience match (20% weight)
        experience_diff = abs(candidate_features['avg_years_experience'] - job_features['required_years'])
        experience_score = max(0, 1 - (experience_diff / 10))  # Normalize to 0-1
        
        # Location proximity (10% weight)
        distance = self.calculate_distance(
            candidate_features['location'],
            job_features['location']
        )
        distance_score = max(0, 1 - (distance / 1000))  # Normalize distance
        
        # Calculate weighted final score
        final_score = (
            text_similarity * 0.4 +
            skills_overlap * 0.3 +
            experience_score * 0.2 +
            distance_score * 0.1
        )
        
        return final_score
    
    def extract_skills_analysis(self, candidates_df: pd.DataFrame, job_requirements: str) -> Dict:
        """
        Analyze skills sought by employer vs available among candidates
        """
        # Extract skills from job requirements
        job_skills = self.extract_skills_with_spacy(job_requirements)
        sought_skills = [skill['skill'] for skill in job_skills['skills']]
        
        # Extract skills from all candidates
        all_candidate_skills = []
        for _, candidate in candidates_df.iterrows():
            candidate_skills = self.extract_skills_with_spacy(candidate['profile_details'])
            all_candidate_skills.extend([skill['skill'] for skill in candidate_skills['skills']])
        
        # Find common skills
        available_skills = list(set(all_candidate_skills))
        matching_skills = [skill for skill in sought_skills if skill in available_skills]
        missing_skills = [skill for skill in sought_skills if skill not in available_skills]
        
        return {
            'sought_skills': sought_skills,
            'available_skills': available_skills,
            'matching_skills': matching_skills,
            'missing_skills': missing_skills,
            'skills_coverage': len(matching_skills) / len(sought_skills) if sought_skills else 0
        }
    
    def find_top_matches(self, job_id: str, candidates_df: pd.DataFrame, 
                        employers_df: pd.DataFrame, companies_df: pd.DataFrame, 
                        top_k: int = 5) -> Dict:
        """
        Find top matching candidates for a specific job
        """
        # Find the specific job
        job_row = employers_df[employers_df['id'] == job_id]
        if job_row.empty:
            return {
                'success': False,
                'error': f'Job {job_id} not found'
            }
        
        job = job_row.iloc[0]
        job_features = self.create_job_features({
            'job_requirements': job['job_requirements'],
            'location': job.get('location', 'Unknown')
        })
        
        # Calculate scores for all candidates
        candidate_scores = []
        
        for _, candidate in candidates_df.iterrows():
            candidate_features = self.create_candidate_features({
                'profile_details': candidate['profile_details'],
                'location': candidate['location'],
                'benefits_requirements': candidate['benefits_requirements'],
                'corporate_culture': candidate['corporate_culture']
            }, companies_df)
            
            score = self.calculate_matching_score(candidate_features, job_features)
            
            candidate_scores.append({
                'candidate_id': candidate['id'],
                'candidate_name': candidate.get('name', f"Candidate {candidate['id']}"),
                'score': round(score, 3),
                'location': candidate['location'],
                'profile_details': candidate['profile_details']
            })
        
        # Sort by score and get top matches
        candidate_scores.sort(key=lambda x: x['score'], reverse=True)
        top_matches = candidate_scores[:top_k]
        
        # Get skills analysis
        skills_analysis = self.extract_skills_analysis(candidates_df, job['job_requirements'])
        
        return {
            'job_id': job_id,
            'job_requirements': job['job_requirements'],
            'top_matches': top_matches,
            'skills_analysis': skills_analysis
        }

# Example usage
def main():
    # Initialize the system
    GOOGLE_CREDENTIALS_PATH = "path-to-your-google-credentials.json"
    
    matcher = FreeCandidateMatchingSystem(GOOGLE_CREDENTIALS_PATH)
    
    # Replace with your actual Google Sheets IDs
    CANDIDATES_SHEET_ID = "your-candidates-sheet-id"
    EMPLOYERS_SHEET_ID = "your-employers-sheet-id"
    COMPANIES_SHEET_ID = "your-companies-sheet-id"
    
    # Load data
    candidates_df, employers_df, companies_df = matcher.load_data_from_sheets(
        CANDIDATES_SHEET_ID, EMPLOYERS_SHEET_ID, COMPANIES_SHEET_ID
    )
    
    if candidates_df is not None:
        # Find matches for a specific job
        job_id = "job_001"
        results = matcher.find_top_matches(job_id, candidates_df, employers_df, companies_df)
        
        # Print results
        print(f"Top 5 matches for Job ID: {results['job_id']}")
        print(f"Job Requirements: {results['job_requirements']}")
        print("\nTop Matches:")
        
        for i, match in enumerate(results['top_matches'], 1):
            print(f"{i}. {match['candidate_name']} (ID: {match['candidate_id']})")
            print(f"   Score: {match['score']:.3f}")
            print(f"   Location: {match['location']}")
            print(f"   Profile: {match['profile_details'][:100]}...")
            print()
        
        print("Skills Analysis:")
        print(f"Skills sought: {results['skills_analysis']['sought_skills']}")
        print(f"Skills coverage: {results['skills_analysis']['skills_coverage']:.2%}")

if __name__ == "__main__":
    main()
