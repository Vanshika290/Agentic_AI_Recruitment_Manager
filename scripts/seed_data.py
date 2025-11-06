import os
import sys
from datetime import datetime, timedelta

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.models import Base, Candidate, Recruiter, Interview, InterviewStatus

# Database configuration
DATABASE_URL = "sqlite:///./interview_scheduler.db"

def seed_test_data():
    print(f"Creating database at: {os.path.abspath('interview_scheduler.db')}")
    
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    # Create session
    session = Session(engine)
    
    try:
        # Add test candidates
        candidates = [
            Candidate(
                name="John Doe",
                email="john@example.com",
                skills="Python, SQL, FastAPI",
                resume_text="Experienced software developer..."
            ),
            Candidate(
                name="Jane Smith",
                email="jane@example.com",
                skills="React, Node.js, TypeScript",
                resume_text="Frontend developer with 5 years..."
            )
        ]
        session.add_all(candidates)
        print("Added candidates")
        
        # Add test recruiters
        recruiters = [
            Recruiter(
                name="Alice Johnson",
                email="alice@company.com",
                specialization="Technical Recruiting"
            ),
            Recruiter(
                name="Bob Wilson",
                email="bob@company.com",
                specialization="Full-Stack Engineering"
            )
        ]
        session.add_all(recruiters)
        print("Added recruiters")
        
        # Commit to get IDs
        session.commit()
        
        # Add test interviews
        interviews = [
            Interview(
                candidate_id=candidates[0].id,
                recruiter_id=recruiters[0].id,
                scheduled_time=datetime.now() + timedelta(days=1),
                status=InterviewStatus.SCHEDULED,
                calendar_event_id="test_event_1"
            ),
            Interview(
                candidate_id=candidates[1].id,
                recruiter_id=recruiters[1].id,
                scheduled_time=datetime.now() + timedelta(days=2),
                status=InterviewStatus.SCHEDULED,
                calendar_event_id="test_event_2"
            )
        ]
        session.add_all(interviews)
        session.commit()
        print("Added interviews")
        
        print("Test data added successfully!")
        
    except Exception as e:
        print(f"Error adding test data: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    seed_test_data()