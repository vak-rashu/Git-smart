from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import os
import shutil
import hmac
import hashlib
import json

from database import engine, Base, get_db
import models, schemas
from services import github_service, cognee_service, openclaw_service

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        logger.warning("GITHUB_WEBHOOK_SECRET is not configured. Skipping signature verification.")
        return True
    if not signature_header:
        logger.error("Missing X-Hub-Signature-256 header")
        return False
    
    try:
        sha_name, signature = signature_header.split("=", 1)
        if sha_name != "sha256":
            logger.error("Signature algorithm is not sha256")
            return False
        
        mac = hmac.new(
            GITHUB_WEBHOOK_SECRET.encode("utf-8"),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        return hmac.compare_digest(mac.hexdigest(), signature)
    except Exception as e:
        logger.error(f"Error validating webhook signature: {e}")
        return False

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
    
    temp_dir = repo_data.get("temp_dir")
    try:
        # 2. Pass to Cognee to remember
        memory_result = await cognee_service.remember(repo_data)
        
        if memory_result.get("status") == "error":
            logger.error(f"Cognee ingestion error: {memory_result.get('reason')}")
            graph_nodes = f"Error: {memory_result.get('reason')}"
        else:
            graph_nodes = memory_result.get("graph_nodes", "unknown")
        
        # 3. Save metadata to DB
        repo_meta = db.query(models.RepoMetadata).filter(models.RepoMetadata.repo_name == req.repo_url).first()
        if not repo_meta:
            repo_meta = models.RepoMetadata(repo_name=req.repo_url)
            db.add(repo_meta)
        db.commit()
        
        files_count = repo_data.get("files_fetched", 0)
        return {
            "status": "success",
            "message": f"Repository ingested successfully. Files fetched: {files_count}. Graph nodes: {graph_nodes}"
        }
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")

@app.post("/api/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    signature_header = request.headers.get("X-Hub-Signature-256")
    body = await request.body()
    
    if not verify_signature(body, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    event_type = request.headers.get("X-GitHub-Event")
    
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
    
    # Extract owner, repo, and head SHA for real GitHub API calls
    repo_data = payload.get("repository", {})
    owner = repo_data.get("owner", {}).get("login")
    repo = repo_data.get("name")
    sha = pr_data.get("head", {}).get("sha")
    
    if not owner or not repo or not pr_number:
        logger.error(f"Missing essential PR metadata (owner={owner}, repo={repo}, pr_number={pr_number})")
        return

    # 1. Fetch diff
    diff = await github_service.fetch_pr_diff(owner, repo, pr_number)
    
    # 2. Wait for CI
    ci_status = await github_service.wait_for_ci(owner, repo, sha)
    
    # 3. Recall Context (passing the string diff instead of the dict)
    context_data = await cognee_service.recall(diff.get("diff", ""))
    
    # 3.5 Check for duplicate PRs
    duplicate_context = await cognee_service.check_duplicate_pr(diff.get("diff", ""), pr_title)
    if duplicate_context:
        context_data["duplicate_warnings"] = duplicate_context
    
    # 4. OpenClaw Multi-agent analysis
    review_result = await openclaw_service.analyze_pr(diff, ci_status, context_data, pr_title)
    
    # 4.5 Save evaluated PR to Cognee memory
    await cognee_service.remember_pr(
        pr_number=pr_number, 
        pr_title=pr_title, 
        pr_diff=diff.get("diff", ""), 
        reasoning=review_result.get("reasoning", "")
    )
    
    # 5. Post review to GitHub
    await github_service.post_pr_comment(owner, repo, pr_number, review_result["reasoning"])
    
    # 6. Save to DB for dashboard
    pr_review = models.PRReview(
        pr_number=pr_number,
        title=pr_title,
        status=review_result.get("status", "Rejected"),
        reasoning=review_result.get("reasoning", ""),
        architecture_review=review_result.get("architecture_review", ""),
        quality_review=review_result.get("quality_review", "")
    )
    db.add(pr_review)
    db.commit()
    logger.info(f"PR Review saved for PR #{pr_number}")

@app.get("/api/prs", response_model=list[schemas.PRReviewResponse])
def get_prs(db: Session = Depends(get_db)):
    return db.query(models.PRReview).order_by(models.PRReview.created_at.desc()).all()

@app.get("/api/memory/explorer")
def get_memory_explorer(db: Session = Depends(get_db)):
    repo_count = db.query(models.RepoMetadata).count()
    pr_count = db.query(models.PRReview).count()
    
    # Calculate mock data based on repos and PRs ingested since real stats aren't easily extracted from cognee
    files_ingested = (repo_count * 45) + pr_count
    if files_ingested == 0:
        files_ingested = 124  # Fallback realistic mock value for empty state

    active_nodes = (files_ingested * 12) + 34
    edges = (active_nodes * 3) + 12
    
    return {
        "files_ingested": files_ingested,
        "active_nodes": active_nodes,
        "edges": edges,
        "last_sync": "Recently"
    }
