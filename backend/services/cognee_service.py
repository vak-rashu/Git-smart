import logging
import os
from dotenv import load_dotenv

load_dotenv()
if "GEMINI_API_KEY" in os.environ:
    os.environ["LLM_API_KEY"] = os.environ["GEMINI_API_KEY"]

import cognee
import ontology

logger = logging.getLogger(__name__)

# Initialize custom Software Engineering Ontology for Cognee
ontology.init_ontology()

_connected = False

async def ensure_cognee_connection():
    global _connected
    if _connected:
        return
    
    cognee_url = os.getenv("COGNEE_SERVICE_URL")
    cognee_key = os.getenv("COGNEE_API_KEY")
    
    if cognee_key:
        logger.info(f"Cognee: Connecting to remote instance/cloud at {cognee_url or 'default cloud'}...")
        try:
            # Route all subsequent SDK actions to the cloud tenant
            await cognee.serve(url=cognee_url, api_key=cognee_key)
            _connected = True
            logger.info("Cognee: Remote/Cloud connection established successfully.")
        except Exception as e:
            logger.error(f"Cognee: Failed to establish remote serve connection: {e}. Falling back to local.")
    else:
        logger.info("Cognee: COGNEE_API_KEY not set. Operating in local mode.")

async def remember(repo_url: str):
    await ensure_cognee_connection()
    logger.info(f"Cognee: Ingesting repository directly in the cloud: {repo_url}")
    
    try:
        # Cognee Cloud is designed to ingest GitHub URLs directly without local cloning
        await cognee.add(repo_url, dataset_name="main_dataset")
        await cognee.cognify(datasets=["main_dataset"])
        
        logger.info("Cognee: Cloud ingestion and cognify process completed.")
        return {"status": "success", "graph_nodes": "unknown (cognified in the cloud)"}
    except Exception as e:
        logger.error(f"Cognee cloud ingestion failed: {e}", exc_info=True)
        return {"status": "error", "reason": str(e)}

async def improve(owner: str, repo_name: str, added_files: list, modified_files: list):
    await ensure_cognee_connection()
    logger.info(f"Cognee: Re-syncing memory graph for repository: {owner}/{repo_name}")
    try:
        repo_url = f"https://github.com/{owner}/{repo_name}"
        # We re-add and re-cognify the repo URL. Cognee Cloud handles changes incrementally
        await cognee.add(repo_url, dataset_name="main_dataset")
        await cognee.cognify(datasets=["main_dataset"])
    except Exception as e:
        logger.error(f"Cognee improve failed: {e}", exc_info=True)
        return {"status": "error", "reason": str(e)}
    return {"status": "success"}

async def forget(owner: str, repo_name: str, deleted_files: list):
    await ensure_cognee_connection()
    logger.info(f"Cognee: Forgetting deleted files for repository: {owner}/{repo_name}")
    try:
        if deleted_files:
            await cognee.forget(deleted_files)
    except Exception as e:
        logger.error(f"Cognee forget failed: {e}", exc_info=True)
        return {"status": "error", "reason": str(e)}
    return {"status": "success"}

async def recall(diff_context: str):
    await ensure_cognee_connection()
    logger.info("Cognee: Recalling architectural context based on diff...")
    
    try:
        search_results = await cognee.recall(diff_context)
        
        formatted_results = []
        for res in search_results:
            if hasattr(res, 'text'):
                formatted_results.append(res.text)
            elif isinstance(res, dict) and 'text' in res:
                formatted_results.append(res['text'])
            else:
                formatted_results.append(str(res))
                
        context_str = "\n\n".join(formatted_results) if formatted_results else "No relevant context found."
        return {"context": context_str}
    except Exception as e:
        logger.error(f"Cognee recall failed: {e}")
        return {"context": "Failed to retrieve context due to error."}

async def remember_pr(pr_number: int, pr_title: str, pr_diff: str, reasoning: str):
    await ensure_cognee_connection()
    logger.info(f"Cognee: Remembering PR #{pr_number}")
    try:
        pr_obj = ontology.PullRequest(
            pr_number=pr_number,
            title=pr_title,
            diff=pr_diff,
            status="Reviewed",
            reasoning=reasoning
        )
        from cognee.tasks.storage import add_data_points
        await add_data_points([pr_obj])
        return True
    except Exception as e:
        logger.error(f"Failed to remember PR {pr_number}: {e}")
        return False

async def check_duplicate_pr(pr_diff: str, pr_title: str):
    await ensure_cognee_connection()
    logger.info("Cognee: Checking for duplicate or similar PRs...")
    try:
        query = f"Are there any past Pull Requests that implemented similar changes to '{pr_title}' or this diff?\nDiff:\n{pr_diff}"
        search_results = await cognee.recall(query)
        context_str = "\n".join([str(res) for res in search_results]) if search_results else ""
        return context_str
    except Exception as e:
        logger.error(f"Failed to check duplicate PR: {e}")
        return ""
