"""
Sales Agent — runs hourly via GitHub Actions
1 Claude call per run = ~$0.002
Free: lead research from public sources
"""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.base import call_claude, new_task, save_task, PRODUCTS

SYSTEM = f"""You are the Sales Agent for OpsRunner and Leakly.
{PRODUCTS}
Write highly specific, personalised cold outreach. Never generic. Always research-based.
Format output as structured sections. Be concise and persuasive.
"""

def run():
    day  = datetime.datetime.utcnow().strftime("%A %B %d")
    hour = datetime.datetime.utcnow().strftime("%H:00 UTC")

    # ONE Claude call — generates leads + emails + LinkedIn messages together
    # This is the only API call in this entire agent run
    output = call_claude(SYSTEM, f"""
Date: {day} {hour}

Generate a complete sales package:

## LEAD RESEARCH (no API needed — these are hypothetical but realistic)
Find 3 specific accounting firm owners or CFOs in the US who would benefit from either Leakly or OpsRunner.
For each lead include:
- Full name + company name + location
- Why they specifically need our product (be specific — staff costs, privacy concerns, etc)
- LinkedIn URL pattern: linkedin.com/in/[firstname-lastname]
- Best subject line for their situation

## COLD EMAILS (ready to send — personalised to each lead)
Write one cold email per lead. Max 120 words each. Strong subject line. One clear CTA.

## LINKEDIN CONNECTION MESSAGES (under 300 chars each)
One per lead.

## FOLLOW-UP SEQUENCE
Day 3, Day 7, Day 14 follow-up for the strongest lead.

## TODAY'S PRIORITY
Which lead to contact first and why.
""")

    task = new_task(
        agent="Sales agent",
        task_type="lead_generation",
        title=f"Sales package — {day} {hour}",
        output=output,
        manager="VP Revenue",
    )
    save_task(task)
    print(f"[SALES] Created task {task['id']}")
    return task

if __name__ == "__main__":
    run()
