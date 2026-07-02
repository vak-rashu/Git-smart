from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PRReviewResponse(BaseModel):
    id: int
    pr_number: int
    title: str
    status: str
    reasoning: Optional[str] = None
    architecture_review: Optional[str] = None
    quality_review: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True

class IngestRepoRequest(BaseModel):
    repo_url: str
