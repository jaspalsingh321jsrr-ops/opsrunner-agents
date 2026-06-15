"""
Manager Agent — runs after every agent
ZERO Claude API calls — pure rule-based logic
Fast auto-approve or flag for human review
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.base import load_tasks, update_task, now

# Rules: auto-approve if output passes these checks
# No API calls — instant, free
QUALITY_RULES = {
    "min_length": 200,        # output must be at least 200 chars
    "required_sections": [],  # override per task type
    "blocked_phrases": [      # if these appear, flag for human review
        "ERROR:", "I cannot", "I'm unable", "I don't have access",
        "I apologize", "As an AI", "I don't know"
    ]
}

TASK_RULES = {
    "lead_generation": {"min_length": 400, "required": ["LEAD", "EMAIL", "SUBJECT"]},
    "content_creation": {"min_length": 300, "required": ["LINKEDIN", "TWITTER"]},
    "financial_report": {"min_length": 300, "required": ["REVENUE", "MRR"]},
    "client_emails":    {"min_length": 300, "required": ["EMAIL", "SUBJECT", "CTA"]},
    "product_roadmap":  {"min_length": 300, "required": ["SPRINT", "PRIORITY"]},
}

def check_quality(task: dict) -> tuple[bool, str]:
    output = task.get("output", "")
    task_type = task.get("task_type", "")
    rules = TASK_RULES.get(task_type, {})

    # Check for error phrases
    for phrase in QUALITY_RULES["blocked_phrases"]:
        if phrase in output:
            return False, f"Output contains error phrase: '{phrase}'"

    # Check minimum length
    min_len = rules.get("min_length", QUALITY_RULES["min_length"])
    if len(output) < min_len:
        return False, f"Output too short: {len(output)} chars (min {min_len})"

    # Check required sections
    required = rules.get("required", [])
    missing = [r for r in required if r.upper() not in output.upper()]
    if missing:
        return False, f"Missing required sections: {', '.join(missing)}"

    return True, "All quality checks passed"

def run_manager_review():
    """Review all pending tasks — no API calls, instant."""
    tasks = load_tasks()
    reviewed = 0

    for task in tasks:
        if task["status"] != "pending_review":
            continue

        passed, reason = check_quality(task)

        if passed:
            # Auto-approve — goes straight to CEO level
            update_task(task["id"], {
                "status": "approved",
                "approved_by": task.get("manager", "Manager"),
                "revision_note": f"Auto-approved: {reason}",
            })
            print(f"[MANAGER] ✓ Auto-approved {task['id']} ({task['agent']})")
        else:
            # Flag for human (Jaspal) to review
            update_task(task["id"], {
                "status": "needs_review",
                "revision_note": f"Quality check failed: {reason}",
            })
            print(f"[MANAGER] ⚠ Flagged {task['id']}: {reason}")
        reviewed += 1

    # CEO auto-approves all manager-approved tasks
    tasks = load_tasks()
    for task in tasks:
        if task["status"] == "approved" and task.get("approved_by") != "CEO":
            update_task(task["id"], {
                "status": "completed",
                "approved_by": "CEO (auto)",
            })
            print(f"[CEO] ✓ Completed {task['id']}")

    print(f"[MANAGER] Reviewed {reviewed} tasks")

if __name__ == "__main__":
    run_manager_review()
