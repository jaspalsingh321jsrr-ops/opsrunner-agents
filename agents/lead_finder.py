"""
Lead Finder Agent — runs every 2 hours
Finds Hunter-VERIFIED emails at the domains YOU choose.

TARGETING IS YOURS: edit data/target_domains.json and add the website domains
of e-commerce brands, Shopify agencies, or any business you want as a client.
Example: {"domains": ["examplestore.com", "someagency.com"]}
The system contacts each domain only once, with the free statement-scan offer.
"""
import sys, os, json, uuid, datetime, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import call_claude, PRODUCTS

HUNTER_KEY = os.environ.get("HUNTER_API_KEY", "")
DATA_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LEADS_DB   = os.path.join(DATA_DIR, "leads.json")
FINANCE_DB = os.path.join(DATA_DIR, "finance.json")
TARGETS_DB = os.path.join(DATA_DIR, "target_domains.json")

ICP = """
IDEAL CUSTOMER — E-COMMERCE SELLER:
- Shopify / Amazon / multi-channel store, $10k-$100k per month revenue, US-based
- Pain: multi-channel fees, refunds and settlements make their books a mess;
  bookkeeping always late; no idea where money leaks
- THE OFFER (free, no pitch): send your bank statement, get a money-leak report
  in 24 hours. No bank login. Privacy-first.
"""

def now():
    return datetime.datetime.utcnow().isoformat()

def _load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def load_leads():
    return _load(LEADS_DB, [])

def save_leads(leads):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LEADS_DB, "w") as f:
        json.dump(leads[:1000], f, indent=2, default=str)

def get_target_domains():
    """Domains come from data/target_domains.json — Jaspal's editable list."""
    cfg = _load(TARGETS_DB, {})
    domains = [d.strip().lower() for d in cfg.get("domains", []) if isinstance(d, str) and "." in d]
    contacted = {l.get("domain", "") for l in load_leads()}
    fresh = [d for d in domains if d not in contacted]
    return fresh

def hunter_search(domain):
    if not HUNTER_KEY:
        print("[HUNTER] No API key set")
        return []
    try:
        r = requests.get("https://api.hunter.io/v2/domain-search", params={
            "domain": domain, "api_key": HUNTER_KEY, "limit": 5,
        }, timeout=15)
        data   = r.json()
        emails = data.get("data", {}).get("emails", [])
        org    = data.get("data", {}).get("organization", domain)
        verified = [{
            "email":      e.get("value", ""),
            "first_name": e.get("first_name") or "",
            "last_name":  e.get("last_name") or "",
            "position":   e.get("position") or "Owner",
            "company":    org,
            "domain":     domain,
            "linkedin":   e.get("linkedin") or "",
            "confidence": e.get("confidence", 0),
            "source":     "hunter_verified",
        } for e in emails if e.get("confidence", 0) >= 70 and e.get("value")]
        print(f"[HUNTER] {domain} -> {len(verified)} verified emails (70%+ confidence)")
        return verified
    except Exception as e:
        print(f"[HUNTER] Error for {domain}: {e}")
        return []

def write_scan_offer_email(lead):
    system = f"""You write outreach for Jaspal Singh, founder of Scroll and Find and OpsRunner.
{PRODUCTS}
You are offering ONLY the FREE statement scan — never pitch the paid service in a cold email.
Rules:
- MAX 90 words in the body
- Open with a pain specific to running an online store (settlement fees, refunds, messy books)
- Offer: free money-leak report from their bank statement, 24h turnaround, NO bank login
- End with a simple yes/no question
- Founder-to-founder tone, zero corporate language
- Sign off: Jaspal Singh, jaspal@scrollandfind.com
Return ONLY:
SUBJECT: [under 8 words]
BODY:
[body]"""
    prompt = (f"Write the free-scan offer email for:\n"
              f"Name: {lead['first_name']} {lead['last_name']}\n"
              f"Company: {lead['company']} ({lead['domain']})\n"
              f"Position: {lead.get('position', 'Owner')}")
    result = call_claude(system, prompt)
    subject, body, in_body = "", [], False
    for line in result.strip().split("\n"):
        if line.startswith("SUBJECT:"):
            subject = line.replace("SUBJECT:", "").strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body.append(line)
    body_text = "\n".join(body).strip() or result.strip()
    subject = subject or f"Quick question about {lead.get('company', 'your store')}"
    return subject, body_text

def run():
    existing        = load_leads()
    existing_emails = {l["email"].lower() for l in existing if l.get("email")}
    domains         = get_target_domains()[:2]   # 2 domains per run = gentle pace

    if not domains:
        print("[LEAD FINDER] No fresh target domains. Add domains to data/target_domains.json "
              "(e-commerce brands / Shopify agencies you want as clients).")
        return []

    print(f"[LEAD FINDER] Targets this run: {', '.join(domains)}")
    contacts = []
    for domain in domains:
        contacts.extend(hunter_search(domain))

    fresh = [c for c in contacts if c["email"].lower() not in existing_emails]
    if not fresh:
        print("[LEAD FINDER] No new verified emails this run")
        return []

    new_leads = []
    for contact in fresh[:3]:
        subject, body = write_scan_offer_email(contact)
        lead = {
            "id":              str(uuid.uuid4())[:8],
            "segment":         "ecommerce",
            "email":           contact["email"],
            "first_name":      contact.get("first_name", ""),
            "last_name":       contact.get("last_name", ""),
            "full_name":       f"{contact.get('first_name','')} {contact.get('last_name','')}".strip(),
            "position":        contact.get("position", "Owner"),
            "company":         contact.get("company", ""),
            "domain":          contact.get("domain", ""),
            "linkedin":        contact.get("linkedin", ""),
            "confidence":      contact.get("confidence", 0),
            "source":          "hunter_verified",
            "pain_point":      "multi-channel bookkeeping mess, unknown money leaks",
            "why_us":          "free 24h money-leak scan, no bank login",
            "email_subject":   subject,
            "email_body":      body,
            "status":          "new",
            "follow_up_count": 0,
            "notes":           "",
            "created_at":      now(),
            "updated_at":      now(),
            "emailed_at":      None,
            "replied_at":      None,
        }
        new_leads.append(lead)
        existing_emails.add(contact["email"].lower())
        print(f"[LEAD FINDER] VERIFIED: {lead['full_name']} <{lead['email']}> ({lead['confidence']}%) — {lead['company']}")

    if new_leads:
        all_leads = new_leads + existing
        save_leads(all_leads)
        try:
            fin = _load(FINANCE_DB, {})
            fin["leads_total"] = len(all_leads)
            with open(FINANCE_DB, "w") as f:
                json.dump(fin, f, indent=2)
        except Exception:
            pass
        print(f"[LEAD FINDER] {len(new_leads)} verified leads queued for the free-scan offer")
    return new_leads

if __name__ == "__main__":
    run()
