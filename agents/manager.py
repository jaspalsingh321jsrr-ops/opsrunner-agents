"""
Manager Agent — runs after EVERY agent automatically
Zero Claude API calls — instant rule-based review
VP Revenue reviews: Sales, Marketing, Client Success
VP Operations reviews: Finance, Tech, Lead Finder
CEO auto-approves everything VP approved
Tasks move from pending_review → approved → completed automatically
"""
import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import load_tasks, update_task

MANAGER_MAP = {
    "VP Revenue":    ["Sales agent", "Marketing agent", "Client success agent", "LinkedIn Poster"],
    "VP Operations": ["Finance agent", "Tech agent", "Lead Finder", "Email Sender"],
}

QUALITY_RULES = {
    "lead_generation":  {"min": 400, "required": ["LEAD", "EMAIL", "SUBJECT"]},
    "content_creation": {"min": 300, "required": ["LINKEDIN", "TWITTER"]},
    "linkedin_post":    {"min": 200, "required": ["POST"]},
    "financial_report": {"min": 300, "required": ["REVENUE", "MRR"]},
    "client_emails":    {"min": 200, "required": ["EMAIL", "SUBJECT"]},
    "product_roadmap":  {"min": 200, "required": ["SPRINT", "PRIORITY"]},
}

BAD_PHRASES = ["ERROR:", "I cannot", "I'm unable", "As an AI", "I apologize", "I don't have access"]

def check_quality(task):
    output = task.get("output", "")
    ttype  = task.get("task_type", "")
    rules  = QUALITY_RULES.get(ttype, {"min": 150, "required": []})

    for phrase in BAD_PHRASES:
        if phrase in output:
            return False, f"Contains error phrase: '{phrase}'"

    if len(output) < rules["min"]:
        return False, f"Too short: {len(output)} chars (min {rules['min']})"

    missing = [r for r in rules.get("required", []) if r.upper() not in output.upper()]
    if missing:
        return False, f"Missing sections: {', '.join(missing)}"

    return True, "Quality checks passed"

def run():
    tasks    = load_tasks()
    reviewed = 0
    approved = 0
    flagged  = 0

    # Step 1: Manager reviews pending_review tasks
    for task in tasks:
        if task["status"] != "pending_review":
            continue

        passed, reason = check_quality(task)

        # Find manager
        manager = task.get("manager", "VP Revenue")

        if passed:
            update_task(task["id"], {
                "status":      "approved",
                "approved_by": manager,
                "revision_note": f"✓ {manager} approved: {reason}",
            })
            approved += 1
        else:
            # Auto-fix: if only issue is length, still approve
            if "Too short" in reason and len(task.get("output","")) > 100:
                update_task(task["id"], {
                    "status":      "approved",
                    "approved_by": manager,
                    "revision_note": f"✓ {manager} approved (minor: {reason})",
                })
                approved += 1
            else:
                update_task(task["id"], {
                    "status":      "needs_revision",
                    "revision_note": f"⚠ {manager} flagged: {reason}",
                })
                flagged += 1
        reviewed += 1

    # Step 2: CEO auto-approves all manager-approved tasks
    tasks = load_tasks()
    completed = 0
    for task in tasks:
        if task["status"] == "approved" and task.get("approved_by") != "CEO (auto)":
            update_task(task["id"], {
                "status":      "completed",
                "approved_by": "CEO (auto)",
                "revision_note": task.get("revision_note","") + " → CEO approved",
            })
            completed += 1

    print(f"[MANAGER] Reviewed: {reviewed} | Approved: {approved} | Flagged: {flagged} | CEO completed: {completed}")

if __name__ == "__main__":
    run()
