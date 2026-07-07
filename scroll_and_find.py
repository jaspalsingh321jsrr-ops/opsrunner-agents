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

 DAILY USE (all also run automatically on schedule):
   python scroll_and_find.py run due            # run every AI employee due now
   python scroll_and_find.py run marketing      # run one AI employee
   python scroll_and_find.py director           # Workforce Director audit
   python scroll_and_find.py manager            # rule-based manager review
   python scroll_and_find.py dashboard          # rebuild docs/index.html
   python scroll_and_find.py status             # terminal status report
   python scroll_and_find.py approve <task_id>  # human approval gate
   python scroll_and_find.py reject  <task_id> "reason"
   python scroll_and_find.py approve-email <email_id>
   python scroll_and_find.py send-emails        # sends ONLY human-approved

 COST: claude-haiku, 1 API call per employee run, cadence-throttled.
 Default schedule ~= 8-10 calls/day  ->  roughly $0.05-0.15/day.
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

FOUNDER: Jaspal Singh — QBO certified. Contact: singhjaspal3460@gmail.com

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

    # --- Approval routing ---
    if not passed:
        task["status"] = "needs_revision"
        task["note"] = f"Manager({spec['manager']}) rejected: {reason}"
    elif spec["high_risk"]:
        task["status"] = "pending_human_approval"
        task["note"] = "High-risk output (external communication). Run: python scroll_and_find.py approve " + task["id"]
    else:
        task["status"] = "completed"
        task["approved_by"] = spec["manager"]

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
# EXECUTIVE + DEPARTMENT DASHBOARDS (static build -> docs/index.html on Pages)
# ----------------------------------------------------------------------------
DASH_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scroll and Find — AI Workforce OS</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f1117;color:#e2e8f0;font-size:13px}
.app{display:flex;min-height:100vh}
.side{width:210px;background:#1a1d27;border-right:1px solid #2a2d3e;flex-shrink:0;padding-bottom:20px}
.logo{padding:16px;border-bottom:1px solid #2a2d3e}.logo h1{font-size:15px}.logo p{font-size:10px;color:#64748b;margin-top:2px}
.sec{padding:12px 14px 4px;font-size:9px;font-weight:700;color:#4b5563;text-transform:uppercase;letter-spacing:.08em}
.nav{display:block;padding:7px 14px;font-size:12px;cursor:pointer;color:#94a3b8;border-left:2px solid transparent}
.nav:hover{background:#222535;color:#e2e8f0}.nav.on{background:#222535;color:#7f77dd;border-left-color:#7f77dd;font-weight:600}
.main{flex:1;padding:16px 20px;overflow-x:hidden}
h2{font-size:15px;margin-bottom:2px}.sub{font-size:10px;color:#64748b;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-bottom:16px}
.stat{background:#1a1d27;border:1px solid #2a2d3e;border-radius:8px;padding:10px 12px}
.stat .v{font-size:20px;font-weight:700;font-family:ui-monospace,monospace}.stat .l{font-size:9px;color:#64748b;margin-top:3px;text-transform:uppercase;letter-spacing:.04em}
.card{background:#1a1d27;border:1px solid #2a2d3e;border-radius:8px;padding:12px;margin-bottom:14px}
.card h3{font-size:12px;margin-bottom:8px;color:#a5b4fc}
table{width:100%;border-collapse:collapse;font-size:11px}
th{text-align:left;color:#64748b;font-size:9px;text-transform:uppercase;padding:4px 6px;border-bottom:1px solid #2a2d3e}
td{padding:5px 6px;border-bottom:1px solid #1f2230;vertical-align:top}
.b{display:inline-block;padding:1px 7px;border-radius:9px;font-size:9px;font-weight:700}
.g{background:#14532d;color:#4ade80}.y{background:#422006;color:#fbbf24}.r{background:#450a0a;color:#f87171}.bl{background:#0c1a33;color:#60a5fa}.p{background:#2e1065;color:#c4b5fd}
pre{white-space:pre-wrap;font-family:inherit;font-size:11px;color:#cbd5e1;max-height:260px;overflow-y:auto;background:#111827;border-radius:6px;padding:8px;margin-top:6px}
.hide{display:none}.mut{color:#64748b}
</style></head><body><div class="app">
<div class="side"><div class="logo"><h1>Scroll and Find</h1><p>AI Workforce OS · OpsRunner DNA</p></div>
<div class="sec">Company</div><div class="nav on" data-v="exec">Executive Dashboard</div>
<div class="sec">Departments</div><div id="deptnav"></div></div>
<div class="main"><h2 id="title">Executive Dashboard</h2><div class="sub">Built __BUILT__ UTC · auto-refreshes on every agent run</div>
<div id="view"></div></div></div>
<script>
const D = __DATA__;
const S = {completed:'g',pending_human_approval:'y',needs_revision:'r',in_progress:'bl',open:'y',draft:'y',approved:'bl',sent:'g',error:'r',stale:'r'};
const b = s => `<span class="b ${S[s]||'bl'}">${(s||'').replace(/_/g,' ')}</span>`;
const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;');
function stat(v,l){return `<div class="stat"><div class="v">${v}</div><div class="l">${l}</div></div>`}
function taskRows(ts){return ts.map(t=>`<tr><td><b>${esc(t.agent)}</b><div class="mut">${esc(t.id)} · ${esc((t.created_at||'').slice(0,16))}</div></td><td>${b(t.status)}<div class="mut">${esc(t.quality||'')}</div></td><td><details><summary style="cursor:pointer">output</summary><pre>${esc(t.output)}</pre></details></td></tr>`).join('')}
function exec(){
 const t=D.tasks, pend=t.filter(x=>x.status==='pending_human_approval'), rev=t.filter(x=>x.status==='needs_revision');
 const openReq=D.requests.filter(r=>r.status==='open'), openRec=D.recs.filter(r=>r.status==='open');
 const eng=openReq.filter(r=>/engineer/i.test(r.department));
 let h='<div class="grid">';
 h+=stat('$'+(D.finance.mrr||D.finance.revenue||0),'Revenue / MRR')+stat(D.leads,'Leads')+stat(D.finance.clients||0,'Clients')+stat(D.finance.projects||0,'Projects');
 h+=stat(Object.keys(D.workforce).length,'AI Workforce')+stat(t.filter(x=>x.status==='completed').length,'Workflows Done')+stat(pend.length,'Pending Approvals')+stat(eng.length,'Engineering Tasks');
 h+=stat(rev.length,'Errors / Revisions')+stat(D.analytics.healthOk+'/'+D.analytics.healthAll,'API Health')+stat((D.analytics.input_tokens+D.analytics.output_tokens).toLocaleString(),'Tokens Used')+stat('$'+(D.analytics.cost_usd||0).toFixed(3),'API Cost To Date');
 h+='</div>';
 if(pend.length){h+=`<div class="card"><h3>⚠ Pending Human Approvals — run: python scroll_and_find.py approve &lt;id&gt;</h3><table><tr><th>Agent</th><th>Status</th><th>Output</th></tr>${taskRows(pend)}</table></div>`}
 h+=`<div class="card"><h3>AI Workforce Status</h3><table><tr><th>Employee</th><th>Dept</th><th>Cadence</th><th>Last Run</th><th>Health</th></tr>${Object.entries(D.workforce).map(([k,w])=>{const hh=D.analytics.health[k];return `<tr><td><b>${k}</b><div class="mut">${esc(w.mission.slice(0,70))}…</div></td><td>${w.dept}</td><td>${w.hours}h</td><td>${hh?esc(hh.last_run.slice(0,16)):'<span class=mut>never</span>'}</td><td>${hh?(hh.ok?b('completed'):b('error')):b('open')}</td></tr>`}).join('')}</table></div>`;
 h+=`<div class="card"><h3>Workforce Director — Open Recommendations</h3>${openRec.length?`<table><tr><th>Problem / Impact</th><th>Solution</th><th>Pri</th><th>Effort</th><th>ROI</th></tr>${openRec.map(r=>`<tr><td><b>${esc(r.problem)}</b><div class="mut">${esc(r.business_impact)}</div></td><td>${esc(r.recommended_solution)}<div class="mut">deps: ${esc(r.dependencies||'—')}</div></td><td>${b(r.priority==='P1'?'error':'open')} ${esc(r.priority)}</td><td>${esc(r.estimated_effort)}</td><td>${esc(r.expected_roi)}</td></tr>`).join('')}</table>`:'<span class="mut">None — run: python scroll_and_find.py director</span>'}</div>`;
 h+=`<div class="card"><h3>Automation Queue — Cross-Department Requests</h3>${openReq.length?`<table><tr><th>From → Dept</th><th>Request</th><th>Pri</th><th>Status</th></tr>${openReq.map(r=>`<tr><td>${esc(r.from)} → <b>${esc(r.department)}</b></td><td>${esc(r.request)}</td><td>${esc(r.priority)}</td><td>${b(r.status)}</td></tr>`).join('')}</table>`:'<span class="mut">Queue empty</span>'}</div>`;
 h+=`<div class="card"><h3>Outreach Queue (human-gated)</h3>${D.outreach.length?`<table><tr><th>Id</th><th>To</th><th>Status</th><th>Created</th></tr>${D.outreach.slice(0,10).map(e=>`<tr><td>${esc(e.id)}</td><td>${esc(e.to||'— fill in sf_outreach.json')}</td><td>${b(e.status)}</td><td>${esc((e.created_at||'').slice(0,16))}</td></tr>`).join('')}</table>`:'<span class="mut">Empty</span>'}</div>`;
 h+=`<div class="card"><h3>Notifications & Errors</h3>${D.analytics.errors.length?`<table><tr><th>When</th><th>Role</th><th>Error</th></tr>${D.analytics.errors.slice(0,8).map(e=>`<tr><td>${esc(e.ts.slice(0,16))}</td><td>${esc(e.role)}</td><td class="mut">${esc(e.error)}</td></tr>`).join('')}</table>`:'<span class="mut">No errors 🎉</span>'}</div>`;
 h+=`<div class="card"><h3>Recent Activity</h3><table><tr><th>Agent</th><th>Status</th><th>Output</th></tr>${taskRows(t.slice(0,12))}</table></div>`;
 return h;
}
function dept(name){
 const roles=Object.entries(D.workforce).filter(([k,w])=>w.dept===name).map(([k])=>k);
 const t=D.tasks.filter(x=>roles.includes(x.agent)||x.dept===name);
 const req=D.requests.filter(r=>r.department.toLowerCase().includes(name.toLowerCase().split(' ')[0]));
 let h='<div class="grid">'+stat(roles.length,'AI Employees')+stat(t.length,'Tasks')+stat(t.filter(x=>x.status==='completed').length,'Completed')+stat(t.filter(x=>x.status==='pending_human_approval').length,'Awaiting Approval')+'</div>';
 h+=`<div class="card"><h3>Open Requests For This Department</h3>${req.filter(r=>r.status==='open').map(r=>`<div style="padding:4px 0">${b('open')} <b>${esc(r.priority)}</b> ${esc(r.request)} <span class="mut">(from ${esc(r.from)})</span></div>`).join('')||'<span class="mut">None</span>'}</div>`;
 h+=`<div class="card"><h3>Tasks</h3><table><tr><th>Agent</th><th>Status</th><th>Output</th></tr>${taskRows(t.slice(0,15))||''}</table></div>`;
 return h;
}
const depts=[...new Set(Object.values(D.workforce).map(w=>w.dept))];
document.getElementById('deptnav').innerHTML=depts.map(d=>`<div class="nav" data-v="${d}">${d}</div>`).join('');
document.querySelectorAll('.nav').forEach(n=>n.onclick=()=>{document.querySelectorAll('.nav').forEach(x=>x.classList.remove('on'));n.classList.add('on');
 const v=n.dataset.v;document.getElementById('title').textContent=v==='exec'?'Executive Dashboard':v+' Dashboard';
 document.getElementById('view').innerHTML=v==='exec'?exec():dept(v);});
document.getElementById('view').innerHTML=exec();
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
    - cron: '15 */6 * * *'    # every 6h: run all due employees (cadence-throttled)
    - cron: '45 13 * * *'     # daily: Workforce Director audit
  workflow_dispatch:
    inputs:
      command:
        description: 'run due | run <role> | director | manager | dashboard | send-emails'
        default: 'run due'

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
            echo "cmd=director" >> $GITHUB_OUTPUT
          else
            echo "cmd=run due" >> $GITHUB_OUTPUT
          fi
      - name: Execute
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_EMAIL: ${{ secrets.GMAIL_EMAIL }}
          GMAIL_PASSWORD: ${{ secrets.GMAIL_PASSWORD }}
        run: |
          python scroll_and_find.py ${{ steps.cmd.outputs.cmd }}
          python scroll_and_find.py manager
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
    print("[SF] next: commit + push, add ANTHROPIC_API_KEY secret, enable Pages from /docs")

# ----------------------------------------------------------------------------
# STATUS (terminal report)
# ----------------------------------------------------------------------------
def status():
    t, a, recs = load_tasks(), load_analytics(), load_recs()
    pend = [x for x in t if x["status"] == "pending_human_approval"]
    print(f"\n=== SCROLL AND FIND — AI WORKFORCE OS ===")
    print(f" employees: {len(WORKFORCE)} | tasks stored: {len(t)} | spend: ${a.get('cost_usd',0):.4f} "
          f"| tokens: {a.get('input_tokens',0)}/{a.get('output_tokens',0)}")
    print(f" pending human approvals: {len(pend)}")
    for x in pend[:10]:
        print(f"   -> approve {x['id']}  ({x['agent']}, {x['created_at'][:16]})")
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
    elif cmd == "director":
        run_director()
    elif cmd == "manager":
        run_manager()
    elif cmd == "dashboard":
        build_dashboard()
    elif cmd == "status":
        status()
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
