"""
Email Sender Agent — runs every 30 minutes
Sends emails that Jaspal has approved in the dashboard
Also handles auto follow-ups on day 3 and day 7
Uses Gmail SMTP — no extra cost
"""
import sys, os, json, datetime, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GMAIL_EMAIL    = os.environ.get("GMAIL_EMAIL", "")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "")
LEADS_DB       = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "leads.json")
FINANCE_DB     = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "finance.json")

FOLLOW_UP_TEMPLATES = {
    3: {
        "subject": "Re: {original_subject}",
        "body": """Hi {first_name},

Just following up on my previous message — wanted to make sure it didn't get buried.

Happy to show you a quick 10-minute demo of how {product} works for firms like {company}.

Worth a quick look this week?

— Jaspal
singhjaspal3460@gmail.com"""
    },
    7: {
        "subject": "Re: {original_subject}",
        "body": """Hi {first_name},

Last follow-up — I know you're busy.

If {product} isn't relevant right now, no worries at all. But if you're still dealing with {pain_point}, I'd love to help.

Free to chat for 15 minutes?

— Jaspal"""
    }
}

def load_leads():
    if not os.path.exists(LEADS_DB):
        return []
    try:
        with open(LEADS_DB) as f:
            return json.load(f)
    except:
        return []

def save_leads(leads):
    with open(LEADS_DB, "w") as f:
        json.dump(leads, f, indent=2, default=str)

def update_finance_sent():
    try:
        with open(FINANCE_DB) as f:
            fin = json.load(f)
        fin["emails_sent"] = fin.get("emails_sent", 0) + 1
        with open(FINANCE_DB, "w") as f:
            json.dump(fin, f, indent=2)
    except:
        pass

def send_email(to_email, subject, body, from_name="Jaspal Singh"):
    """Send email via Gmail SMTP."""
    if not GMAIL_EMAIL or not GMAIL_PASSWORD:
        print(f"[EMAIL] No Gmail credentials — cannot send to {to_email}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{from_name} <{GMAIL_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_EMAIL, GMAIL_PASSWORD)
            server.sendmail(GMAIL_EMAIL, to_email, msg.as_string())
        print(f"[EMAIL] ✓ Sent to {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL] ✗ Failed to send to {to_email}: {e}")
        return False

def days_since(iso_date):
    if not iso_date:
        return 999
    try:
        sent = datetime.datetime.fromisoformat(iso_date)
        return (datetime.datetime.utcnow() - sent).days
    except:
        return 999

def run():
    leads   = load_leads()
    updated = False
    sent_count = 0

    for lead in leads:
        # Send approved emails
        if lead.get("status") == "approved":
            ok = send_email(
                to_email=lead["email"],
                subject=lead["email_subject"],
                body=lead["email_body"],
            )
            if ok:
                lead["status"]     = "sent"
                lead["emailed_at"] = datetime.datetime.utcnow().isoformat()
                lead["updated_at"] = datetime.datetime.utcnow().isoformat()
                update_finance_sent()
                sent_count += 1
                updated = True
            else:
                lead["status"] = "send_failed"
                updated = True

        # Auto follow-up day 3
        elif lead.get("status") == "sent" and lead.get("follow_up_count", 0) == 0:
            days = days_since(lead.get("emailed_at"))
            if days >= 3:
                tmpl = FOLLOW_UP_TEMPLATES[3]
                subject = tmpl["subject"].format(original_subject=lead["email_subject"])
                body    = tmpl["body"].format(
                    first_name=lead["first_name"],
                    company=lead["company"],
                    product="Leakly" if "privacy" in lead.get("email_body","").lower() else "OpsRunner",
                    pain_point="manual reconciliation and high staff costs",
                )
                ok = send_email(lead["email"], subject, body)
                if ok:
                    lead["follow_up_count"] = 1
                    lead["updated_at"]      = datetime.datetime.utcnow().isoformat()
                    update_finance_sent()
                    sent_count += 1
                    updated = True

        # Auto follow-up day 7
        elif lead.get("status") == "sent" and lead.get("follow_up_count", 0) == 1:
            days = days_since(lead.get("emailed_at"))
            if days >= 7:
                tmpl = FOLLOW_UP_TEMPLATES[7]
                subject = tmpl["subject"].format(original_subject=lead["email_subject"])
                body    = tmpl["body"].format(
                    first_name=lead["first_name"],
                    company=lead["company"],
                    product="Leakly" if "privacy" in lead.get("email_body","").lower() else "OpsRunner",
                    pain_point="manual reconciliation",
                )
                ok = send_email(lead["email"], subject, body)
                if ok:
                    lead["follow_up_count"] = 2
                    lead["status"]          = "sequence_complete"
                    lead["updated_at"]      = datetime.datetime.utcnow().isoformat()
                    update_finance_sent()
                    sent_count += 1
                    updated = True

    if updated:
        save_leads(leads)

    print(f"[EMAIL SENDER] Sent {sent_count} emails this run")
    return sent_count

if __name__ == "__main__":
    run()
