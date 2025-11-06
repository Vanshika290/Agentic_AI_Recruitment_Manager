from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import DeclarativeBase, relationship
import enum

class Base(DeclarativeBase):
    pass

class InterviewStatus(enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True)
    resume_text = Column(String)
    skills = Column(String)
    interviews = relationship("Interview", back_populates="candidate")

class Recruiter(Base):
    __tablename__ = "recruiters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True)
    specialization = Column(String)
    interviews = relationship("Interview", back_populates="recruiter")

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    recruiter_id = Column(Integer, ForeignKey("recruiters.id"))
    scheduled_time = Column(DateTime)
    status = Column(Enum(InterviewStatus))
    calendar_event_id = Column(String)
    candidate = relationship("Candidate", back_populates="interviews")
    recruiter = relationship("Recruiter", back_populates="interviews")

if __name__ == "__main__":
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///./interview_scheduler.db", echo=True)
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")