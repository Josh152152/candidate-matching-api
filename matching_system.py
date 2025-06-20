import pandas as pd
import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
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
        Initialize the matching system with free alternatives
        
        Args:
            google_credentials_path: Path to Google service account credentials JSON
        """
        # Load free NLP models
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')  # Free sentence embeddings
        
        # Load spaCy model for NLP (download with: python -m spacy download en_core_web_sm)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Please install spaCy English model: python -m spacy download en_core_web_sm")
            self.nlp = None
            
        self.scaler = MinMaxScaler()
        self.geolocator = Nominatim(user_agent="candidate_matcher")
        
        # Initialize Google Sheets connection
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(google_credentials_path, scopes=scope)
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
        Extract years of experience using regex patterns (FREE alternative to OpenAI)
        
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
        Extract structured information using spaCy (FREE alternative to OpenAI)
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary with extracted skills, years, companies, positions
        """
        if not self.nlp:
            return self.extract_skills_basic(text)
            
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
        Get latitude and longitude for a location (FREE using Nominatim)
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
        Calculate distance between two locations in miles (FREE)
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
    
    def create_candidate_vector(self, candidate: Dict, companies_df: pd.DataFrame) -> np.ndarray:
        """
        Create vector representation for a candidate using FREE tools
        """
        # Extract skills information using spaCy/regex
        skills_info = self.extract_skills_with_spacy(candidate['profile_details'])
        
        # Create embeddings for text fields (FREE with sentence-transformers)
        profile_embedding = self.sentence_model.encode(candidate['profile_details'])
        location_embedding = self.sentence_model.encode(candidate['location'])
        benefits_embedding = self.sentence_model.encode(candidate['benefits_requirements'])
        culture_embedding = self.sentence_model.encode(candidate['corporate_culture'])
        
        # Calculate aggregate metrics
        avg_years_experience = 0
        max_company_ranking = 1
        position_score = 1.0
        
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
        
        # Combine all features
        feature_vector = np.concatenate([
            profile_embedding,
            location_embedding,
            benefits_embedding,
            culture_embedding,
            [avg_years_experience, max_company_ranking, position_score]
        ])
        
        return feature_vector
    
    def create_job_vector(self, job: Dict) -> np.ndarray:
        """
        Create vector representation for a job using FREE tools
        """
        # Create embeddings for job requirements
        job_embedding = self.sentence_model.encode(job['job_requirements'])
        
        # Extract requirements using free methods
        requirements_info = self.extract_skills_with_spacy(job['job_requirements'])
        
        # Calculate required metrics
        required_years = 0
        required_seniority = 1.0
        
        if requirements_info['skills']:
            years_list = [s['years'] for s in requirements_info['skills'] if s['years'] is not None]
            if years_list:
                required_years = np.mean(years_list)
        
        # Check for seniority requirements
        job_text_lower = job['job_requirements'].lower()
        for level, score in self.position_levels.items():
            if level in job_text_lower:
                required_seniority = max(required_seniority, score / 10.0)
        
        # Pad to match candidate vector length
        padding_size = 384 * 4 + 3 - len(job_embedding)
        padded_vector = np.concatenate([
            job_embedding,
            np.zeros(max(0, padding_size - 2)),
            [required_years, required_seniority]
        ])
        
        return padded_vector
    
    def calculate_matching_score(self, candidate_vector: np.ndarray, job_vector: np.ndarray,
                                candidate_location: str, job_location: str) -> float:
        """
        Calculate matching score between candidate and job
        """
        # Ensure vectors are same length
        min_length = min(len(candidate_vector), len(job_vector))
        candidate_vector = candidate_vector[:min_length]
        job_vector = job_vector[:min_length]
        
        # Calculate cosine similarity for skills/profile match
        profile_similarity = cosine_similarity([candidate_vector], [job_vector])[0][0]
        
        # Calculate distance penalty (FREE with Nominatim)
        distance = self.calculate_distance(candidate_location, job_location)
        distance_score = max(0, 1 - (distance / 1000))  # Normalize distance
        
        # Weighted final score
        final_score = (
            profile_similarity * 0.7 +  # 70% weight on profile match
            distance_score * 0.3        # 30% weight on location proximity
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
        Find top matching candidates for a specific job using FREE tools only
        """
        # Find the specific job
        job = employers_df[employers_df['id'] == job_id].iloc[0]
        job_location = job.get('location', 'Unknown')
        
        # Create job vector
        job_dict = {
            'job_requirements': job['job_requirements']
        }
        job_vector = self.create_job_vector(job_dict)
        
        # Calculate scores for all candidates
        candidate_scores = []
        
        for _, candidate in candidates_df.iterrows():
            candidate_dict = {
                'profile_details': candidate['profile_details'],
                'location': candidate['location'],
                'benefits_requirements': candidate['benefits_requirements'],
                'corporate_culture': candidate['corporate_culture']
            }
            
            candidate_vector = self.create_candidate_vector(candidate_dict, companies_df)
            
            score = self.calculate_matching_score(
                candidate_vector, job_vector,
                candidate['location'], job_location
            )
            
            candidate_scores.append({
                'candidate_id': candidate['id'],
                'candidate_name': candidate.get('name', f"Candidate {candidate['id']}"),
                'score': score,
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

# Example usage with FREE tools only
def main():
    # Initialize the system (NO OpenAI API key needed!)
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