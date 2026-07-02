from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging

from database import engine, Base, get_db
import models, schemas
from services import github_service, cognee_service, openclaw_service

# Initialize DB
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GitHub Native Companion Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/repo/ingest")
async def ingest_repository(req: schemas.IngestRepoRequest, db: Session = Depends(get_db)):
    logger.info(f"Triggered ingestion for {req.repo_url}")
    
    # 1. Fetch repo data
    repo_data = await github_service.fetch_default_branch(req.repo_url)
    
    # 2. Pass to Cognee to remember
    memory_result = await cognee_service.remember(repo_data)
    
    # 3. Save metadata to DB
    repo_meta = db.query(models.RepoMetadata).filter(models.RepoMetadata.repo_name == req.repo_url).first()
    if not repo_meta:
        repo_meta = models.RepoMetadata(repo_name=req.repo_url)
        db.add(repo_meta)
    db.commit()
    
    return {"status": "success", "message": f"Repository ingested successfully. Graph nodes: {memory_result['graph_nodes']}"}

@app.post("/api/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    event_type = request.headers.get("X-GitHub-Event")
    payload = await request.json()
    
    # Log the webhook event
    event_record = models.WebhookEvent(event_type=event_type, payload=str(payload))
    db.add(event_record)
    db.commit()

    if event_type == "push":
        logger.info("Received push webhook")
        background_tasks.add_task(handle_push_event, payload)
        return {"status": "accepted"}
        
    elif event_type == "pull_request":
        logger.info("Received pull_request webhook")
        action = payload.get("action")
        if action in ["opened", "synchronize"]:
            background_tasks.add_task(handle_pr_event, payload, db)
        return {"status": "accepted"}
        
    return {"status": "ignored"}

async def handle_push_event(payload: dict):
    # Mock extracting commits
    commits = payload.get("commits", [])
    added = []
    modified = []
    removed = []
    for c in commits:
        added.extend(c.get("added", []))
        modified.extend(c.get("modified", []))
        removed.extend(c.get("removed", []))
        
    if added or modified:
        await cognee_service.improve(added, modified)
    if removed:
        await cognee_service.forget(removed)

async def handle_pr_event(payload: dict, db: Session):
    pr_data = payload.get("pull_request", {})
    pr_number = pr_data.get("number")
    pr_title = pr_data.get("title", f"PR #{pr_number}")
    
    # 1. Fetch diff
    diff = await github_service.fetch_pr_diff(pr_number)
    
    # 2. Wait for CI
    ci_status = await github_service.wait_for_ci(pr_number)
    
    # 3. Recall Context
    context = await cognee_service.recall(diff)
    
    # 4. OpenClaw Multi-agent analysis
    review_result = await openclaw_service.analyze_pr(diff, ci_status, context, pr_title)
    
    # 5. Post review to GitHub
    await github_service.post_pr_comment(pr_number, review_result["reasoning"])
    
    # 6. Save to DB for dashboard
    pr_review = models.PRReview(
        pr_number=pr_number,
        title=pr_title,
        status=review_result["status"],
        reasoning=review_result["reasoning"]
    )
    db.add(pr_review)
    db.commit()
    logger.info(f"PR Review saved for PR #{pr_number}")

@app.get("/api/prs", response_model=list[schemas.PRReviewResponse])
def get_prs(db: Session = Depends(get_db)):
    return db.query(models.PRReview).order_by(models.PRReview.created_at.desc()).all()
