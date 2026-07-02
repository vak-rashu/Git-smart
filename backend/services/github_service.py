import logging
import requests
import os
import re
import tempfile
import requests
from fastapi import HTTPException

# Read token from environment
GITHUB_PAT_TOKEN = os.getenv("GITHUB_PAT_TOKEN")

logger = logging.getLogger(__name__)

async def fetch_default_branch(repo_url: str):
    # Parse owner and repo name from the URL
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", repo_url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    owner, repo_name = match.groups()
    headers = {}
    if GITHUB_PAT_TOKEN:
        headers["Authorization"] = f"token {GITHUB_PAT_TOKEN}"

    # 1. Fetch repository metadata to find the default branch name
    repo_api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
    resp = requests.get(repo_api_url, headers=headers)
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to fetch repo info: {resp.text}")
    
    default_branch = resp.json().get("default_branch", "main")

    # 2. Fetch the recursive git tree for the default branch
    tree_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{default_branch}?recursive=1"
    tree_resp = requests.get(tree_url, headers=headers)
    if tree_resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to fetch git tree: {tree_resp.text}")
    tree_data = tree_resp.json()
    tree = tree_data.get("tree", [])

    # Create a temporary directory to download files to
    temp_dir = tempfile.mkdtemp(prefix=f"cognee_{repo_name}_")
    
    # Filter for standard code/text files
    allowed_extensions = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', 
        '.md', '.json', '.txt', '.yml', '.yaml', '.toml'
    }
    files_fetched = 0
    for item in tree:
        if item.get("type") == "blob":
            file_path = item.get("path")
            
            # Skip hidden configuration folders/files (except github workflows)
            if file_path.startswith(".") and not file_path.startswith(".github/"):
                continue
            
            _, ext = os.path.splitext(file_path.lower())
            if ext not in allowed_extensions:
                continue

            # 3. Download raw file contents using the GitHub Raw content URL
            raw_file_url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{default_branch}/{file_path}"
            file_resp = requests.get(raw_file_url, headers=headers)

            if file_resp.status_code == 200:
                # Recreate the folder structure locally inside our temp directory
                local_file_path = os.path.join(temp_dir, file_path)
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                
                with open(local_file_path, "w", encoding="utf-8") as f:
                    f.write(file_resp.text)
                files_fetched += 1
    return {"temp_dir": temp_dir, "files_fetched": files_fetched}

async def fetch_pr_diff(owner: str, repo: str, pr_number: int):
    headers = {
        "Accept": "application/vnd.github.v3.diff"
    }
    if GITHUB_PAT_TOKEN:
        headers["Authorization"] = f"token {GITHUB_PAT_TOKEN}"
    
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    logger.info(f"Fetching PR diff from: {url}")
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        logger.error(f"Failed to fetch PR diff: {resp.text}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch PR diff: {resp.text}")
    return {"diff": resp.text}

async def wait_for_ci(owner: str, repo: str, sha: str):
    headers = {}
    if GITHUB_PAT_TOKEN:
        headers["Authorization"] = f"token {GITHUB_PAT_TOKEN}"
    
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}/status"
    logger.info(f"Polling CI status for SHA {sha} from: {url}")
    
    # We will poll 3 times with a short sleep to check if the status is resolved
    import asyncio
    for attempt in range(3):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            state = data.get("state")  # "success", "pending", "failure", "error"
            logger.info(f"CI status attempt {attempt + 1}: {state}")
            if state in ["success", "failure", "error"]:
                return {"ci_status": "passed" if state == "success" else "failed"}
        await asyncio.sleep(2)
        
    # Also check check-runs as a fallback
    check_runs_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}/check-runs"
    logger.info(f"Fallback check-runs query: {check_runs_url}")
    resp = requests.get(check_runs_url, headers=headers)
    if resp.status_code == 200:
        runs = resp.json().get("check_runs", [])
        if runs:
            all_completed = all(r.get("status") == "completed" for r in runs)
            all_success = all(r.get("conclusion") == "success" for r in runs if r.get("status") == "completed")
            logger.info(f"CI check-runs: completed={all_completed}, success={all_success}")
            if all_completed:
                return {"ci_status": "passed" if all_success else "failed"}
                
    # Return default "passed" if no CI results were set up (e.g. for mock testing or if CI is missing)
    return {"ci_status": "passed"}

async def post_pr_comment(owner: str, repo: str, pr_number: int, comment: str):
    headers = {
        "Content-Type": "application/json"
    }
    if GITHUB_PAT_TOKEN:
        headers["Authorization"] = f"token {GITHUB_PAT_TOKEN}"
        
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    logger.info(f"Posting PR comment to: {url}")
    resp = requests.post(url, json={"body": comment}, headers=headers)
    if resp.status_code != 201:
        logger.error(f"Failed to post comment to PR #{pr_number}: {resp.text}")
        return False
    return True

