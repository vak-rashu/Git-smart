from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base
from datetime import datetime

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True)
    payload = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class PRReview(Base):
    __tablename__ = "pr_reviews"

    id = Column(Integer, primary_key=True, index=True)
    pr_number = Column(Integer, index=True)
    title = Column(String)
    status = Column(String) # "Accepted", "Rejected", "Pending"
    reasoning = Column(Text)
    architecture_review = Column(Text, nullable=True)
    quality_review = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
class RepoMetadata(Base):
    __tablename__ = "repo_metadata"

    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String, unique=True, index=True)
    last_ingested = Column(DateTime, default=datetime.utcnow)

class PendingPR(Base):
    __tablename__ = "pending_prs"

    id = Column(Integer, primary_key=True, index=True)
    owner = Column(String, index=True)
    repo = Column(String, index=True)
    pr_number = Column(Integer, index=True)
    title = Column(String)
    sha = Column(String, index=True)
    ci_status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
