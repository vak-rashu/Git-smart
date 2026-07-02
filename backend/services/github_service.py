import logging

logger = logging.getLogger(__name__)

async def fetch_default_branch(repo_url: str):
    logger.info(f"Mock: Fetching default branch for {repo_url}")
    return {"status": "success", "files_fetched": 150}

async def fetch_pr_diff(pr_number: int):
    logger.info(f"Mock: Fetching PR diff for PR #{pr_number}")
    return {"diff": "+ added some code\n- removed some code"}

async def wait_for_ci(pr_number: int):
    logger.info(f"Mock: Polling CI status for PR #{pr_number}...")
    return {"ci_status": "passed"}

async def post_pr_comment(pr_number: int, comment: str):
    logger.info(f"Mock: Posting comment to PR #{pr_number}: {comment}")
    return True
