"""Client Success Agent — runs every 4 hours. 1 Claude call per run."""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.base import call_claude, new_task, save_task, PRODUCTS

SYSTEM = f"""You are the Client Success Agent.
{PRODUCTS}
Write warm, helpful emails. Not salesy. Focus on user value. Short sentences. Clear CTAs.
"""

def run():
    day = datetime.datetime.utcnow().strftime("%B %d")
    output = call_claude(SYSTEM, f"""
Date: {day}

Create today's client success email toolkit (all 5 emails ready to send):

## EMAIL 1 — WELCOME (new free user, hasn't uploaded yet)
Subject:
Body: (max 100 words)
CTA: Upload your first statement

## EMAIL 2 — DAY 3 NUDGE (signed up, uploaded once, not back)
Subject:
Body: (max 100 words)
CTA: See what we found for you

## EMAIL 3 — FREE → PRO UPGRADE (hit 3-upload limit)
Subject:
Body: (max 100 words)
CTA: Upgrade to Pro — $9.99/mo

## EMAIL 4 — CHURN SAVE (cancelled Pro subscription)
Subject:
Body: (max 100 words)
CTA: Come back — 1 month free

## EMAIL 5 — REFERRAL ASK (active user, NPS score 9-10)
Subject:
Body: (max 100 words)
CTA: Share Leakly with one friend

## WHATSAPP MESSAGE VERSIONS (under 160 chars each)
One WhatsApp version for emails 1, 3, and 4 above.
""")

    task = new_task(
        agent="Client success agent",
        task_type="client_emails",
        title=f"Client email toolkit — {day}",
        output=output,
        manager="VP Revenue",
    )
    save_task(task)
    print(f"[CLIENT] Created task {task['id']}")
    return task

if __name__ == "__main__":
    run()
