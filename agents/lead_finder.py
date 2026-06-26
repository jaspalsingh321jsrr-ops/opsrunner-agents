"""
Lead Finder Agent — runs every 2 hours
Finds leads, writes personalised email, auto-approves for immediate sending.
No human approval needed — fully automatic pipeline.
"""
import sys, os, json, uuid, datetime, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import call_claude, PRODUCTS

HUNTER_KEY = os.environ.get("HUNTER_API_KEY", "")
LEADS_DB   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "leads.json")
FINANCE_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finance.json")

# ── TARGET 1: Small CPA firms ──
CPA_DOMAINS = [
    "padgettbusiness.com", "bookkeeping-express.com", "beachfleischman.com",
    "hhcpa.com", "grfcpa.com", "mhtcpa.com", "wrcpa.com", "mkdcpa.com",
    "hcvt.com", "dmcpas.com", "aldercpa.com", "skrcpa.com",
    "solomoncpa.com", "westcpa.com", "localcpafirm.com",
]

# ── TARGET 2: Small business owners ──
SMB_DOMAINS = [
    "shopify.com", "etsy.com", "squarespace.com", "wix.com",
    "restaurantowner.com", "salonowner.com", "fitnessowner.com",
    "dentistpractice.com", "lawfirm.com", "realtoroffice.com",
    "constructionco.com", "plumbingco.com", "electricalco.com",
]

ICP_CPA = """
IDEAL CUSTOMER — CPA FIRM:
- Small CPA / bookkeeping firm, 3-20 staff
- Uses QBO, Xero, or Sage manually
- Spends 20+ hours/week on reconciliation and data entry
- Annual revenue: $200K-$2M
- Pain: too much manual work, can't scale, staff turnover
- PRODUCT: OpsRunner (AI automates 90% of accounting work)
- NOT: Big 4, KPMG, Deloitte, RSM — too big
"""

ICP_SMB = """
IDEAL CUSTOMER — SMALL BUSINESS OWNER:
- Business owner with 1-20 employees
- Pays for 5-15 SaaS subscriptions they may have forgotten about
- Frustrated with bank login requirements for finance apps
- Pain: losing money on unused subscriptions, messy bank statements
- PRODUCT: Scroll_land_find (finds hidden subscriptions from bank statement, no login needed)
"""

def load_leads():
    os.makedirs(os.path.dirname(LEADS_DB), exist_ok=True)
    if not os.path.exists(LEADS_DB):
        return []
    try:
        with open(LEADS_DB) as f:
            return json.load(f)
    except:
        return []

def save_leads(leads):
    with open(LEADS_DB, "w") as f:
        json.dump(leads[:1000], f, indent=2, default=str)

def get_domains_for_run():
    import hashlib
    seed = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H")
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    hour = datetime.datetime.utcnow().hour
    if hour % 2 == 0:
        domains = [CPA_DOMAINS[idx % len(CPA_DOMAINS)], CPA_DOMAINS[(idx+1) % len(CPA_DOMAINS)]]
        icp     = ICP_CPA
        segment = "cpa_firm"
    else:
        domains = [SMB_DOMAINS[idx % len(SMB_DOMAINS)], SMB_DOMAINS[(idx+1) % len(SMB_DOMAINS)]]
        icp     = ICP_SMB
        segment = "small_business"
    return domains, icp, segment

def hunter_search(domain):
    if not HUNTER_KEY:
        return []
    try:
        r = requests.get("https://api.hunter.io/v2/domain-search", params={
            "domain": domain, "api_key": HUNTER_KEY, "limit": 3,
        }, timeout=15)
        data   = r.json()
        emails = data.get("data", {}).get("emails", [])
        org    = data.get("data", {}).get("organization", domain)
        # Only use emails with 70%+ confidence to reduce bounces
        return [{
            "email":      e.get("value", ""),
            "first_name": e.get("first_name", ""),
            "last_name":  e.get("last_name", ""),
            "position":   e.get("position", "Owner"),
            "company":    org,
            "domain":     domain,
            "linkedin":   e.get("linkedin", ""),
            "confidence": e.get("confidence", 0),
            "source":     "hunter_verified",
        } for e in emails if e.get("confidence", 0) >= 70 and e.get("value")]
    except Exception as e:
        print(f"[HUNTER] Error: {e}")
        return []

def claude_generate_leads(domains, icp, segment):
    system = """You are a B2B lead researcher. Generate realistic US leads.
Return ONLY valid JSON array. No markdown. No explanation. No comments."""

    if segment == "cpa_firm":
        prompt = f"""Generate 3 realistic leads for SMALL CPA firms (5-20 employees only).
{icp}
Domains to use: {", ".join(domains)}

JSON array format:
[{{
  "email": "firstname.lastname@domain.com",
  "first_name": "Common US first name",
  "last_name": "Common US last name",
  "position": "Owner or Managing Partner or Principal",
  "company": "Small local CPA firm name (e.g. Johnson & Associates CPA)",
  "domain": "domain from list",
  "linkedin": "https://www.linkedin.com/in/firstname-lastname-cpa",
  "confidence": 72,
  "source": "claude_research",
  "segment": "cpa_firm",
  "pain_point": "Specific: e.g. 2 bookkeepers spending 35hrs/week manually reconciling 30 QBO clients",
  "why_us": "OpsRunner would automate that 35hrs down to 4hrs, saving $3,500/month in labor"
}}]"""
    else:
        prompt = f"""Generate 3 realistic leads for SMALL BUSINESS OWNERS (restaurants, salons, retail, services).
{icp}
Domains to use: {", ".join(domains)}

JSON array format:
[{{
  "email": "firstname@businessdomain.com",
  "first_name": "Common US first name",
  "last_name": "Common US last name",
  "position": "Owner or Founder or CEO",
  "company": "Small business name (e.g. Maria's Salon, Peak Performance Gym, Smith Plumbing)",
  "domain": "domain from list",
  "linkedin": "https://www.linkedin.com/in/firstname-lastname",
  "confidence": 70,
  "source": "claude_research",
  "segment": "small_business",
  "pain_point": "Specific: e.g. Paying for 12 SaaS tools, forgot about 4 of them, loses $340/month",
  "why_us": "Scroll_land_find finds all hidden subscriptions from their bank statement in 2 minutes, no bank login"
}}]"""

    result = call_claude(system, prompt)
    try:
        clean = result.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception as e:
        print(f"[CLAUDE] Parse error: {e}")
        return []

def write_cold_email(lead, segment):
    system = f"""You are a sales copywriter for Jaspal Singh, founder of Scroll_land_find and OpsRunner.
{PRODUCTS}
Rules:
- MAX 90 words in body
- Start with their specific pain point
- Include one specific number or stat
- End with a simple yes/no question
- Friendly peer tone, NOT corporate
- Sign off: Jaspal Singh, singhjaspal3460@gmail.com
Return ONLY this format (no extra text):
SUBJECT: [under 8 words, specific to their business]
BODY:
[email body]"""

    if segment == "cpa_firm":
        prompt = f"""Write a cold email for this CPA firm owner:
Name: {lead['first_name']} {lead['last_name']}
Company: {lead['company']}
Pain: {lead.get('pain_point', 'spending too many staff hours on manual bookkeeping')}
Product: OpsRunner — AI automates 90% of reconciliation and reporting
Benefit: {lead.get('why_us', 'saves 30+ hours/week per bookkeeper, clients get reports 5x faster')}
Tone: one founder to another, direct and honest"""
    else:
        prompt = f"""Write a cold email for this small business owner:
Name: {lead['first_name']} {lead['last_name']}
Business: {lead['company']}
Pain: {lead.get('pain_point', 'paying for forgotten subscriptions every month')}
Product: Scroll_land_find — upload your bank statement, find all hidden subscriptions in 2 minutes. No bank login needed, totally private.
Benefit: {lead.get('why_us', 'average user finds $200-500/month in forgotten charges')}
Tone: friendly and helpful, like a useful tip from a friend"""

    result = call_claude(system, prompt)
    lines   = result.strip().split("\n")
    subject = ""
    body    = []
    in_body = False
    for line in lines:
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body.append(line)

    body_text = "\n".join(body).strip()

    # Fallback if parsing failed
    if not subject:
        subject = f"Quick question about {lead.get('company', 'your business')}"
    if not body_text:
        body_text = result.strip()

    return subject, body_text

def run():
    existing        = load_leads()
    existing_emails = {l["email"].lower() for l in existing}
    domains, icp, segment = get_domains_for_run()
    new_leads       = []

    print(f"[LEAD FINDER] Segment: {segment} | Domains: {', '.join(domains)}")

    # Try Hunter first (real verified emails)
    contacts = []
    for domain in domains:
        contacts.extend(hunter_search(domain))

    fresh = [c for c in contacts if c["email"].lower() not in existing_emails]

    # Fallback to Claude-generated leads
    if not fresh:
        print("[LEAD FINDER] Hunter empty — using Claude research")
        fresh = claude_generate_leads(domains, icp, segment)
        fresh = [c for c in fresh if c.get("email","").lower() not in existing_emails]

    for contact in fresh[:3]:
        if not contact.get("email"):
            continue

        # Build LinkedIn if missing
        linkedin = contact.get("linkedin", "")
        if not linkedin:
            fn     = contact.get("first_name","").lower().replace(" ","-")
            ln     = contact.get("last_name","").lower().replace(" ","-")
            suffix = "-cpa" if segment == "cpa_firm" else ""
            linkedin = f"https://www.linkedin.com/in/{fn}-{ln}{suffix}"

        subject, body = write_cold_email(contact, segment)

        lead = {
            "id":              str(uuid.uuid4())[:8],
            "segment":         segment,
            "email":           contact["email"],
            "first_name":      contact.get("first_name",""),
            "last_name":       contact.get("last_name",""),
            "full_name":       f"{contact.get('first_name','')} {contact.get('last_name','')}".strip(),
            "position":        contact.get("position","Owner"),
            "company":         contact.get("company",""),
            "domain":          contact.get("domain",""),
            "linkedin":        linkedin,
            "confidence":      contact.get("confidence",72),
            "source":          contact.get("source","research"),
            "pain_point":      contact.get("pain_point",""),
            "why_us":          contact.get("why_us",""),
            "email_subject":   subject,
            "email_body":      body,
            # AUTO-APPROVED — no manual step needed
            "status":          "approved",
            "follow_up_count": 0,
            "notes":           "",
            "created_at":      datetime.datetime.utcnow().isoformat(),
            "updated_at":      datetime.datetime.utcnow().isoformat(),
            "emailed_at":      None,
            "replied_at":      None,
        }
        new_leads.append(lead)
        existing_emails.add(contact["email"].lower())
        print(f"[LEAD FINDER] ✓ {segment}: {contact.get('first_name')} {contact.get('last_name')} <{contact['email']}> — {contact.get('company')} [AUTO-APPROVED]")

    if new_leads:
        all_leads = new_leads + existing
        save_leads(all_leads)
        try:
            with open(FINANCE_DB) as f:
                fin = json.load(f)
            fin["leads_total"] = len(all_leads)
            fin["pipeline"]    = len([l for l in all_leads if l["status"] not in ["won","lost"]]) * 500
            with open(FINANCE_DB, "w") as f:
                json.dump(fin, f, indent=2)
        except:
            pass
        print(f"[LEAD FINDER] ✓ Added {len(new_leads)} new leads — all auto-approved for sending")
    else:
        print("[LEAD FINDER] No new leads this run")

    return new_leads

if __name__ == "__main__":
    run()
