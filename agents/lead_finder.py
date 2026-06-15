"""
Lead Finder Agent — runs every 2 hours via GitHub Actions
1. Searches Hunter.io for real accounting firm owners/CFOs
2. Gets verified email addresses
3. Claude writes personalised cold email for each
4. Saves to leads.json with status: new
Cost: 3 Hunter API calls (free tier: 25/month) + 1 Claude call
"""
import sys, os, json, uuid, datetime, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import call_claude, PRODUCTS

HUNTER_KEY  = os.environ.get("HUNTER_API_KEY", "")
LEADS_DB    = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "leads.json")
FINANCE_DB  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finance.json")

# Target companies — accounting firms and CFO services in the US
TARGET_DOMAINS = [
    "bkd.com", "marcumllp.com", "cbiz.com", "citrincooperman.com",
    "pkfod.com", "sikich.com", "berrydunn.com", "eidebailly.com",
    "plantemoran.com", "wipfli.com", "rsmus.com", "kpmg.com",
    "cohencpa.com", "froehlinggordon.com", "hmwc.com",
]

# Rotate through domains so we find new leads each run
import hashlib
def get_today_domains(n=3):
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

def update_finance(new_leads_count):
    try:
        with open(FINANCE_DB) as f:
            fin = json.load(f)
        fin["leads_total"] = fin.get("leads_total", 0) + new_leads_count
        fin["pipeline"] = fin.get("leads_total", 0) * 500  # $500 avg deal value estimate
        with open(FINANCE_DB, "w") as f:
            json.dump(fin, f, indent=2)
    except:
        pass

def find_emails_hunter(domain):
    """Use Hunter.io to find real email addresses at a company."""
    if not HUNTER_KEY:
        print(f"[HUNTER] No API key — skipping real lookup for {domain}")
        return []
    try:
        url = "https://api.hunter.io/v2/domain-search"
        params = {
            "domain": domain,
            "api_key": HUNTER_KEY,
            "limit": 3,
            "type": "personal",
            "seniority": "executive,senior",
            "department": "finance,accounting,management",
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("data", {}).get("emails"):
            results = []
            for e in data["data"]["emails"][:3]:
                results.append({
                    "email":      e.get("value", ""),
                    "first_name": e.get("first_name", ""),
                    "last_name":  e.get("last_name", ""),
                    "position":   e.get("position", ""),
                    "company":    data["data"].get("organization", domain),
                    "domain":     domain,
                    "confidence": e.get("confidence", 0),
                })
            return results
        return []
    except Exception as e:
        print(f"[HUNTER] Error for {domain}: {e}")
        return []

def write_cold_email(lead):
    """Claude writes ONE personalised cold email per lead."""
    system = f"""You are a sales copywriter for OpsRunner and Leakly.
{PRODUCTS}
Write short, specific, human cold emails. Max 120 words. No fluff.
Always use the person's first name. Reference their company specifically.
Subject line must create curiosity. End with one clear question as CTA."""

    prompt = f"""Write a cold email for this lead:

Name: {lead['first_name']} {lead['last_name']}
Position: {lead['position']}
Company: {lead['company']}
Email: {lead['email']}

Choose the most relevant product:
- Leakly if they seem privacy-conscious or deal with personal finance data
- OpsRunner if they run an accounting firm or have a team

Return ONLY:
SUBJECT: [subject line]
BODY:
[email body]"""

    result = call_claude(system, prompt)
    # Parse subject and body
    lines  = result.strip().split("\n")
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
    existing   = load_leads()
    existing_emails = {l["email"] for l in existing}
    domains    = get_today_domains(3)
    new_leads  = []

    print(f"[LEAD FINDER] Searching {len(domains)} domains: {', '.join(domains)}")

    for domain in domains:
        contacts = find_emails_hunter(domain)

        for contact in contacts:
            if not contact["email"]:
                continue
            if contact["email"] in existing_emails:
                print(f"[LEAD FINDER] Already have {contact['email']} — skipping")
                continue
            if contact["confidence"] < 70:
                print(f"[LEAD FINDER] Low confidence {contact['confidence']}% — skipping {contact['email']}")
                continue

            print(f"[LEAD FINDER] Found: {contact['first_name']} {contact['last_name']} <{contact['email']}>")

            # Write personalised email
            subject, body = write_cold_email(contact)

            lead = {
                "id":           str(uuid.uuid4())[:8],
                "email":        contact["email"],
                "first_name":   contact["first_name"],
                "last_name":    contact["last_name"],
                "position":     contact["position"],
                "company":      contact["company"],
                "domain":       contact["domain"],
                "confidence":   contact["confidence"],
                "status":       "new",          # new → email_ready → sent → replied → call → won → lost
                "email_subject": subject,
                "email_body":    body,
                "notes":        "",
                "follow_up_count": 0,
                "created_at":   datetime.datetime.utcnow().isoformat(),
                "updated_at":   datetime.datetime.utcnow().isoformat(),
                "emailed_at":   None,
                "replied_at":   None,
                "call_at":      None,
            }
            new_leads.append(lead)
            existing_emails.add(contact["email"])

    if new_leads:
        all_leads = new_leads + existing
        save_leads(all_leads)
        update_finance(len(new_leads))
        print(f"[LEAD FINDER] Added {len(new_leads)} new leads. Total: {len(all_leads)}")
    else:
        print("[LEAD FINDER] No new leads found this run")

    return new_leads

if __name__ == "__main__":
    run()
