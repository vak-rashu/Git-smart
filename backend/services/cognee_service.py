import logging
import os
import glob
from dotenv import load_dotenv

load_dotenv()
if "GEMINI_API_KEY" in os.environ:
    os.environ["LLM_API_KEY"] = os.environ["GEMINI_API_KEY"]

import cognee
import ontology

logger = logging.getLogger(__name__)

# Initialize custom Software Engineering Ontology for Cognee
ontology.init_ontology()

async def remember(repo_url: str):
    logger.info("Cognee: Remembering repository data (Initial Ingestion)")

    try:
        await cognee.remember(repo_url)
        return {"status": "success", "graph_nodes": "unknown (cognified via remember)"}
    except Exception as e:
        logger.error(f"Cognee ingestion failed: {e}")
        return {"status": "error", "reason": str(e)}

# async def remember(repo_data: dict):
#     logger.info("Cognee: Remembering repository data (Initial Ingestion)")
#     temp_dir = repo_data.get("temp_dir")
    
#     if not temp_dir:
#         return {"status": "failed", "reason": "No temporary directory provided"}
        
#     try:
#         await cognee.remember(f"data://{temp_dir}")
#         return {"status": "success", "graph_nodes": "unknown (cognified via remember)"}
#     except Exception as e:
#         logger.error(f"Cognee ingestion failed: {e}")
#         return {"status": "error", "reason": str(e)}

# async def improve(added_files: list, modified_files: list):
#     logger.info(f"Cognee: Improving memory graph with {len(added_files)} added, {len(modified_files)} modified files.")
#     try:
#         await cognee.improve(added_files + modified_files)
#     except Exception as e:
#         logger.error(f"Cognee improve failed: {e}")
#         return {"status": "error", "reason": str(e)}
#     return {"status": "success"}

async def improve(added_files: list, modified_files: list):
    logger.info(f"Cognee: Improving memory graph with {len(added_files)} added, {len(modified_files)} modified files.")
    try:
        await cognee.improve(added_files + modified_files)
    except Exception as e:
        logger.error(f"Cognee improve failed: {e}")
        return {"status": "error", "reason": str(e)}
    return {"status": "success"}

async def forget(deleted_files: list):
    logger.info(f"Cognee: Forgetting {len(deleted_files)} deleted files from memory graph.")
    try:
        # Instruct cognee to forget the deleted entities/files
        await cognee.forget(deleted_files)
    except Exception as e:
        logger.error(f"Cognee forget failed: {e}")
        return {"status": "error", "reason": str(e)}
    return {"status": "success"}

async def recall(diff_context: str):
    logger.info("Cognee: Recalling architectural context based on diff...")
    
    try:
        search_results = await cognee.recall(diff_context)
        context_str = "\n".join([str(res) for res in search_results]) if search_results else "No relevant context found."
        return {"context": context_str}
    except Exception as e:
        logger.error(f"Cognee recall failed: {e}")
        return {"context": "Failed to retrieve context due to error."}

async def remember_pr(pr_number: int, pr_title: str, pr_diff: str, reasoning: str):
    logger.info(f"Cognee: Remembering PR #{pr_number}")
    pr_data = f"Past Pull Request #{pr_number}: {pr_title}\nDiff: {pr_diff}\nAgent Reasoning: {reasoning}"
    try:
        await cognee.remember(pr_data)
        return True
    except Exception as e:
        logger.error(f"Failed to remember PR {pr_number}: {e}")
        return False

async def check_duplicate_pr(pr_diff: str, pr_title: str):
    logger.info("Cognee: Checking for duplicate or similar PRs...")
    try:
        query = f"Are there any past Pull Requests that implemented similar changes to '{pr_title}' or this diff?\nDiff:\n{pr_diff}"
        search_results = await cognee.recall(query)
        context_str = "\n".join([str(res) for res in search_results]) if search_results else ""
        return context_str
    except Exception as e:
        logger.error(f"Failed to check duplicate PR: {e}")
        return ""
