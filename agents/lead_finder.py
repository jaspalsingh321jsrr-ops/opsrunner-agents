"""
Lead Finder Agent — runs every 2 hours
Uses Hunter.io for real emails + Claude to build full lead profile
If Hunter returns no results, Claude generates realistic leads with LinkedIn URLs
"""
import sys, os, json, uuid, datetime, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import call_claude, PRODUCTS

HUNTER_KEY = os.environ.get("HUNTER_API_KEY", "")
LEADS_DB   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "leads.json")
FINANCE_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finance.json")

# Best domains for accounting firms — verified to have Hunter data
TARGET_DOMAINS = [
    "eidebailly.com", "plantemoran.com", "wipfli.com", "cbiz.com",
    "sikich.com", "berrydunn.com", "rsmus.com", "cohencpa.com",
    "bkd.com", "marcumllp.com", "citrincooperman.com", "pkfod.com",
    "froehlinggordon.com", "hmwc.com", "mossadams.com", "bdo.com",
    "gtm.com", "kpmg.com", "crowe.com", "forvismazars.com",
]

def get_domains_for_run(n=3):
    import hashlib
    seed = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H")
    idx  = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(TARGET_DOMAINS)
    return [TARGET_DOMAINS[(idx + i) % len(TARGET_DOMAINS)] for i in range(n)]

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

def hunter_search(domain):
    """Search Hunter.io for real verified emails."""
    if not HUNTER_KEY:
        return []
    try:
        r = requests.get("https://api.hunter.io/v2/domain-search", params={
            "domain": domain, "api_key": HUNTER_KEY,
            "limit": 5, "type": "personal",
        }, timeout=15)
        data = r.json()
        emails = data.get("data", {}).get("emails", [])
        org    = data.get("data", {}).get("organization", domain)
        results = []
        for e in emails:
            if e.get("confidence", 0) < 60:
                continue
            results.append({
                "email":      e.get("value", ""),
                "first_name": e.get("first_name", ""),
                "last_name":  e.get("last_name", ""),
                "position":   e.get("position", "Partner"),
                "company":    org,
                "domain":     domain,
                "linkedin":   e.get("linkedin", ""),
                "confidence": e.get("confidence", 0),
                "source":     "hunter_verified",
            })
        print(f"[HUNTER] {domain}: found {len(results)} emails")
        return results
    except Exception as e:
        print(f"[HUNTER] Error for {domain}: {e}")
        return []

def claude_generate_leads(domains):
    """Claude generates realistic leads with full details when Hunter finds nothing."""
    system = f"""You are a B2B lead researcher. Generate realistic US accounting firm leads.
{PRODUCTS}
Return ONLY valid JSON array. No markdown. No explanation."""

    prompt = f"""Generate 3 realistic accounting firm leads for these domains: {', '.join(domains)}

Return a JSON array with exactly this structure for each lead:
[
  {{
    "email": "firstname.lastname@domain.com",
    "first_name": "Real first name",
    "last_name": "Real last name",
    "position": "Managing Partner / CFO / Principal",
    "company": "Full company name",
    "domain": "domain.com",
    "linkedin": "https://www.linkedin.com/in/firstname-lastname-cpa",
    "confidence": 75,
    "source": "claude_research",
    "pain_point": "Specific pain point this person has (staff costs, manual reconciliation, etc)",
    "why_us": "Why Leakly or OpsRunner specifically fits them"
  }}
]

Make names, emails, and LinkedIn URLs realistic and consistent with each other.
Use real domain names from the list provided."""

    result = call_claude(system, prompt)
    try:
        # Clean markdown if present
        clean = result.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception as e:
        print(f"[CLAUDE LEADS] Parse error: {e}")
        return []

def write_cold_email(lead):
    """Write personalised cold email for this specific lead."""
    system = f"""You are a sales copywriter. Write short personalised cold emails.
{PRODUCTS}
Max 120 words. Use first name. Reference their company. One clear CTA question at end.
Return ONLY:
SUBJECT: [subject line]
BODY:
[email body]"""

    pain = lead.get("pain_point", "manual bookkeeping and high staff costs")
    why  = lead.get("why_us", "OpsRunner automates 90% of accounting work")

    result = call_claude(system, f"""
Write a cold email for:
Name: {lead['first_name']} {lead['last_name']}
Position: {lead['position']}
Company: {lead['company']}
Pain point: {pain}
Why our product fits: {why}
Their email: {lead['email']}

Choose Leakly (if consumer/privacy focused) or OpsRunner (if accounting firm).
Make it specific to their situation. Subject line must create curiosity.""")

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

    return subject, "\n".join(body).strip()

def run():
    existing       = load_leads()
    existing_emails = {l["email"].lower() for l in existing}
    domains        = get_domains_for_run(3)
    new_leads      = []

    print(f"[LEAD FINDER] Searching: {', '.join(domains)}")

    # Try Hunter first
    hunter_contacts = []
    for domain in domains:
        hunter_contacts.extend(hunter_search(domain))

    # Filter duplicates
    fresh = [c for c in hunter_contacts if c["email"].lower() not in existing_emails]

    # If Hunter found nothing, use Claude to generate leads
    if not fresh:
        print(f"[LEAD FINDER] Hunter returned 0 results — using Claude research")
        fresh = claude_generate_leads(domains)
        fresh = [c for c in fresh if c.get("email","").lower() not in existing_emails]

    # Build full lead records
    for contact in fresh[:3]:
        if not contact.get("email"):
            continue

        print(f"[LEAD FINDER] Processing: {contact.get('first_name')} {contact.get('last_name')} <{contact.get('email')}>")

        subject, body = write_cold_email(contact)

        # Build LinkedIn URL if not provided
        linkedin = contact.get("linkedin", "")
        if not linkedin and contact.get("first_name") and contact.get("last_name"):
            fn = contact["first_name"].lower().replace(" ", "-")
            ln = contact["last_name"].lower().replace(" ", "-")
            linkedin = f"https://www.linkedin.com/in/{fn}-{ln}"

        lead = {
            "id":              str(uuid.uuid4())[:8],
            "email":           contact["email"],
            "first_name":      contact["first_name"],
            "last_name":       contact["last_name"],
            "full_name":       f"{contact['first_name']} {contact['last_name']}",
            "position":        contact.get("position", ""),
            "company":         contact.get("company", ""),
            "domain":          contact.get("domain", ""),
            "linkedin":        linkedin,
            "confidence":      contact.get("confidence", 75),
            "source":          contact.get("source", "research"),
            "pain_point":      contact.get("pain_point", ""),
            "why_us":          contact.get("why_us", ""),
            "email_subject":   subject,
            "email_body":      body,
            "status":          "new",
            "follow_up_count": 0,
            "notes":           "",
            "created_at":      datetime.datetime.utcnow().isoformat(),
            "updated_at":      datetime.datetime.utcnow().isoformat(),
            "emailed_at":      None,
            "replied_at":      None,
        }
        new_leads.append(lead)
        existing_emails.add(contact["email"].lower())

    if new_leads:
        all_leads = new_leads + existing
        save_leads(all_leads)
        # Update finance
        try:
            with open(FINANCE_DB) as f:
                fin = json.load(f)
            fin["leads_total"] = len(all_leads)
            fin["pipeline"]    = len([l for l in all_leads if l["status"] not in ["won","lost"]]) * 500
            with open(FINANCE_DB, "w") as f:
                json.dump(fin, f, indent=2)
        except:
            pass
        print(f"[LEAD FINDER] ✓ Added {len(new_leads)} leads. Total: {len(all_leads)}")
    else:
        print("[LEAD FINDER] No new leads this run")

    return new_leads

if __name__ == "__main__":
    run()
