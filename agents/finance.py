"""Finance Agent — runs every 8 hours. 1 Claude call per run."""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.base import call_claude, new_task, save_task, PRODUCTS

SYSTEM = f"""You are the Finance Agent. Think like a CFO.
{PRODUCTS}
Give specific numbers, tables, and actionable recommendations.
"""

def run():
    day = datetime.datetime.utcnow().strftime("%B %d %Y")
    output = call_claude(SYSTEM, f"""
Date: {day}

Generate the daily finance intelligence report:

## REVENUE MODEL — LEAKLY SAAS
Assumptions: Free (3 uploads), Pro $9.99/mo, Business $29.99/mo
Model 12 months: start 0 users → realistic growth curve
Show: MRR, ARR, cumulative revenue per month in a table.

## PRICING DECISION
Should Leakly Pro be $7.99, $9.99, or $12.99?
Show revenue at 500 paid users for each price.
Recommendation with reason.

## UNIT ECONOMICS
- LTV at $9.99/mo with 18-month avg retention
- CAC budget (how much can we spend per paid user?)
- Break-even month (assuming $200/mo infra costs)

## OPSRUNNER MODEL
- Setup fee recommendation: $X one-time
- Monthly retainer per accounting firm client: $X
- Revenue at 5 clients / 10 clients / 20 clients

## THIS WEEK'S FINANCIAL PRIORITY
One specific action Jaspal should take this week.
Include: what to do, expected $ impact, time to implement.
""")

    task = new_task(
        agent="Finance agent",
        task_type="financial_report",
        title=f"Finance report — {day}",
        output=output,
        manager="VP Operations",
    )
    save_task(task)
    print(f"[FINANCE] Created task {task['id']}")
    return task

if __name__ == "__main__":
    run()
