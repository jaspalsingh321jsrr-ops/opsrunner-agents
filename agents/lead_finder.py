"""
Lead Finder Agent — runs every 2 hours
Only sends emails to Hunter-verified leads (real emails).
Claude-generated leads are saved but NOT emailed (marked as needs_verification).
"""
import sys, os, json, uuid, datetime, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import call_claude, PRODUCTS

HUNTER_KEY = os.environ.get("HUNTER_API_KEY", "")
LEADS_DB   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "leads.json")
FINANCE_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finance.json")

# Real CPA firm domains — Hunter can find real emails here
CPA_DOMAINS = [
    "padgettbusiness.com", "bookkeeping-express.com", "beachfleischman.com",
    "hhcpa.com", "grfcpa.com", "mhtcpa.com", "wrcpa.com", "mkdcpa.com",
    "hcvt.com", "dmcpas.com", "aldercpa.com", "skrcpa.com",
    "solomoncpa.com", "westcpa.com", "bgwcpas.com", "gma-cpa.com",
    "smithadvisory.com", "taxpronetwork.com", "accountingpros.com",
    "cpaamerica.com", "bookkeepingplus.com",
]

# Real small business domains
SMB_DOMAINS = [
    "nextdoor.com", "thumbtack.com", "alignable.com",
    "yelp.com", "angi.com", "houzz.com",
]

ICP_CPA = """
IDEAL CUSTOMER — CPA FIRM:
- Small CPA / bookkeeping firm, 3-20 staff
- Uses QBO, Xero, or Sage manually
- Spends 20+ hours/week on reconciliation
- Pain: too much manual work, can't scale
- PRODUCT: OpsRunner (AI automates 90% of accounting work)
"""

ICP_SMB = """
IDEAL CUSTOMER — SMALL BUSINESS OWNER:
- Business owner with 1-20 employees
- Pays for forgotten SaaS subscriptions
- Pain: losing money on unused subscriptions
- PRODUCT: Scroll_land_find (finds hidden subscriptions, no bank login)
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
        domains = [CPA_DOMAINS[idx % len(CPA_DOMAINS)]]  # SMB Hunter rarely works, use CPA
        icp     = ICP_CPA
        segment = "cpa_firm"
    return domains, icp, segment

def hunter_search(domain):
    """Search Hunter for REAL verified emails only."""
    if not HUNTER_KEY:
        print(f"[HUNTER] No API key set")
        return []
    try:
        r = requests.get("https://api.hunter.io/v2/domain-search", params={
            "domain": domain, "api_key": HUNTER_KEY, "limit": 5,
        }, timeout=15)
        data   = r.json()
        emails = data.get("data", {}).get("emails", [])
        org    = data.get("data", {}).get("organization", domain)

        print(f"[HUNTER] {domain} → found {len(emails)} emails")

        # Only use emails with 70%+ confidence
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

        print(f"[HUNTER] {domain} → {len(verified)} emails with 70%+ confidence")
        return verified
    except Exception as e:
        print(f"[HUNTER] Error for {domain}: {e}")
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
Return ONLY:
SUBJECT: [under 8 words]
BODY:
[body]"""

    prompt = f"""Write a cold email for this CPA firm contact:
Name: {lead['first_name']} {lead['last_name']}
Company: {lead['company']}
Position: {lead.get('position', 'Owner')}
Product: OpsRunner — AI automates 90% of bookkeeping reconciliation and reporting
Benefit: saves 30+ hours/week per bookkeeper, clients get reports 5x faster
Tone: one founder to another, direct and honest"""

    result  = call_claude(system, prompt)
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
    if not subject:
        subject = f"Quick question about {lead.get('company', 'your firm')}"
    if not body_text:
        body_text = result.strip()

    return subject, body_text

def run():
    existing        = load_leads()
    existing_emails = {l["email"].lower() for l in existing}
    domains, icp, segment = get_domains_for_run()
    new_leads       = []

    print(f"[LEAD FINDER] Searching Hunter for real emails | Domains: {', '.join(domains)}")

    # Hunter only — no Claude fallback for email sending
    contacts = []
    for domain in domains:
        contacts.extend(hunter_search(domain))

    fresh = [c for c in contacts if c["email"].lower() not in existing_emails]
    print(f"[LEAD FINDER] {len(fresh)} new verified contacts found")

    if not fresh:
        print("[LEAD FINDER] No verified emails found this run — skipping (better than sending to fake addresses)")
        return []

    for contact in fresh[:3]:
        if not contact.get("email"):
            continue

        # Only write emails for Hunter-verified contacts
        subject, body = write_cold_email(contact, segment)

        # Build LinkedIn if missing
        linkedin = contact.get("linkedin", "")
        if not linkedin:
            fn     = contact.get("first_name","").lower().replace(" ","-")
            ln     = contact.get("last_name","").lower().replace(" ","-")
            linkedin = f"https://www.linkedin.com/in/{fn}-{ln}-cpa"

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
            "confidence":      contact.get("confidence", 0),
            "source":          "hunter_verified",
            "email_subject":   subject,
            "email_body":      body,
            # AUTO-APPROVED — Hunter verified, real email
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
        print(f"[LEAD FINDER] ✓ VERIFIED: {contact.get('first_name')} {contact.get('last_name')} <{contact['email']}> ({contact.get('confidence')}% confidence) — {contact.get('company')}")

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
        print(f"[LEAD FINDER] ✓ {len(new_leads)} verified leads ready to send")
    else:
        print("[LEAD FINDER] No verified leads this run")

    return new_leads

if __name__ == "__main__":
    run()
