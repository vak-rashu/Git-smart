import uuid
from sqlalchemy.sql.sqltypes import UUID

# Patch SQLAlchemy UUID bind_processor to handle string UUID inputs on SQLite / character-based databases
original_bind_processor = UUID.bind_processor

def patched_bind_processor(self, dialect):
    proc = original_bind_processor(self, dialect)
    if proc is not None:
        def wrapped_process(value):
            if value is not None:
                if isinstance(value, str):
                    if self.as_uuid:
                        try:
                            return uuid.UUID(value).hex
                        except ValueError:
                            return value.replace("-", "")
                    else:
                        return value.replace("-", "")
                elif hasattr(value, "hex"):
                    return value.hex
                elif isinstance(value, uuid.UUID):
                    if self.as_uuid:
                        return value.hex
                    else:
                        return str(value).replace("-", "")
            return value
        return wrapped_process
    return proc

UUID.bind_processor = patched_bind_processor

from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import os
import shutil
import hmac
import hashlib
import json

from database import engine, Base, get_db, SessionLocal
import models, schemas
from services import github_service, cognee_service, openclaw_service

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

# def verify_signature(payload_body: bytes, signature_header: str) -> bool:
#     if not GITHUB_WEBHOOK_SECRET:
#         logger.warning("GITHUB_WEBHOOK_SECRET is not configured. Skipping signature verification.")
#         return True
#     if not signature_header:
#         logger.error("Missing X-Hub-Signature-256 header")
#         return False
    
#     try:
#         sha_name, signature = signature_header.split("=", 1)
#         if sha_name != "sha256":
#             logger.error("Signature algorithm is not sha256")
#             return False
        
#         mac = hmac.new(
#             GITHUB_WEBHOOK_SECRET.encode("utf-8"),
#             msg=payload_body,
#             digestmod=hashlib.sha256
#         )
#         return hmac.compare_digest(mac.hexdigest(), signature)
#     except Exception as e:
#         logger.error(f"Error validating webhook signature: {e}")
#         return False

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
    
    try:
        # Pass to Cognee to remember (downloads code and DLT data)
        memory_result = await cognee_service.remember(req.repo_url)
        
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
        
        return {
            "status": "success",
            "message": f"Repository ingested successfully. Graph nodes: {graph_nodes}"
        }
    except Exception as e:
        logger.error(f"Unexpected error during ingestion: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
@app.post("/api/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    signature_header = request.headers.get("X-Hub-Signature-256")
    body = await request.body()
    
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
        action = payload.get("action")
        logger.info(f"Received pull_request webhook with action: {action}")
        if action in ["opened", "synchronize"]:
            pr_data = payload.get("pull_request", {})
            pr_number = pr_data.get("number")
            pr_title = pr_data.get("title", f"PR #{pr_number}")
            repo_data = payload.get("repository", {})
            owner = repo_data.get("owner", {}).get("login")
            repo = repo_data.get("name")
            sha = pr_data.get("head", {}).get("sha")
            
            if owner and repo and pr_number and sha:
                # Add or update pending PR record
                pending_pr = db.query(models.PendingPR).filter(
                    models.PendingPR.owner == owner,
                    models.PendingPR.repo == repo,
                    models.PendingPR.pr_number == pr_number
                ).first()
                if not pending_pr:
                    pending_pr = models.PendingPR(
                        owner=owner,
                        repo=repo,
                        pr_number=pr_number,
                        title=pr_title,
                        sha=sha,
                        ci_status="pending"
                    )
                    db.add(pending_pr)
                else:
                    pending_pr.sha = sha
                    pending_pr.title = pr_title
                    pending_pr.ci_status = "pending"
                db.commit()
                logger.info(f"Saved PendingPR #{pr_number} with head SHA {sha}. Waiting for CI/CD webhook...")
        return {"status": "accepted"}
        
    elif event_type == "status":
        sha = payload.get("sha")
        state = payload.get("state")  # "pending", "success", "failure", "error"
        repo_data = payload.get("repository", {})
        owner = repo_data.get("owner", {}).get("login")
        repo = repo_data.get("name")
        
        logger.info(f"Received status webhook for SHA {sha}: state={state}")
        if state in ["success", "failure", "error"] and sha and owner and repo:
            ci_status_str = "passed" if state == "success" else "failed"
            pending_pr = db.query(models.PendingPR).filter(
                models.PendingPR.owner == owner,
                models.PendingPR.repo == repo,
                models.PendingPR.sha == sha
            ).first()
            if pending_pr:
                background_tasks.add_task(
                    handle_pending_pr_review,
                    owner,
                    repo,
                    pending_pr.pr_number,
                    pending_pr.title,
                    sha,
                    ci_status_str
                )
        return {"status": "accepted"}
        
    elif event_type in ["check_run", "check_suite"]:
        suite = payload.get("check_suite") or payload.get("check_run", {}).get("check_suite")
        if not suite:
            run = payload.get("check_run", {})
            head_sha = run.get("head_sha")
            status = run.get("status")
            conclusion = run.get("conclusion")
        else:
            head_sha = suite.get("head_sha")
            status = suite.get("status")
            conclusion = suite.get("conclusion")
            
        repo_data = payload.get("repository", {})
        owner = repo_data.get("owner", {}).get("login")
        repo = repo_data.get("name")
        
        logger.info(f"Received check webhook for SHA {head_sha}: status={status}, conclusion={conclusion}")
        if status == "completed" and head_sha and owner and repo:
            ci_status_str = "passed" if conclusion == "success" else "failed"
            pending_pr = db.query(models.PendingPR).filter(
                models.PendingPR.owner == owner,
                models.PendingPR.repo == repo,
                models.PendingPR.sha == head_sha
            ).first()
            if pending_pr:
                background_tasks.add_task(
                    handle_pending_pr_review,
                    owner,
                    repo,
                    pending_pr.pr_number,
                    pending_pr.title,
                    head_sha,
                    ci_status_str
                )
        return {"status": "accepted"}
        
    return {"status": "ignored"}

async def handle_push_event(payload: dict):
    repo_data = payload.get("repository", {})
    owner = repo_data.get("owner", {}).get("login")
    repo_name = repo_data.get("name")
    
    if not owner or not repo_name:
        logger.error("Push event missing owner or repo name.")
        return
        
    commits = payload.get("commits", [])
    added = []
    modified = []
    removed = []
    for c in commits:
        added.extend(c.get("added", []))
        modified.extend(c.get("modified", []))
        removed.extend(c.get("removed", []))
        
    if added or modified:
        await cognee_service.improve(owner, repo_name, added, modified)
    if removed:
        await cognee_service.forget(owner, repo_name, removed)

async def handle_pending_pr_review(owner: str, repo: str, pr_number: int, pr_title: str, sha: str, ci_status_str: str):
    db = SessionLocal()
    try:
        # Check if already reviewed to avoid duplicates
        existing = db.query(models.PRReview).filter(
            models.PRReview.pr_number == pr_number,
            models.PRReview.title == pr_title
        ).first()
        if existing:
            logger.info(f"PR #{pr_number} has already been reviewed. Skipping.")
            return

        logger.info(f"Running automated review orchestration for PR #{pr_number} with CI/CD status: {ci_status_str}")
        
        # 1. Fetch diff
        diff = await github_service.fetch_pr_diff(owner, repo, pr_number)
        
        # 2. CI status data
        ci_status = {"ci_status": ci_status_str}
        
        # 3. Recall Context from Cognee
        diff_recall = await cognee_service.recall(diff.get("diff", ""))
        diff_context = diff_recall.get("context", "No context found.")
        
        infra_recall = await cognee_service.recall("What databases, caches (like Redis), libraries, frameworks, or external services are used in this codebase?")
        infra_context = infra_recall.get("context", "No context found.")
        
        combined_context = (
            f"=== Repository Infrastructure & Tech Stack ===\n{infra_context}\n\n"
            f"=== Diff-Specific Architecture Context ===\n{diff_context}"
        )
        context_data = {"context": combined_context}
        
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
        
        # Clean up PendingPR table for this SHA
        db.query(models.PendingPR).filter(models.PendingPR.sha == sha).delete()
        db.commit()
        logger.info(f"PR Review saved and pending PR cleared for PR #{pr_number}")
    except Exception as e:
        logger.error(f"Error in handle_pending_pr_review: {str(e)}", exc_info=True)
    finally:
        db.close()

@app.get("/api/prs", response_model=list[schemas.PRReviewResponse])
def get_prs(db: Session = Depends(get_db)):
    return db.query(models.PRReview).order_by(models.PRReview.created_at.desc()).all()


@app.get("/api/search")
async def search_memory(q: str):
    logger.info(f"Searching Cognee memory for: {q}")
    if not q:
        return {"results": "Please provide a query."}
    
    try:
        search_response = await cognee_service.recall(q)
        return {"results": search_response.get("context", "No results found.")}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_memory(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    logger.info(f"Chat query: {req.query}, pr_number={req.pr_number}")
    if not req.query:
        return {"answer": "Please provide a query."}
        
    try:
        # 1. Recall from Cognee
        cognee_recall = await cognee_service.recall(req.query)
        codebase_context = cognee_recall.get("context", "No context found.")
        
        # 2. Get PR review details if pr_number is provided
        pr_context = ""
        if req.pr_number:
            pr_db = db.query(models.PRReview).filter(models.PRReview.pr_number == req.pr_number).first()
            if pr_db:
                pr_context = (
                    f"=== Selected PR #{pr_db.pr_number} review context ===\n"
                    f"Title: {pr_db.title}\n"
                    f"Status: {pr_db.status}\n"
                    f"Decision Reasoning: {pr_db.reasoning}\n"
                    f"Architecture Review: {pr_db.architecture_review}\n"
                    f"Quality Review: {pr_db.quality_review}\n"
                )
                
        # 3. Call OpenClaw Agent
        from openclaw_sdk import OpenClawClient, Agent
        client = await OpenClawClient.connect()
        chat_agent = Agent(client=client, agent_id="chat-assistant")
        
        prompt = f"""
        You are a highly capable Software Engineering Assistant.
        Your goal is to answer the user's questions responsibly and accurately by analyzing the codebase context and the current pull request review details provided.
        
        User Query: {req.query}
        
        Codebase Architecture Context from Cognee:
        {codebase_context}
        
        {pr_context}
        
        Please provide a detailed, rich, developer-centric answer.
        - If comparing coding patterns or code changes, use clear before-and-after structures or comparisons.
        - Point out if a design pattern aligns with the codebase's existing structures.
        - Answer objectively and cite the architectural context when possible.
        """
        
        result = await chat_agent.execute(prompt)
        answer = result.content if result else "No answer returned from OpenClaw."
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Chat query failed: {e}", exc_info=True)
        return {"answer": f"Error: {e}"}
