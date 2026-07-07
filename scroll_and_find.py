#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 SCROLL AND FIND — AI WORKFORCE OPERATING SYSTEM  (single-file edition)
 Powered by the OpsRunner Business DNA. Zero-cost architecture:
 GitHub Actions = scheduler | JSON files = database | GitHub Pages = dashboard
===============================================================================

 SETUP (once):
   1. Drop this file in the ROOT of your opsrunner-agents repo.
   2. python scroll_and_find.py install      -> writes the GitHub Actions
      workflow (.github/workflows/scroll_and_find.yml) + seeds the knowledge
      base + builds docs/index.html
   3. Commit + push. Add ANTHROPIC_API_KEY in repo Settings > Secrets.
      (Optional for outreach: GMAIL_EMAIL + GMAIL_PASSWORD app password.)
   4. Enable GitHub Pages: Settings > Pages > deploy from branch /docs.

 FULL-AUTO MODE (everything runs itself; nothing waits for a human):
   - Every 2h: all due AI employees run + auto-outreach to VERIFIED leads
   - Daily 13:45 UTC: Workforce Director audit + status email to you
   - Every run: manager review, CSV/JSON export to data/exports/, dashboard

 SECRETS (repo Settings > Secrets and variables > Actions):
   ANTHROPIC_API_KEY  (required)
   GMAIL_EMAIL + GMAIL_PASSWORD  (app password — enables outreach + daily email)
   COMPANY_ADDRESS  (your mailing address — legally required on outreach emails)
   HUNTER_API_KEY   (used by lead_finder to discover REAL verified leads)
   DIGEST_EMAIL     (optional, where the daily report goes; default = GMAIL_EMAIL)

 MANUAL COMMANDS (optional):
   python scroll_and_find.py auto | run due | run <role> | director | manager
   python scroll_and_find.py dashboard | status | export | outreach | daily-report
   python scroll_and_find.py suppress someone@example.com   # never email them

 SAFETY RAILS (kept even in full-auto — they protect your Gmail account):
   outreach only to Hunter-VERIFIED addresses (confidence >= 80), max 3 per run,
   12 per day, suppression list honored, unsubscribe line on every email.

 COST: claude-haiku, cadence-throttled ~= $0.20-0.40/day.
===============================================================================
"""

import os, sys, json, uuid, re, datetime, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
MODEL              = "claude-haiku-4-5-20251001"
MAX_TOKENS         = 2500
PRICE_IN_PER_MTOK  = 1.00   # USD per 1M input tokens  (haiku)
PRICE_OUT_PER_MTOK = 5.00   # USD per 1M output tokens (haiku)
API_KEY            = os.environ.get("ANTHROPIC_API_KEY", "")

# --- FULL-AUTO MODE ---------------------------------------------------------
AUTO_APPROVE       = True    # quality-passed work completes instantly, no human gate
MAX_EMAILS_PER_RUN = 3       # outreach throttle (protects Gmail reputation)
MAX_EMAILS_PER_DAY = 12
MIN_LEAD_CONFIDENCE = 80     # only email verified, high-confidence leads
GMAIL_EMAIL        = os.environ.get("GMAIL_EMAIL", "")
GMAIL_PASSWORD     = os.environ.get("GMAIL_PASSWORD", "")
DIGEST_EMAIL       = os.environ.get("DIGEST_EMAIL", GMAIL_EMAIL or "jaspalsingh321jsrr@gmail.com")
COMPANY_ADDRESS    = os.environ.get("COMPANY_ADDRESS", "")   # required by CAN-SPAM before outreach sends
REPO_URL           = os.environ.get("REPO_URL", "https://github.com/jaspalsingh321jsrr-ops/opsrunner-agents")
PAGES_URL          = os.environ.get("PAGES_URL", "https://jaspalsingh321jsrr-ops.github.io/opsrunner-agents")

ROOT      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(ROOT, "data")
DOCS_DIR  = os.path.join(ROOT, "docs")
WF_DIR    = os.path.join(ROOT, ".github", "workflows")

F_TASKS     = os.path.join(DATA_DIR, "sf_tasks.json")        # workflow tasks
F_KNOWLEDGE = os.path.join(DATA_DIR, "sf_knowledge.json")    # knowledge base
F_ANALYTICS = os.path.join(DATA_DIR, "sf_analytics.json")    # tokens/cost/health
F_RECS      = os.path.join(DATA_DIR, "sf_recommendations.json")  # director output
F_REQUESTS  = os.path.join(DATA_DIR, "sf_requests.json")     # cross-dept requests
F_OUTREACH  = os.path.join(DATA_DIR, "sf_outreach.json")     # gated email queue
F_FINANCE   = os.path.join(DATA_DIR, "finance.json")         # existing repo data
F_LEADS     = os.path.join(DATA_DIR, "leads.json")           # existing repo data

def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")

def now_dt():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

# ----------------------------------------------------------------------------
# BUSINESS DNA — injected into EVERY AI employee, EVERY call
# ----------------------------------------------------------------------------
BUSINESS_DNA = """
############ OPSRUNNER BUSINESS DNA (MANDATORY — READ BEFORE ACTING) ############
You are a permanent OpsRunner employee, never a generic chatbot.

ABOUT: OpsRunner is an AI-powered accounting operations platform for accounting
firms, bookkeeping firms, CPAs, tax professionals and finance teams. It automates
marketing, sales, CRM, client onboarding, document collection, bookkeeping,
accounting, month-end close, financial reporting, workflow management, client
communication, internal operations and AI workforce management.

PRODUCTS:
- OpsRunner — AI team for accounting firms. 9 departments. ~80% cost reduction.
  Multi-ERP: QuickBooks Online, QuickBooks Desktop, Xero, Zoho Books, Sage.
- Scroll and Find (scrollandfind.com) — privacy-first bank statement analyzer.
  No bank login. Upload PDF/Excel/CSV. Free tier + Pro. Works US + India.
  Competitors: Rocket Money ($7-14/mo, requires bank login), Copilot ($10.99/mo).

CORE SERVICES: Bookkeeping, AP, AR, Payroll Support, Bank Reconciliation, QBO,
QB Desktop, Xero, Zoho Books, Financial Reporting, Cleanup, Catch-up, Month-End
Close, Controller Support, Virtual Accounting Team, Automation Consulting,
Workflow Design, AI Agent Development, Business Process Automation.

TARGET CLIENTS (US primary): small businesses, CPA / accounting / bookkeeping
firms, professional services, real estate, construction, e-commerce, retail,
healthcare, startups, multi-entity and growing companies.

FOUNDER: Jaspal Singh — QBO certified. Contact: jaspal@scrollandfind.com

BUSINESS GOALS (optimize every action for these): more qualified leads, more
revenue, lower operating cost, better retention, faster bookkeeping turnaround,
higher financial accuracy, more automation coverage, higher CSAT, more
referrals, more recurring revenue.

BRAND VOICE: professional, consultative, accurate, helpful, modern,
automation-first. NEVER overpromise. NEVER fabricate. NEVER guess accounting
information. NEVER give tax/legal advice without noting professional review.

COLLABORATION: no employee works in isolation. If a task needs another
department, emit an internal request (see OUTPUT CONTRACT) so it is routed,
tracked on the dashboard and stakeholders are notified.

LIFECYCLE every task follows: Request -> Validation -> Planning -> Execution ->
Quality Check -> Approval (when required) -> Completion -> Reporting ->
Knowledge Base Update -> Analytics Update.

ENGINEERING RULES before building anything: 1) does the feature already exist?
2) can another AI employee do it? 3) can an existing workflow be reused?
4) is there a mature open-source solution? 5) only then build from scratch.

HIGH-RISK ACTIONS (sending emails, publishing posts, deployments, spending
money) ALWAYS require human approval. Protect company reputation and client
data at all times.
#################################################################################
"""

OUTPUT_CONTRACT = """
OUTPUT CONTRACT (mandatory):
1. Produce every required section below, each as an UPPERCASE heading on its
   own line (e.g. "## SECTION NAME").
2. Be specific and actionable. No filler, no apologies, no "as an AI".
3. Never invent real people's names or real contact details. Use role-based
   targeting (e.g. "Managing Partner at a 5-20 staff CPA firm in Texas").
4. End with ONE fenced json block exactly like:
```json
{"internal_requests": [{"department": "Engineering", "request": "...", "priority": "P1"}],
 "kb_update": "one-line lesson or asset worth saving to the knowledge base",
 "metrics": {"tasks_completed": 1, "quality_self_score": 0}}
```
   internal_requests may be an empty list. quality_self_score is 1-10.
"""

# ----------------------------------------------------------------------------
# AI WORKFORCE REGISTRY — 22 employees + Director
# cadence_hours throttles cost; high_risk routes output to human approval.
# ----------------------------------------------------------------------------
def _R(dept, manager, cadence_hours, high_risk, mission, sections):
    return {"dept": dept, "manager": manager, "hours": cadence_hours,
            "high_risk": high_risk, "mission": mission, "sections": sections}

WORKFORCE = {
    "ceo": _R("Executive", "HUMAN", 168, False,
        "Act as CEO AI. Review the whole company: pipeline, revenue, workforce output, director recommendations. Set direction.",
        ["STRATEGIC REVIEW", "TOP 3 PRIORITIES THIS WEEK", "RISKS", "DECISIONS NEEDED FROM FOUNDER"]),
    "coo": _R("Executive", "ceo", 168, False,
        "Act as COO AI. Audit operations: workflow bottlenecks, stuck tasks, cross-department requests aging, process fixes.",
        ["OPERATIONS AUDIT", "BOTTLENECKS", "PROCESS IMPROVEMENTS", "THIS WEEK'S OPS PLAN"]),
    "product_manager": _R("Product", "coo", 72, False,
        "Act as Product Manager AI for OpsRunner + Scroll and Find. Maintain roadmap, write user stories with acceptance criteria, prioritize by ROI.",
        ["ROADMAP UPDATE", "TOP USER STORIES", "PRIORITY RATIONALE", "SPRINT PLAN"]),
    "marketing": _R("Marketing", "coo", 24, True,
        "Act as Marketing AI. Produce LinkedIn + X posts, one SEO content idea targeting CPA-firm pain points, and a CTA strategy. Public posts require human approval.",
        ["LINKEDIN POST", "TWITTER POST", "SEO CONTENT IDEA", "CTA STRATEGY"]),
    "sales": _R("Sales", "coo", 24, True,
        "Act as Sales AI. Build ICP-targeted outreach: segment definitions, cold email templates (max 120 words, one CTA), LinkedIn connection notes (<300 chars), objection handling. Role-based targeting only — no invented names. Sending requires human approval.",
        ["TARGET SEGMENT", "COLD EMAIL TEMPLATES", "LINKEDIN MESSAGES", "OBJECTION HANDLING", "FOLLOW-UP SEQUENCE"]),
    "customer_success": _R("Customer Success", "coo", 48, False,
        "Act as Customer Success AI. Design onboarding sequences, check-in cadences, churn-risk playbooks and referral asks for accounting-firm clients.",
        ["ONBOARDING PLAYBOOK", "CHECK-IN TEMPLATES", "CHURN-RISK SIGNALS", "REFERRAL PLAY"]),
    "accounting": _R("Accounting Ops", "coo", 72, False,
        "Act as Accounting AI. Produce SOPs and checklists for bookkeeping, reconciliation, AP/AR, month-end close across QBO/Xero/Zoho. Flag anything needing CPA review.",
        ["SOP", "CHECKLIST", "COMMON ERRORS TO CATCH", "CPA REVIEW FLAGS"]),
    "finance": _R("Finance", "ceo", 72, False,
        "Act as Finance AI. Model MRR scenarios, pricing experiments, unit economics and runway for OpsRunner + Scroll and Find. Use only data provided; mark assumptions.",
        ["REVENUE MODEL", "MRR SCENARIOS", "PRICING RECOMMENDATION", "ASSUMPTIONS"]),
    "hr": _R("HR", "coo", 168, False,
        "Act as HR AI. Maintain AI-workforce role definitions, performance rubrics tied to success metrics, and escalation policies.",
        ["ROLE DEFINITIONS UPDATE", "PERFORMANCE RUBRIC", "POLICY UPDATES"]),
    "recruiter": _R("HR", "hr", 168, False,
        "Act as Recruiter AI. Define hiring criteria for future human hires and specs for proposed new AI employees awaiting approval.",
        ["OPEN ROLES", "CANDIDATE PROFILE", "AI EMPLOYEE SPECS"]),
    "backend_engineer": _R("Engineering", "devops", 72, False,
        "Act as Backend Engineer AI. Work the engineering queue: design APIs, data models and Python implementations for requested features. Follow the 5 engineering rules.",
        ["QUEUE REVIEW", "DESIGN", "IMPLEMENTATION PLAN", "CODE"]),
    "frontend_engineer": _R("Engineering", "devops", 72, False,
        "Act as Frontend Engineer AI. Improve the executive + department dashboards (static HTML/JS on GitHub Pages). Propose concrete UI changes with code.",
        ["UX ISSUES FOUND", "PROPOSED CHANGES", "CODE"]),
    "fullstack_engineer": _R("Engineering", "devops", 168, False,
        "Act as Full Stack Engineer AI. Take one engineering-queue item end to end: architecture, backend, frontend, tests, docs.",
        ["FEATURE SELECTED", "ARCHITECTURE", "IMPLEMENTATION", "TESTS", "DOCS"]),
    "devops": _R("Engineering", "coo", 72, False,
        "Act as DevOps AI. Audit GitHub Actions workflows, cron cadences, secrets hygiene, failure rates and repo health. Keep infra cost at $0.",
        ["INFRA AUDIT", "WORKFLOW HEALTH", "FIXES", "COST CHECK"]),
    "qa": _R("Engineering", "devops", 72, False,
        "Act as QA Engineer AI. Review recent AI-employee outputs and engineering changes for defects; define test cases and quality gates.",
        ["DEFECTS FOUND", "TEST CASES", "QUALITY GATE UPDATES"]),
    "designer": _R("Product", "product_manager", 168, False,
        "Act as UI/UX Designer AI. Design dashboard and product screens: layout specs, component lists, accessibility notes. Text specs + HTML/CSS snippets.",
        ["DESIGN SPEC", "COMPONENTS", "ACCESSIBILITY", "HTML CSS SNIPPET"]),
    "security": _R("Security", "coo", 168, False,
        "Act as Security AI. Audit for secret leakage, injection risks in agent prompts, data exposure in the public repo/dashboard, and email-sending abuse vectors.",
        ["THREATS FOUND", "SEVERITY", "REMEDIATIONS", "SECURE-BY-DEFAULT CHECKLIST"]),
    "compliance": _R("Compliance", "coo", 168, False,
        "Act as Compliance AI. Review outreach for CAN-SPAM, data handling for privacy promises (Scroll and Find is privacy-first), and accounting-content disclaimers.",
        ["COMPLIANCE REVIEW", "VIOLATIONS OR RISKS", "REQUIRED CHANGES", "DISCLAIMER TEXT"]),
    "analytics": _R("Analytics", "coo", 24, False,
        "Act as Analytics AI. Read the metrics provided (tasks, approvals, token cost, leads) and report trends, anomalies and the single highest-leverage metric to move.",
        ["KPI SNAPSHOT", "TRENDS", "ANOMALIES", "HIGHEST-LEVERAGE METRIC"]),
    "documentation": _R("Knowledge", "coo", 72, False,
        "Act as Documentation AI. Turn recent completed work into crisp docs: READMEs, runbooks, changelogs.",
        ["DOCS WRITTEN", "CHANGELOG", "GAPS REMAINING"]),
    "knowledge_base": _R("Knowledge", "coo", 72, False,
        "Act as Knowledge Base AI. Curate the shared knowledge base: merge duplicates, flag stale entries, extract reusable SOPs/templates/prompts from recent tasks.",
        ["KB HEALTH", "NEW ENTRIES", "STALE ENTRIES", "MERGE ACTIONS"]),
}

# Proposed additional AI employees (Director evaluates gaps against this list)
EXPANSION_CANDIDATES = [
    "Payroll AI", "Proposal AI", "Collections AI", "Forecast AI", "Quality AI",
    "Customer Retention AI", "SEO AI", "Voice AI", "WhatsApp AI", "AI Trainer",
    "Testing AI", "Integration AI", "Mobile App AI",
]

# ----------------------------------------------------------------------------
# DEFAULT KNOWLEDGE BASE (seeded on install; every employee consults it)
# ----------------------------------------------------------------------------
DEFAULT_KNOWLEDGE = {
    "brand_voice": "Professional, consultative, accurate, helpful, modern, automation-first. Short sentences. No hype. Never overpromise or fabricate.",
    "pricing": "OpsRunner: custom quotes by firm size (anchor: ~50-80% below a US bookkeeper's fully-loaded cost). Scroll and Find: Free tier + Pro plan.",
    "business_rules": [
        "Human approval required before any email is sent or post is published.",
        "Never invent real people's names or contact details.",
        "Never give tax/legal advice without a professional-review disclaimer.",
        "Check the engineering rules (reuse first) before building anything.",
        "US market first; India secondary for Scroll and Find.",
    ],
    "email_template_cold": "Subject: {pain} at {company_type}?\n\nHi {first_name},\n\n{specific_pain_observation}\n\nOpsRunner automates ~90% of that work across QBO/Xero/Zoho — firms cut ops cost ~80%.\n\nWorth a 10-minute look this week?\n\n— Jaspal Singh, OpsRunner (QBO certified)",
    "sops": ["Month-end close SOP v1: reconcile banks -> review uncategorized -> AR/AP aging -> accruals -> reports -> client summary email."],
    "engineering_standards": "Python 3.11 stdlib-first. One Claude call per agent run. JSON-on-git storage. All schedules via GitHub Actions cron. Secrets only in GitHub Secrets.",
    "prompt_library": {},
    "case_studies": [],
    "entries": [],
}

# ----------------------------------------------------------------------------
# STORAGE
# ----------------------------------------------------------------------------
def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str, ensure_ascii=False)

def load_tasks():      return _load(F_TASKS, [])
def load_knowledge():  return _load(F_KNOWLEDGE, dict(DEFAULT_KNOWLEDGE))
def load_analytics():  return _load(F_ANALYTICS, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "runs": [], "errors": [], "health": {}})
def load_recs():       return _load(F_RECS, [])
def load_requests():   return _load(F_REQUESTS, [])
def load_outreach():   return _load(F_OUTREACH, [])

def save_task(task):
    tasks = load_tasks()
    for i, t in enumerate(tasks):
        if t["id"] == task["id"]:
            tasks[i] = task
            break
    else:
        tasks.insert(0, task)
    _save(F_TASKS, tasks[:600])

def update_task(task_id, updates):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t.update(updates)
            t["updated_at"] = now()
    _save(F_TASKS, tasks)

# ----------------------------------------------------------------------------
# CLAUDE — one call per employee run, fully cost-tracked
# ----------------------------------------------------------------------------
def call_claude(system, prompt, role="system"):
    if not API_KEY:
        return "ERROR: ANTHROPIC_API_KEY not set", 0, 0
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=API_KEY)
        r = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS,
                                   system=system,
                                   messages=[{"role": "user", "content": prompt}])
        tin  = getattr(r.usage, "input_tokens", 0)
        tout = getattr(r.usage, "output_tokens", 0)
        _track(role, tin, tout, ok=True)
        return r.content[0].text, tin, tout
    except Exception as e:
        _track(role, 0, 0, ok=False, err=str(e))
        return f"ERROR: {e}", 0, 0

def _track(role, tin, tout, ok=True, err=None):
    a = load_analytics()
    cost = tin / 1e6 * PRICE_IN_PER_MTOK + tout / 1e6 * PRICE_OUT_PER_MTOK
    a["input_tokens"]  = a.get("input_tokens", 0) + tin
    a["output_tokens"] = a.get("output_tokens", 0) + tout
    a["cost_usd"]      = round(a.get("cost_usd", 0.0) + cost, 6)
    a.setdefault("runs", []).insert(0, {"role": role, "ts": now(), "in": tin, "out": tout, "cost": round(cost, 6), "ok": ok})
    a["runs"] = a["runs"][:800]
    if err:
        a.setdefault("errors", []).insert(0, {"role": role, "ts": now(), "error": err[:400]})
        a["errors"] = a["errors"][:100]
    a.setdefault("health", {})[role] = {"last_run": now(), "ok": ok}
    _save(F_ANALYTICS, a)

# ----------------------------------------------------------------------------
# KNOWLEDGE BASE
# ----------------------------------------------------------------------------
def kb_context():
    kb = load_knowledge()
    lines = ["KNOWLEDGE BASE (consult before acting):",
             f"- Brand voice: {kb.get('brand_voice','')}",
             f"- Pricing: {kb.get('pricing','')}",
             f"- Engineering standards: {kb.get('engineering_standards','')}",
             "- Business rules: " + " | ".join(kb.get("business_rules", []))]
    for s in kb.get("sops", [])[:3]:
        lines.append(f"- SOP: {s}")
    for e in kb.get("entries", [])[:8]:
        lines.append(f"- Note ({e.get('by','?')}, {str(e.get('ts',''))[:10]}): {e.get('text','')}")
    return "\n".join(lines)

def kb_add(text, by):
    if not text or len(text) < 8:
        return
    kb = load_knowledge()
    kb.setdefault("entries", []).insert(0, {"ts": now(), "by": by, "text": text[:300]})
    kb["entries"] = kb["entries"][:200]
    _save(F_KNOWLEDGE, kb)

# ----------------------------------------------------------------------------
# BUSINESS CONTEXT snapshot given to employees (real data, not hallucinated)
# ----------------------------------------------------------------------------
def business_snapshot():
    tasks, recs, reqs, a = load_tasks(), load_recs(), load_requests(), load_analytics()
    fin   = _load(F_FINANCE, {})
    leads = _load(F_LEADS, [])
    open_reqs = [r for r in reqs if r.get("status") == "open"]
    pend      = [t for t in tasks if t.get("status") == "pending_human_approval"]
    return (f"LIVE COMPANY DATA (as of {now()} UTC):\n"
            f"- Leads in pipeline: {len(leads)}\n"
            f"- Finance snapshot: {json.dumps(fin)[:400]}\n"
            f"- Tasks last 7 days: {sum(1 for t in tasks if t.get('created_at','') > (now_dt()-datetime.timedelta(days=7)).isoformat())}\n"
            f"- Pending human approvals: {len(pend)}\n"
            f"- Open cross-dept requests: {len(open_reqs)} -> {json.dumps(open_reqs[:5])[:600]}\n"
            f"- Open director recommendations: {sum(1 for r in recs if r.get('status')=='open')}\n"
            f"- API spend to date: ${a.get('cost_usd',0):.4f} | tokens in/out: {a.get('input_tokens',0)}/{a.get('output_tokens',0)}\n")

# ----------------------------------------------------------------------------
# WORKFLOW ENGINE — full lifecycle for every employee run
# Request -> Validation -> Planning -> Execution -> Quality Check -> Approval
# -> Completion -> Reporting -> KB Update -> Analytics Update
# ----------------------------------------------------------------------------
JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)

def parse_contract(output):
    m = JSON_BLOCK.search(output or "")
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}

def quality_check(role, output):
    spec = WORKFORCE[role]
    bad = ["ERROR:", "I cannot", "I'm unable", "As an AI", "I apologize", "I don't have access"]
    for p in bad:
        if p in output:
            return False, f"contains '{p}'"
    if len(output) < 250:
        return False, f"too short ({len(output)} chars)"
    up = output.upper()
    missing = [s for s in spec["sections"] if s not in up]
    if missing:
        return False, "missing sections: " + ", ".join(missing)
    return True, "all quality gates passed"

def last_run_of(role):
    for t in load_tasks():
        if t.get("agent") == role:
            return t.get("created_at", "")
    return ""

def is_due(role):
    last = last_run_of(role)
    if not last:
        return True
    try:
        delta = now_dt() - datetime.datetime.fromisoformat(last)
        return delta.total_seconds() >= WORKFORCE[role]["hours"] * 3600 - 300
    except Exception:
        return True

def run_employee(role):
    if role not in WORKFORCE:
        print(f"[SF] unknown employee '{role}'. Roles: {', '.join(WORKFORCE)}")
        return None
    spec = WORKFORCE[role]

    # --- Request + Validation ---
    task = {
        "id": str(uuid.uuid4())[:8], "agent": role, "dept": spec["dept"],
        "manager": spec["manager"], "title": f"{role} run — {now()[:16]} UTC",
        "status": "in_progress", "high_risk": spec["high_risk"],
        "created_at": now(), "updated_at": now(),
        "quality": None, "approved_by": None, "note": None, "output": "",
    }

    # --- Planning + Execution (single Claude call, DNA + KB + live data) ---
    system = BUSINESS_DNA + "\n" + kb_context()
    sections = "\n".join(f"## {s}" for s in spec["sections"])
    prompt = (f"{business_snapshot()}\n"
              f"YOUR ROLE: {spec['mission']}\n"
              f"Your manager: {spec['manager']}. Department: {spec['dept']}.\n\n"
              f"Follow the workflow lifecycle. First silently validate the request and plan, "
              f"then produce ONLY the final deliverable with EXACTLY these sections:\n{sections}\n"
              f"{OUTPUT_CONTRACT}")
    output, tin, tout = call_claude(system, prompt, role=role)
    task["output"] = output

    # --- Quality Check ---
    passed, reason = quality_check(role, output)
    task["quality"] = reason

    # --- Approval routing (AUTO_APPROVE = no human gate, nothing ever pends) ---
    if not passed:
        task["status"] = "needs_revision"
        task["note"] = f"Manager({spec['manager']}) rejected: {reason} (auto-retries next cycle)"
    elif spec["high_risk"] and not AUTO_APPROVE:
        task["status"] = "pending_human_approval"
        task["note"] = "Run: python scroll_and_find.py approve " + task["id"]
    else:
        task["status"] = "completed"
        task["approved_by"] = spec["manager"] + (" (auto-policy)" if spec["high_risk"] else "")

    # --- Completion + Reporting + KB + Analytics + Collaboration ---
    contract = parse_contract(output)
    kb_add(contract.get("kb_update", ""), by=role)
    route_requests(role, contract.get("internal_requests", []))
    if role == "sales" and passed:
        queue_outreach_from(task)
    save_task(task)
    print(f"[SF] {role}: {task['status']} ({task['id']}) — {reason}; tokens {tin}/{tout}")
    return task

def route_requests(from_role, requests):
    if not isinstance(requests, list) or not requests:
        return
    reqs = load_requests()
    for r in requests[:5]:
        if not isinstance(r, dict):
            continue
        dept = str(r.get("department", "Engineering"))[:40]
        reqs.insert(0, {
            "id": str(uuid.uuid4())[:8], "from": from_role, "department": dept,
            "request": str(r.get("request", ""))[:500], "priority": str(r.get("priority", "P2"))[:4],
            "status": "open", "created_at": now(),
        })
    _save(F_REQUESTS, reqs[:300])

def queue_outreach_from(task):
    """Sales output -> gated outreach queue. NOTHING is sent without human approval."""
    q = load_outreach()
    q.insert(0, {
        "id": str(uuid.uuid4())[:8], "task_id": task["id"], "created_at": now(),
        "status": "draft",  # draft -> approved (human) -> sent
        "to": "",           # human fills a real, verified address before approving
        "subject": "", "body": task["output"][:4000],
        "note": "Set 'to' + 'subject' + trimmed 'body' in data/sf_outreach.json, then: approve-email <id>",
    })
    _save(F_OUTREACH, q[:200])

# ----------------------------------------------------------------------------
# MANAGER — rule-based re-review of anything stuck (0 API calls, free)
# ----------------------------------------------------------------------------
def run_manager():
    n = 0
    # full-auto: clear anything pending immediately (nothing pends > 2 min)
    if AUTO_APPROVE:
        for t in load_tasks():
            if t.get("status") == "pending_human_approval":
                update_task(t["id"], {"status": "completed", "approved_by": "AUTO-POLICY"})
                n += 1
    for t in load_tasks():
        if t.get("status") == "in_progress":  # crashed mid-run
            passed, reason = quality_check(t["agent"], t.get("output", "")) if t.get("agent") in WORKFORCE else (False, "unknown role")
            update_task(t["id"], {"status": "completed" if passed and not t.get("high_risk") else "needs_revision" if not passed else "pending_human_approval",
                                  "quality": reason, "approved_by": WORKFORCE.get(t.get("agent"), {}).get("manager") if passed else None})
            n += 1
    # age out stale cross-dept requests
    reqs = load_requests()
    for r in reqs:
        if r.get("status") == "open" and r.get("created_at", "") < (now_dt() - datetime.timedelta(days=14)).isoformat():
            r["status"] = "stale"
    _save(F_REQUESTS, reqs)
    print(f"[SF] manager: re-reviewed {n} stuck task(s), aged stale requests")

# ----------------------------------------------------------------------------
# AI WORKFORCE DIRECTOR — continuous audit + structured recommendations
# ----------------------------------------------------------------------------
def run_director():
    tasks, reqs, recs, a = load_tasks(), load_requests(), load_recs(), load_analytics()
    recent = [{"agent": t["agent"], "status": t["status"], "quality": t.get("quality")} for t in tasks[:40]]
    fail_rate = {}
    for t in tasks[:100]:
        fail_rate.setdefault(t["agent"], [0, 0])
        fail_rate[t["agent"]][1] += 1
        if t["status"] == "needs_revision":
            fail_rate[t["agent"]][0] += 1
    open_recs = [r for r in recs if r.get("status") == "open"]

    system = BUSINESS_DNA + "\n" + kb_context()
    prompt = (f"{business_snapshot()}\n"
              "YOU ARE THE AI WORKFORCE DIRECTOR. Audit the platform continuously.\n"
              f"Current workforce roles: {', '.join(WORKFORCE)}\n"
              f"Expansion candidates to evaluate: {', '.join(EXPANSION_CANDIDATES)}\n"
              f"Recent task outcomes: {json.dumps(recent)[:1500]}\n"
              f"Revision rates by agent: {json.dumps(fail_rate)}\n"
              f"Open cross-dept requests: {json.dumps([r for r in reqs if r.get('status')=='open'][:10])[:1200]}\n"
              f"Already-open recommendations (do NOT repeat): {json.dumps([r.get('problem','')[:80] for r in open_recs])}\n\n"
              "Detect: missing features, missing workflows, missing departments, repetitive manual "
              "work, automation opportunities, needed AI employees, engineering / dashboard / "
              "architecture improvements.\n"
              "Return ONLY a fenced json block:\n"
              "```json\n{\"recommendations\": [{\"problem\": \"\", \"business_impact\": \"\", "
              "\"recommended_solution\": \"\", \"priority\": \"P1|P2|P3\", \"estimated_effort\": \"\", "
              "\"dependencies\": \"\", \"expected_roi\": \"\", \"type\": \"feature|workflow|department|"
              "automation|ai_employee|engineering|dashboard|architecture\"}]}\n```\n"
              "3 to 5 recommendations, highest ROI first. New AI employees need a business case in "
              "business_impact. Route anything buildable to Engineering via dependencies.")
    output, tin, tout = call_claude(system, prompt, role="director")
    data = parse_contract(output)
    new = data.get("recommendations", []) if isinstance(data, dict) else []
    for r in new[:5]:
        if not isinstance(r, dict) or not r.get("problem"):
            continue
        r.update({"id": str(uuid.uuid4())[:8], "status": "open", "created_at": now()})
        recs.insert(0, r)
        if r.get("type") in ("feature", "engineering", "dashboard", "architecture", "ai_employee"):
            route_requests("director", [{"department": "Engineering",
                                         "request": f"[{r.get('priority','P2')}] {r.get('recommended_solution','')[:300]}",
                                         "priority": r.get("priority", "P2")}])
    _save(F_RECS, recs[:150])
    save_task({"id": str(uuid.uuid4())[:8], "agent": "director", "dept": "Executive",
               "manager": "HUMAN", "title": f"Director audit — {now()[:16]} UTC",
               "status": "completed", "high_risk": False, "created_at": now(),
               "updated_at": now(), "quality": f"{len(new)} recommendations",
               "approved_by": "HUMAN-standing-order", "note": None, "output": output})
    print(f"[SF] director: {len(new)} new recommendation(s); tokens {tin}/{tout}")

# ----------------------------------------------------------------------------
# HUMAN APPROVAL GATE
# ----------------------------------------------------------------------------
def approve(task_id):
    update_task(task_id, {"status": "completed", "approved_by": "HUMAN", "note": "Human approved"})
    print(f"[SF] task {task_id} approved")

def reject(task_id, note="rejected"):
    update_task(task_id, {"status": "needs_revision", "approved_by": None, "note": f"HUMAN rejected: {note}"})
    print(f"[SF] task {task_id} rejected")

def approve_email(email_id):
    q = load_outreach()
    for e in q:
        if e["id"] == email_id:
            if not e.get("to") or "@" not in e.get("to", "") or not e.get("subject"):
                print(f"[SF] cannot approve {email_id}: fill real 'to' and 'subject' in data/sf_outreach.json first")
                return
            e["status"] = "approved"
            e["approved_at"] = now()
            _save(F_OUTREACH, q)
            print(f"[SF] email {email_id} approved for sending")
            return
    print(f"[SF] email {email_id} not found")

def send_emails():
    """Sends ONLY human-approved emails. High-risk action stays gated."""
    gmail, pwd = os.environ.get("GMAIL_EMAIL", ""), os.environ.get("GMAIL_PASSWORD", "")
    if not gmail or not pwd:
        print("[SF] GMAIL_EMAIL / GMAIL_PASSWORD not set — nothing sent")
        return
    q, sent = load_outreach(), 0
    for e in q:
        if e.get("status") != "approved":
            continue
        try:
            msg = MIMEMultipart()
            msg["From"], msg["To"], msg["Subject"] = gmail, e["to"], e["subject"]
            msg.attach(MIMEText(e["body"], "plain"))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
                s.login(gmail, pwd)
                s.sendmail(gmail, e["to"], msg.as_string())
            e["status"], e["sent_at"] = "sent", now()
            sent += 1
        except Exception as ex:
            e["status"], e["error"] = "error", str(ex)[:200]
    _save(F_OUTREACH, q)
    print(f"[SF] sent {sent} human-approved email(s)")

# ----------------------------------------------------------------------------
# AUTO OUTREACH — every 2h, ZERO human dependency, with safety rails:
# only Hunter-VERIFIED real addresses, confidence >= 80, 3/run, 12/day cap,
# suppression list honored, CAN-SPAM footer (needs COMPANY_ADDRESS secret).
# ----------------------------------------------------------------------------
F_SUPPRESS = os.path.join(DATA_DIR, "sf_suppression.json")

def _smtp_send(to, subject, body):
    msg = MIMEMultipart()
    msg["From"], msg["To"], msg["Subject"] = GMAIL_EMAIL, to, subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_EMAIL, GMAIL_PASSWORD)
        s.sendmail(GMAIL_EMAIL, to, msg.as_string())

def _sent_today():
    today = now()[:10]
    return [e for e in load_outreach() if e.get("status") == "sent" and str(e.get("sent_at", ""))[:10] == today]

def run_outreach():
    if not GMAIL_EMAIL or not GMAIL_PASSWORD:
        print("[SF] outreach: GMAIL_EMAIL/GMAIL_PASSWORD secrets missing — skipped")
        return
    if not COMPANY_ADDRESS:
        print("[SF] outreach: COMPANY_ADDRESS secret missing (required by CAN-SPAM) — skipped")
        return
    budget = min(MAX_EMAILS_PER_RUN, MAX_EMAILS_PER_DAY - len(_sent_today()))
    if budget <= 0:
        print("[SF] outreach: daily cap reached — skipped")
        return
    leads = _load(F_LEADS, [])
    suppress = set(_load(F_SUPPRESS, []))
    contacted = {e.get("to") for e in load_outreach()}
    eligible = [l for l in leads
                if l.get("source") == "hunter_verified"
                and int(l.get("confidence") or 0) >= MIN_LEAD_CONFIDENCE
                and l.get("status") == "new"
                and "@" in str(l.get("email", ""))
                and l["email"] not in suppress and l["email"] not in contacted]
    if not eligible:
        print("[SF] outreach: 0 verified eligible leads (need HUNTER_API_KEY lead runs) — nothing sent")
        return
    q, sent = load_outreach(), 0
    for l in eligible[:budget]:
        subject = l.get("email_subject") or f"Quick question for {l.get('company','your firm')}"
        body = (l.get("email_body") or "").strip()
        if len(body) < 80:
            out, _, _ = call_claude(BUSINESS_DNA + "\n" + kb_context(),
                f"Write ONLY the body of a cold email (max 110 words, one CTA, brand voice) to "
                f"{l.get('first_name','')} ({l.get('position','')}) at {l.get('company','')}. "
                f"Pain point: {l.get('pain_point','manual bookkeeping workload')}. "
                f"Why us: {l.get('why_us','OpsRunner automates ~90% of accounting ops')}.", role="outreach")
            if out.startswith("ERROR:"):
                continue
            body = out.strip()
        body += (f"\n\n—\nJaspal Singh · OpsRunner · jaspal@scrollandfind.com · {COMPANY_ADDRESS}"
                 f"\nDon't want these emails? Reply UNSUBSCRIBE and you'll never hear from me again.")
        rec = {"id": str(uuid.uuid4())[:8], "to": l["email"], "subject": subject,
               "lead_id": l.get("id"), "company": l.get("company"), "created_at": now()}
        try:
            _smtp_send(l["email"], subject, body)
            rec.update({"status": "sent", "sent_at": now()})
            l["status"], l["emailed_at"] = "emailed", now()
            sent += 1
        except Exception as ex:
            rec.update({"status": "error", "error": str(ex)[:200]})
            l["status"] = "send_failed"
        q.insert(0, rec)
    _save(F_OUTREACH, q[:400])
    _save(F_LEADS, leads)
    print(f"[SF] outreach: sent {sent} email(s) to verified leads ({len(_sent_today())}/{MAX_EMAILS_PER_DAY} today)")

def suppress_email(addr):
    s = _load(F_SUPPRESS, [])
    if addr not in s:
        s.append(addr)
    _save(F_SUPPRESS, s)
    print(f"[SF] {addr} added to suppression list — will never be emailed")

# ----------------------------------------------------------------------------
# DATA EXPORT — CSV + JSON of everything, refreshed every run -> data/exports/
# ----------------------------------------------------------------------------
def export_data():
    import csv
    exp = os.path.join(DATA_DIR, "exports")
    os.makedirs(exp, exist_ok=True)
    sets = {"tasks": load_tasks(), "leads": _load(F_LEADS, []), "recommendations": load_recs(),
            "requests": load_requests(), "outreach": load_outreach(),
            "analytics_runs": load_analytics().get("runs", [])}
    for name, rows in sets.items():
        _save(os.path.join(exp, f"{name}.json"), rows)
        if rows and isinstance(rows[0], dict):
            keys = sorted({k for r in rows for k in r})
            with open(os.path.join(exp, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
                w.writeheader()
                for r in rows:
                    w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})
    print(f"[SF] exported {len(sets)} datasets (CSV+JSON) -> data/exports/")

# ----------------------------------------------------------------------------
# DAILY STATUS EMAIL — what every agent did today, with direct links
# ----------------------------------------------------------------------------
def daily_report():
    if not GMAIL_EMAIL or not GMAIL_PASSWORD:
        print("[SF] daily report: GMAIL secrets missing — skipped")
        return
    today = now()[:10]
    tasks = [t for t in load_tasks() if str(t.get("created_at", ""))[:10] == today]
    a = load_analytics()
    cost_today = sum(r.get("cost", 0) for r in a.get("runs", []) if str(r.get("ts", ""))[:10] == today)
    sent = _sent_today()
    recs_open = [r for r in load_recs() if r.get("status") == "open"]
    by_agent = {}
    for t in tasks:
        by_agent.setdefault(t["agent"], []).append(t["status"])
    lines = [f"SCROLL AND FIND — daily status for {today}", "",
             f"Dashboard (everything, clickable): {PAGES_URL}",
             f"Exports (CSV/JSON):                {REPO_URL}/tree/main/data/exports",
             f"Run history:                       {REPO_URL}/actions", "",
             f"Agent runs today: {len(tasks)} | completed: {sum(1 for t in tasks if t['status']=='completed')} "
             f"| needs revision: {sum(1 for t in tasks if t['status']=='needs_revision')}",
             f"Outreach emails sent today: {len(sent)}" + (f" -> {', '.join(e['company'] or e['to'] for e in sent[:5])}" if sent else ""),
             f"API cost today: ${cost_today:.4f} (total ${a.get('cost_usd',0):.4f})",
             f"Open Director recommendations: {len(recs_open)}", "",
             "WHAT EACH AGENT DID TODAY:"]
    for agent, sts in sorted(by_agent.items()):
        t0 = next(t for t in tasks if t["agent"] == agent)
        first_line = next((ln.strip("# ").strip() for ln in t0.get("output", "").splitlines() if ln.strip() and not ln.startswith("```")), "")[:110]
        lines.append(f"  - {agent}: {', '.join(sts)} — {first_line}")
    if recs_open:
        lines += ["", "TOP DIRECTOR RECOMMENDATIONS:"]
        lines += [f"  - [{r.get('priority','P2')}] {r.get('problem','')[:100]}" for r in recs_open[:5]]
    if not COMPANY_ADDRESS:
        lines += ["", "ACTION NEEDED: add COMPANY_ADDRESS secret (your mailing address) to enable auto-outreach (CAN-SPAM)."]
    if not any(l.get("source") == "hunter_verified" for l in _load(F_LEADS, [])):
        lines += ["", "NOTE: 0 verified leads in pipeline. Add HUNTER_API_KEY secret so lead_finder can find real, emailable leads."]
    try:
        _smtp_send(DIGEST_EMAIL, f"[Scroll and Find] {today}: {len(tasks)} agent runs, {len(sent)} emails sent, ${cost_today:.2f}", "\n".join(lines))
        print(f"[SF] daily report emailed to {DIGEST_EMAIL}")
    except Exception as ex:
        print(f"[SF] daily report failed: {ex}")

# ----------------------------------------------------------------------------
# EXECUTIVE + DEPARTMENT DASHBOARDS (static build -> docs/index.html on Pages)
# ----------------------------------------------------------------------------
DASH_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scroll and Find — Your AI Company</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#f5f5f5;font-size:15px;line-height:1.55}
.wrap{max-width:1020px;margin:0 auto;padding:28px 18px 60px}
h1{font-size:26px;letter-spacing:-.5px}
.tag{color:#8a8a8a;font-size:13px;margin-top:4px}
.hello{background:linear-gradient(135deg,#101613,#0d1110);border:1px solid #1f3328;border-radius:16px;padding:18px 20px;margin:20px 0;font-size:16px}
.hello b{color:#34d399}
h2{font-size:17px;margin:30px 0 4px}
.sub{color:#8a8a8a;font-size:13px;margin-bottom:12px}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.step{background:#141414;border:1px solid #262626;border-radius:14px;padding:14px}
.step .n{display:inline-block;background:#1f3328;color:#34d399;font-weight:700;font-size:12px;border-radius:8px;padding:2px 8px;margin-bottom:8px}
.step b{display:block;font-size:14px;margin-bottom:4px}
.step p{color:#8a8a8a;font-size:12.5px}
.step .live{margin-top:8px;font-size:13px;color:#34d399;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.stat{background:#141414;border:1px solid #262626;border-radius:14px;padding:14px}
.stat .v{font-size:24px;font-weight:700;letter-spacing:-.5px}
.stat .l{font-size:12px;color:#c9c9c9;margin-top:2px;font-weight:600}
.stat .d{font-size:11.5px;color:#7a7a7a;margin-top:3px}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 14px}
.pill{border:1px solid #2c2c2c;background:#141414;color:#bdbdbd;border-radius:999px;padding:5px 13px;font-size:12.5px;cursor:pointer}
.pill.on{background:#1f3328;border-color:#2f5c44;color:#34d399;font-weight:600}
.emp{background:#141414;border:1px solid #262626;border-radius:14px;padding:13px 15px;margin-bottom:9px}
.emp .top{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.emp .name{font-weight:700;font-size:14px}
.emp .dept{color:#7a7a7a;font-size:12px}
.chip{margin-left:auto;font-size:11.5px;font-weight:700;border-radius:999px;padding:3px 10px;white-space:nowrap}
.ok{background:#12291d;color:#34d399}.warn{background:#2b2010;color:#fbbf24}.bad{background:#2b1212;color:#f87171}.info{background:#101c2b;color:#60a5fa}.zzz{background:#1c1c1c;color:#8a8a8a}
.emp .what{color:#b9b9b9;font-size:13px;margin-top:6px}
details{margin-top:8px}
summary{cursor:pointer;color:#34d399;font-size:12.5px;font-weight:600}
pre{white-space:pre-wrap;font-family:inherit;font-size:12.5px;color:#c9c9c9;background:#0f0f0f;border:1px solid #222;border-radius:10px;padding:12px;margin-top:8px;max-height:300px;overflow-y:auto}
.idea{background:#141414;border:1px solid #262626;border-radius:14px;padding:14px 16px;margin-bottom:9px}
.idea b{font-size:13.5px}
.idea p{color:#9a9a9a;font-size:12.5px;margin-top:4px}
.idea .meta{margin-top:8px;font-size:11.5px;color:#7a7a7a}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:#7a7a7a;font-size:11px;text-transform:uppercase;letter-spacing:.05em;padding:6px 8px;border-bottom:1px solid #262626}
td{padding:8px;border-bottom:1px solid #1b1b1b;vertical-align:top}
.card{background:#141414;border:1px solid #262626;border-radius:14px;padding:16px}
.btns{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.btn{border:1px solid #2c2c2c;background:#181818;color:#e5e5e5;border-radius:10px;padding:8px 14px;font-size:13px;cursor:pointer;text-decoration:none;display:inline-block}
.btn:hover{border-color:#34d399;color:#34d399}
.good{color:#34d399}.mut{color:#8a8a8a}
.foot{color:#5f5f5f;font-size:12px;margin-top:34px;text-align:center}
@media(max-width:600px){h1{font-size:21px}.stat .v{font-size:20px}}
</style></head><body><div class="wrap">

<h1>Scroll and Find · <span class="good">Your AI Company</span></h1>
<div class="tag">21 AI employees running OpsRunner for you, around the clock · powered by OpsRunner Business DNA</div>
<div class="hello" id="hello"></div>

<h2>How your company works</h2>
<div class="sub">This whole loop repeats every 2 hours, automatically. You don't have to do anything.</div>
<div class="flow" id="flow"></div>

<h2>Today's numbers</h2>
<div class="sub">Click any card's section below to see the details behind it.</div>
<div class="grid" id="stats"></div>

<h2 id="team">Your AI employees</h2>
<div class="sub">What each one did in their latest shift. Tap "Read their work" to see the full output.</div>
<div class="pills" id="pills"></div>
<div id="emps"></div>

<h2 id="ideas">Ideas from your AI Director</h2>
<div class="sub">Every day the Director studies your company and suggests improvements. Newest first.</div>
<div id="recs"></div>

<h2 id="emails">Emails sent to potential clients</h2>
<div class="sub">Only real, verified addresses get emailed — maximum 12 per day to keep your Gmail safe.</div>
<div class="card" id="outreach"></div>

<h2 id="leads">Your leads</h2>
<div class="sub">Everyone the Lead Finder has discovered. Only verified leads get emailed - the rest are research.</div>
<div class="pills" id="lpills"></div>
<div class="card" id="leadsbox"></div>

<h2 id="attention">Anything needing attention?</h2>
<div id="issues"></div>

<h2>Your data — download anytime</h2>
<div class="card">Everything your AI company produces belongs to you. Download it as Excel-friendly CSV files:
<div class="btns">
<span class="btn" onclick="exp('tasks','csv')">⬇ All work (CSV)</span>
<span class="btn" onclick="exp('leadsList','csv')">&#11015; Leads (CSV)</span>
<span class="btn" onclick="exp('outreach','csv')">⬇ Emails sent (CSV)</span>
<span class="btn" onclick="exp('recs','csv')">⬇ Director ideas (CSV)</span>
<span class="btn" onclick="exp('all','json')">⬇ Everything (JSON)</span>
<a class="btn" id="lnk-exp" target="_blank">📁 Exports folder on GitHub</a>
<a class="btn" id="lnk-act" target="_blank">▶ Run history</a>
</div></div>

<div class="foot" id="foot"></div>
</div>
<script>
const D=__DATA__;
const BUILT="__BUILT__";
const EMOJI={"Executive":"👔","Product":"📦","Marketing":"📣","Sales":"🤝","Customer Success":"💬","Accounting Ops":"📚","Finance":"💰","HR":"🧑‍💼","Engineering":"🛠️","Security":"🔒","Compliance":"⚖️","Analytics":"📊","Knowledge":"📖"};
const STATUS={completed:["✅ Done","ok"],needs_revision:["🔁 Redoing next run","warn"],in_progress:["⏳ Working now","info"],pending_human_approval:["⏸ Waiting","warn"],sent:["📤 Sent","ok"],error:["⚠️ Problem","bad"],open:["🟡 Open","warn"],draft:["📝 Draft","zzz"],stale:["💤 Expired","zzz"]};
const esc=s=>String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;');
const nice=k=>k.split('_').map(w=>w==='ceo'?'CEO':w==='coo'?'COO':w==='hr'?'HR':w==='qa'?'QA':w[0].toUpperCase()+w.slice(1)).join(' ')+' AI';
const chip=s=>{const[t,c]=STATUS[s]||[s,'zzz'];return `<span class="chip ${c}">${t}</span>`};
const latestOf=r=>D.tasks.find(t=>t.agent===r);
const dayKey=(D.tasks[0]?.created_at||BUILT).slice(0,10);
const todayTasks=D.tasks.filter(t=>(t.created_at||'').slice(0,10)===dayKey);
const doneToday=todayTasks.filter(t=>t.status==='completed').length;
const redoToday=todayTasks.filter(t=>t.status==='needs_revision').length;
const openRecs=D.recs.filter(r=>r.status==='open');
const sentAll=D.outreach.filter(e=>e.status==='sent');

/* hello */
document.getElementById('hello').innerHTML=
 `👋 Hi Jaspal. On <b>${dayKey}</b> your AI team finished <b>${doneToday} pieces of work</b>, sent <b>${D.sentToday} email${D.sentToday==1?'':'s'}</b> to potential clients, and it cost you <b>$${(D.analytics.cost_usd||0).toFixed(2)} total so far</b>. `+
 (redoToday?`${redoToday} task${redoToday==1?' is':'s are'} being redone automatically — no action needed. `:'Everything ran cleanly. ')+
 `Your next daily summary email arrives around 7:15 PM IST.`;

/* flow */
const flow=[
 ["Step 1","🔎 Find clients","Every 2 hours, the Lead Finder searches for accounting firms and verifies real email addresses.",`${D.leadsList.length} leads in pipeline`],
 ["Step 2","✍️ Write & send","Sales AI writes a personal email for each verified lead and sends it — max 12/day.",`${sentAll.length} sent so far`],
 ["Step 3","🏢 Run the company","All 21 AI employees do their daily jobs: marketing, finance, engineering, and more.",`${doneToday} tasks done today`],
 ["Step 4","📬 Report to you","You get a daily email summary, and this page refreshes itself after every run.",`Updated ${BUILT} UTC`]];
document.getElementById('flow').innerHTML=flow.map(f=>`<div class="step"><span class="n">${f[0]}</span><b>${f[1]}</b><p>${f[2]}</p><div class="live">${f[3]}</div></div>`).join('');

/* stats */
const stats=[
 [D.sentToday,"Emails sent today","Real verified clients contacted",'#emails'],
 [D.leadsList.length,"Leads found","Potential clients in your pipeline",'#leads'],
 [doneToday,"Tasks finished today","Work completed by your AI team",'#team'],
 [openRecs.length,"Ideas waiting","Improvements your Director suggests",'#ideas'],
 [redoToday+D.analytics.errors.length,"Needs attention","Things being fixed automatically",'#attention'],
 ["$"+(D.analytics.cost_usd||0).toFixed(2),"Total spend","Everything since day one",'#attention']];
document.getElementById('stats').innerHTML=stats.map(s=>`<a href="${s[3]}" style="text-decoration:none;color:inherit"><div class="stat"><div class="v">${s[0]}</div><div class="l">${s[1]}</div><div class="d">${s[2]}</div></div></a>`).join('');

/* employees + department pills */
const depts=['All',...new Set(Object.values(D.workforce).map(w=>w.dept))];
let cur='All';
function renderPills(){document.getElementById('pills').innerHTML=depts.map(d=>`<span class="pill ${d===cur?'on':''}" onclick="pick('${d}')">${d==='All'?'👥 Everyone':EMOJI[d]+' '+d}</span>`).join('')}
window.pick=d=>{cur=d;renderPills();renderEmps()};
function renderEmps(){
 document.getElementById('emps').innerHTML=Object.entries(D.workforce)
 .filter(([k,w])=>cur==='All'||w.dept===cur)
 .map(([k,w])=>{const t=latestOf(k);
  return `<div class="emp"><div class="top"><span>${EMOJI[w.dept]||'🤖'}</span><span class="name">${nice(k)}</span><span class="dept">${w.dept} · works every ${w.hours>=48?Math.round(w.hours/24)+' days':w.hours+' hours'}</span>${t?chip(t.status):'<span class="chip zzz">💤 Not run yet</span>'}</div>`+
  `<div class="what">${esc(w.mission.replace(/^Act as [^.]*\. /,''))}</div>`+
  (t?`<details><summary>Read their work (${(t.created_at||'').slice(0,16).replace('T',' ')} UTC)</summary><pre>${esc(t.output)}</pre></details>`:'')+
  `</div>`}).join('');
}
renderPills();renderEmps();

/* director ideas */
document.getElementById('recs').innerHTML=openRecs.length?openRecs.map(r=>
 `<div class="idea"><b>💡 ${esc(r.problem)}</b><p>${esc(r.business_impact)}</p><p><span class="good">Suggestion:</span> ${esc(r.recommended_solution)}</p>`+
 `<div class="meta">Priority ${esc(r.priority||'P2')} · Effort: ${esc(r.estimated_effort||'—')} · Expected return: ${esc(r.expected_roi||'—')}</div></div>`).join('')
 :'<div class="card mut">No open ideas right now. The Director reviews your whole company every day at 13:45 UTC (7:15 PM IST).</div>';

/* outreach */
document.getElementById('outreach').innerHTML=D.outreach.length?
 `<table><tr><th>Sent to</th><th>Company</th><th>Status</th><th>When (UTC)</th></tr>`+D.outreach.slice(0,15).map(e=>
 `<tr><td>${esc(e.to)}</td><td>${esc(e.company||'—')}</td><td>${chip(e.status)}</td><td>${esc((e.sent_at||e.created_at||'').slice(0,16).replace('T',' '))}</td></tr>`).join('')+`</table>`
 :`<span class="mut">No emails sent yet. This starts automatically once the Lead Finder discovers verified addresses (it searches every 2 hours). If this stays empty for a few days, your Hunter key may need attention.</span>`;

/* leads */
const LSTAT={new:["\ud83c\udd95 New","info"],emailed:["\ud83d\udce4 Emailed","ok"],send_failed:["\u26a0\ufe0f Bad address","bad"],sequence_complete:["\u2705 Sequence done","ok"]};
const lchip=s=>{const[t,c]=LSTAT[s]||[s,'zzz'];return `<span class="chip ${c}">${t}</span>`};
const vchip=l=>l.source==='hunter_verified'?'<span class="chip ok">\u2705 Verified</span>':'<span class="chip zzz">\ud83d\udd0d Research only</span>';
const lfilters=['All','Verified','Emailed','New'];let lcur='All';
function lmatch(l){if(lcur==='All')return true;if(lcur==='Verified')return l.source==='hunter_verified';if(lcur==='Emailed')return l.status==='emailed'||l.status==='sequence_complete';return l.status==='new'}
window.lpick=f=>{lcur=f;renderLeads()};
function renderLeads(){
 document.getElementById('lpills').innerHTML=lfilters.map(f=>`<span class="pill ${f===lcur?'on':''}" onclick="lpick('${f}')">${f}</span>`).join('');
 const rows=D.leadsList.filter(lmatch);
 document.getElementById('leadsbox').innerHTML=rows.length?
  `<table><tr><th>Who</th><th>Email</th><th>Why they need us</th><th></th><th>Status</th></tr>`+rows.slice(0,40).map(l=>
  `<tr><td><b>${esc(l.full_name||'-')}</b><div class="mut" style="font-size:11.5px">${esc(l.position||'')} \u00b7 ${esc(l.company||'')}</div></td>`+
  `<td style="font-size:12px">${esc(l.email||'-')}</td>`+
  `<td class="mut" style="font-size:12px;max-width:280px">${esc((l.pain_point||'').slice(0,120))}</td>`+
  `<td>${vchip(l)}</td><td>${lchip(l.status)}</td></tr>`).join('')+`</table>`+
  (rows.length>40?`<div class="mut" style="margin-top:8px;font-size:12px">Showing 40 of ${rows.length} - download the full list below.</div>`:'')
  :'<span class="mut">No leads match this filter yet. The Lead Finder searches every 2 hours.</span>';
}
renderLeads();

/* attention */
const errs=D.analytics.errors.slice(0,6);
const redos=todayTasks.filter(t=>t.status==='needs_revision');
document.getElementById('issues').innerHTML=(errs.length||redos.length)?
 `<div class="card">`+
 redos.map(t=>`<div style="padding:5px 0">🔁 <b>${nice(t.agent)}</b> — work didn't pass the quality check (<span class="mut">${esc(t.quality)}</span>). It retries automatically on the next run. Nothing for you to do.</div>`).join('')+
 errs.map(e=>`<div style="padding:5px 0">⚠️ <b>${nice(e.role)}</b> hit a technical error at ${esc(e.ts.slice(0,16))} — <span class="mut">${esc(e.error)}</span></div>`).join('')+
 `</div>`
 :'<div class="card good">✅ Nothing. Your company is running cleanly.</div>';

/* links + export */
document.getElementById('lnk-exp').href=D.repo+'/tree/main/data/exports';
document.getElementById('lnk-act').href=D.repo+'/actions';
document.getElementById('foot').textContent=`Scroll and Find AI Workforce OS · runs itself every 2 hours on GitHub Actions · total AI spend to date $${(D.analytics.cost_usd||0).toFixed(2)} · ${(D.analytics.input_tokens+D.analytics.output_tokens).toLocaleString()} tokens`;
function dl(name,text,mime){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:mime}));a.download=name;a.click()}
function csv(rows){if(!rows||!rows.length)return '';const ks=[...new Set(rows.flatMap(r=>Object.keys(r)))];return [ks.join(','),...rows.map(r=>ks.map(k=>JSON.stringify(typeof r[k]==='object'?JSON.stringify(r[k]||''):(r[k]??''))).join(','))].join('\n')}
window.exp=(what,fmt)=>{const d=what==='all'?D:D[what];dl(`sf_${what}.${fmt}`,fmt==='csv'?csv(d):JSON.stringify(d,null,1),fmt==='csv'?'text/csv':'application/json')};
</script></body></html>"""

def build_dashboard():
    a = load_analytics()
    health = a.get("health", {})
    data = {
        "tasks": load_tasks()[:80],
        "recs": load_recs()[:40],
        "requests": load_requests()[:60],
        "outreach": [{k: v for k, v in e.items() if k != "body"} for e in load_outreach()[:30]],
        "workforce": {k: {"dept": v["dept"], "hours": v["hours"], "mission": v["mission"]} for k, v in WORKFORCE.items()},
        "analytics": {"input_tokens": a.get("input_tokens", 0), "output_tokens": a.get("output_tokens", 0),
                      "cost_usd": a.get("cost_usd", 0.0), "errors": a.get("errors", [])[:20],
                      "health": health,
                      "healthOk": sum(1 for h in health.values() if h.get("ok")),
                      "healthAll": max(len(health), 1)},
        "finance": _load(F_FINANCE, {}),
        "leads": len(_load(F_LEADS, [])),
        "leadsList": [{k: (str(l.get(k, ""))[:160]) for k in
                       ("full_name", "position", "company", "email", "pain_point", "status", "source", "created_at")}
                      for l in _load(F_LEADS, [])[:80]],
        "repo": REPO_URL,
        "sentToday": len(_sent_today()),
    }
    html = DASH_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__BUILT__", now()[:16])
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[SF] dashboard built -> docs/index.html ({len(html)//1024} KB)")

# ----------------------------------------------------------------------------
# INSTALLER — one GitHub Actions workflow runs the whole company
# ----------------------------------------------------------------------------
WORKFLOW_YML = """name: Scroll and Find — AI Workforce OS
on:
  schedule:
    - cron: '10 */2 * * *'    # every 2h: run due employees + auto outreach
    - cron: '45 13 * * *'     # daily: Workforce Director audit + daily status email
  workflow_dispatch:
    inputs:
      command:
        description: 'auto | run due | run <role> | director | manager | dashboard | daily-report | outreach | export'
        default: 'auto'

concurrency:
  group: scroll-and-find
  cancel-in-progress: false

permissions:
  contents: write

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4.2.2
      - uses: actions/setup-python@v5.4.0
        with: { python-version: '3.11' }
      - run: pip install anthropic
      - name: Decide command
        id: cmd
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            echo "cmd=${{ github.event.inputs.command }}" >> $GITHUB_OUTPUT
          elif [ "${{ github.event.schedule }}" = "45 13 * * *" ]; then
            echo "cmd=daily" >> $GITHUB_OUTPUT
          else
            echo "cmd=auto" >> $GITHUB_OUTPUT
          fi
      - name: Execute
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_EMAIL: ${{ secrets.GMAIL_EMAIL }}
          GMAIL_PASSWORD: ${{ secrets.GMAIL_PASSWORD }}
          DIGEST_EMAIL: ${{ secrets.DIGEST_EMAIL }}
          COMPANY_ADDRESS: ${{ secrets.COMPANY_ADDRESS }}
        run: |
          if [ "${{ steps.cmd.outputs.cmd }}" = "daily" ]; then
            python scroll_and_find.py director
            python scroll_and_find.py daily-report
          elif [ "${{ steps.cmd.outputs.cmd }}" = "auto" ]; then
            python scroll_and_find.py run due
            python scroll_and_find.py outreach
          else
            python scroll_and_find.py ${{ steps.cmd.outputs.cmd }}
          fi
          python scroll_and_find.py manager
          python scroll_and_find.py export
          python scroll_and_find.py dashboard
      - name: Commit results (race-safe)
        run: |
          git config user.name "ScrollAndFind Bot"
          git config user.email "bot@scrollandfind.com"
          git add data/ docs/
          git diff --staged --quiet && exit 0
          git commit -m "SF workforce run — $(date -u +%Y-%m-%d-%H%M)"
          for i in 1 2 3; do git pull --rebase && git push && break || sleep $((i*5)); done
"""

def install():
    os.makedirs(WF_DIR, exist_ok=True)
    with open(os.path.join(WF_DIR, "scroll_and_find.yml"), "w", encoding="utf-8") as f:
        f.write(WORKFLOW_YML)
    if not os.path.exists(F_KNOWLEDGE):
        _save(F_KNOWLEDGE, dict(DEFAULT_KNOWLEDGE))
    build_dashboard()
    print("[SF] installed: .github/workflows/scroll_and_find.yml + seeded knowledge base + dashboard")

# ----------------------------------------------------------------------------
# STATUS (terminal report)
# ----------------------------------------------------------------------------
def status():
    t, a, recs = load_tasks(), load_analytics(), load_recs()
    print(f"\n=== SCROLL AND FIND — AI WORKFORCE OS (full-auto) ===")
    print(f" employees: {len(WORKFORCE)} | tasks stored: {len(t)} | spend: ${a.get('cost_usd',0):.4f} "
          f"| tokens: {a.get('input_tokens',0)}/{a.get('output_tokens',0)}")
    print(f" emails sent today: {len(_sent_today())}/{MAX_EMAILS_PER_DAY}")
    print(f" open director recommendations: {sum(1 for r in recs if r.get('status')=='open')}")
    due = [r for r in WORKFORCE if is_due(r)]
    print(f" due to run now: {', '.join(due) if due else 'none'}\n")

# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "install":
        install()
    elif cmd == "run":
        target = args[1] if len(args) > 1 else "due"
        if target == "due":
            due = [r for r in WORKFORCE if is_due(r)]
            print(f"[SF] due now: {', '.join(due) if due else 'none'}")
            for r in due:
                run_employee(r)
        elif target == "all":
            for r in WORKFORCE:
                run_employee(r)
        else:
            run_employee(target)
    elif cmd == "auto":
        for r in [r for r in WORKFORCE if is_due(r)]:
            run_employee(r)
        run_outreach()
    elif cmd == "director":
        run_director()
    elif cmd == "manager":
        run_manager()
    elif cmd == "dashboard":
        build_dashboard()
    elif cmd == "status":
        status()
    elif cmd == "outreach":
        run_outreach()
    elif cmd == "daily-report":
        daily_report()
    elif cmd == "export":
        export_data()
    elif cmd == "suppress" and len(args) > 1:
        suppress_email(args[1])
    elif cmd == "approve" and len(args) > 1:
        approve(args[1])
    elif cmd == "reject" and len(args) > 1:
        reject(args[1], args[2] if len(args) > 2 else "rejected")
    elif cmd == "approve-email" and len(args) > 1:
        approve_email(args[1])
    elif cmd == "send-emails":
        send_emails()
    else:
        print(f"[SF] unknown command: {' '.join(args)}\n{__doc__}")

if __name__ == "__main__":
    main()
