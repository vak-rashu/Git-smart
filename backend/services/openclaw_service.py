import logging
import json
import os
from openclaw_sdk import OpenClawClient, Agent

logger = logging.getLogger(__name__)

async def analyze_pr(pr_diff: dict, ci_results: dict, cognee_context: dict, pr_title: str = ""):
    logger.info("OpenClaw: Orchestrating multi-agent workflow via SDK...")
    
    diff_text = pr_diff.get('diff', 'No diff')
    architecture_context = cognee_context.get('context', 'No context')
    duplicate_warnings = cognee_context.get('duplicate_warnings', '')

    try:
        # Initialize client (will default to OPENCLAW_BASE_URL and OPENCLAW_API_KEY env vars)
        client = await OpenClawClient.connect()

        # 1. Architecture Agent
        arch_prompt = f"PR Title: {pr_title}\nDiff:\n{diff_text}\nRepository Architecture Context (from Cognee memory):\n{architecture_context}"
        arch_agent = Agent(client=client, agent_id="arch-reviewer")
        arch_result = await arch_agent.execute(
            f"You are an Architecture Review Agent. Evaluate if the PR diff aligns with the repository's established architecture.\n\n{arch_prompt}"
        )
        arch_analysis = str(arch_result)

        # 2. Code Quality Agent
        cq_prompt = f"PR Title: {pr_title}\nDiff:\n{diff_text}\nCI Results:\n{json.dumps(ci_results)}"
        cq_agent = Agent(client=client, agent_id="cq-reviewer")
        cq_result = await cq_agent.execute(
            f"You are a Code Quality Agent. Evaluate the code diff for style, security, and read the CI results.\n\n{cq_prompt}"
        )
        cq_analysis = str(cq_result)

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
        
        decision_agent = Agent(client=client, agent_id="decision-maker")
        decision_result = await decision_agent.execute(decision_prompt)
        
        try:
            result_json = json.loads(str(decision_result))
        except json.JSONDecodeError:
            result_json = {
                "status": "Rejected",
                "reasoning": str(decision_result),
                "architecture_review": arch_analysis,
                "quality_review": cq_analysis
            }
            
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
            "architecture_review": "Failed due to gateway error",
            "quality_review": "Failed due to gateway error"
        }
