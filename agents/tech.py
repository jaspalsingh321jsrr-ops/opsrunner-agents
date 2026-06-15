"""Tech Agent — runs every 6 hours. 1 Claude call per run."""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.base import call_claude, new_task, save_task, PRODUCTS

SYSTEM = f"""You are the Tech & Product Agent. Think like a CTO.
{PRODUCTS}
Leakly stack: Next.js 14, TypeScript, Supabase, Vercel, Mumbai region.
Roadmap: Razorpay payments, email reports, WhatsApp alerts, mobile app, Bank AA.
Be specific. Give user stories, effort estimates, and architecture decisions.
"""

def run():
    day = datetime.datetime.utcnow().strftime("%B %d")
    output = call_claude(SYSTEM, f"""
Date: {day}

Weekly tech & product review:

## SPRINT PRIORITIES (next 2 weeks)
Top 3 features to build for Leakly with:
- User story (As a [user] I want [feature] so that [value])
- Acceptance criteria (3 bullet points)
- Effort: S/M/L (S=1-2 days, M=3-5 days, L=1+ week)
- Why now (business reason)

## PAYMENT INTEGRATION PLAN
Razorpay (India) + Stripe (US) — what to build:
- Database changes needed
- API endpoints to create
- Webhook events to handle
- Estimated total effort

## PERFORMANCE & RELIABILITY
3 specific things to check in a Next.js + Supabase app at this stage.
For each: what to check, how to check it, what good looks like.

## MOBILE READINESS
Top 3 things to fix before Leakly works well on mobile.
Each with: what to change, which file, estimated time.

## THIS WEEK'S TECH PRIORITY
One specific coding task. Include: file to edit, what to change, why it matters most.
""")

    task = new_task(
        agent="Tech agent",
        task_type="product_roadmap",
        title=f"Tech review — {day}",
        output=output,
        manager="VP Operations",
    )
    save_task(task)
    print(f"[TECH] Created task {task['id']}")
    return task

if __name__ == "__main__":
    run()
