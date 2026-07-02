import logging
import json
import litellm
import os

logger = logging.getLogger(__name__)

async def call_agent(system_prompt: str, user_prompt: str) -> str:
    try:
        response = litellm.completion(
            model="gemini/gemini-1.5-flash", 
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Agent call failed: {e}")
        return "Agent analysis failed due to an error."

async def analyze_pr(pr_diff: dict, ci_results: dict, cognee_context: dict, pr_title: str = ""):
    logger.info("OpenClaw: Orchestrating multi-agent workflow...")
    
    diff_text = pr_diff.get('diff', 'No diff')
    architecture_context = cognee_context.get('context', 'No context')
    duplicate_warnings = cognee_context.get('duplicate_warnings', '')
    
    # 1. Architecture Agent
    arch_prompt = f"PR Title: {pr_title}\nDiff:\n{diff_text}\nRepository Architecture Context:\n{architecture_context}"
    arch_analysis = await call_agent(
        "You are an Architecture Review Agent. Evaluate if the PR diff aligns with the repository's established architecture.",
        arch_prompt
    )
    
    # 2. Code Quality & CI Agent
    cq_prompt = f"PR Title: {pr_title}\nDiff:\n{diff_text}\nCI Results:\n{json.dumps(ci_results)}"
    cq_analysis = await call_agent(
        "You are a Code Quality Agent. Evaluate the code diff for style, security, and read the CI results.",
        cq_prompt
    )
    
    # 3. Decision Agent (Final JSON output)
    decision_prompt = f"""
    PR Title: {pr_title}
    
    Duplicate PR Warnings (if any):
    {duplicate_warnings}
    
    Architecture Agent Analysis:
    {arch_analysis}
    
    Code Quality Agent Analysis:
    {cq_analysis}
    
    Based on the above analyses and warnings, decide if this PR should be Accepted or Rejected.
    Respond in strict JSON format with keys: 
    "status" (either "Accepted" or "Rejected"),
    "reasoning" (a summary explanation),
    "architecture_review" (the architecture agent's output),
    "quality_review" (the code quality agent's output).
    """
    
    try:
        response = litellm.completion(
            model="gemini/gemini-1.5-flash", 
            messages=[
                {'role': 'user', 'content': decision_prompt},
            ], 
            response_format={"type": "json_object"}
        )
        
        result_json = json.loads(response.choices[0].message.content)
        
        # Ensure we capture all fields
        return {
            "status": result_json.get("status", "Rejected"),
            "reasoning": result_json.get("reasoning", "Failed to parse reasoning."),
            "architecture_review": result_json.get("architecture_review", arch_analysis),
            "quality_review": result_json.get("quality_review", cq_analysis),
        }
    except Exception as e:
        logger.error(f"Decision agent failed: {e}")
        return {
            "status": "Rejected", 
            "reasoning": f"Decision agent failed: {e}",
            "architecture_review": arch_analysis,
            "quality_review": cq_analysis
        }
