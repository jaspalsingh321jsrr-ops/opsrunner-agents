import anthropic, json, uuid, datetime, os, sys

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL   = "claude-haiku-4-5-20251001"   # cheapest model — ~10x less than Sonnet
MAX_TOKENS = 1200

PRODUCTS = """
Scroll_land_find — Bank statement analyzer. No bank login needed. Upload PDF/Excel/CSV.
URL: https://scrollandfind.com | Free tier + Pro plan
Differentiator: Privacy-first. No credentials. Works US + India.
Competitors: Rocket Money (bank login required $7-14/mo), Copilot ($10.99/mo)

OPSRUNNER — AI team for accounting firms. 9 departments. 80% cost reduction.
Differentiator: AI does 90% of work. Multi-ERP (QBO, Xero, Sage).

FOUNDER: Jaspal Singh — QBO certified. jaspal@scrollandfind.com
TARGET: US accounting firms, CFOs, privacy-conscious users.
"""

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tasks.json")

def call_claude(system: str, prompt: str) -> str:
    """Call Claude API — use sparingly."""
    if not API_KEY:
        return "ERROR: ANTHROPIC_API_KEY not set in GitHub Secrets"
    try:
        client = anthropic.Anthropic(api_key=API_KEY)
        r = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return r.content[0].text
    except Exception as e:
        return f"ERROR: {e}"

def load_tasks() -> list:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH):
        return []
    try:
        with open(DB_PATH) as f:
            return json.load(f)
    except:
        return []

def save_task(task: dict):
    tasks = load_tasks()
    # update if exists, else prepend
    for i, t in enumerate(tasks):
        if t["id"] == task["id"]:
            tasks[i] = task
            break
    else:
        tasks.insert(0, task)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w") as f:
        json.dump(tasks[:500], f, indent=2, default=str)

def update_task(task_id: str, updates: dict):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t.update(updates)
            t["updated_at"] = now()
    with open(DB_PATH, "w") as f:
        json.dump(tasks, f, indent=2, default=str)

def new_task(agent, task_type, title, output, manager, status="pending_review") -> dict:
    return {
        "id": str(uuid.uuid4())[:8],
        "agent": agent,
        "manager": manager,
        "task_type": task_type,
        "title": title,
        "output": output,
        "status": status,
        "created_at": now(),
        "updated_at": now(),
        "revision_note": None,
        "approved_by": None,
    }

def now() -> str:
    return datetime.datetime.utcnow().isoformat()
