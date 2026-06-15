"""
Marketing Agent — runs every 2 hours via GitHub Actions
1 Claude call per run = ~$0.002
"""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from agents.base import call_claude, new_task, save_task, PRODUCTS

SYSTEM = f"""You are the Marketing Agent for OpsRunner and Leakly.
{PRODUCTS}
Key stats: Americans spend $219/mo on subscriptions (2.5x their estimate). 59.9% have unused subs.
Voice: Smart, direct, slightly provocative. Hook in line 1. Data-driven.
"""

CONTENT_ROTATION = [
    "Problem awareness — subscription blindness stats",
    "Product story — how Leakly finds hidden charges",
    "Social proof angle — what users discover",
    "OpsRunner — cost of traditional accounting staff",
    "Privacy angle — why no bank login matters",
    "India market — Jio/Airtel/Swiggy subscriptions",
    "US market — Netflix/Spotify/Amazon price hikes",
]

def run():
    day   = datetime.datetime.utcnow().strftime("%A %B %d")
    hour  = int(datetime.datetime.utcnow().strftime("%H"))
    angle = CONTENT_ROTATION[(hour // 2) % len(CONTENT_ROTATION)]

    output = call_claude(SYSTEM, f"""
Date: {day} — Content angle: {angle}

Create a complete content batch:

## LINKEDIN POST (main post — max 1300 chars)
Angle: {angle}
Must have: strong hook line 1, data or story, clear CTA at end
Format: Short punchy paragraphs. Line breaks between each. No hashtag spam (max 3 relevant).

## TWITTER/X THREAD (7 tweets)
Same angle as LinkedIn but compressed.
Tweet 1 = hook. Tweets 2-6 = value. Tweet 7 = CTA.
Each tweet max 270 chars.

## SHORT FORM (Instagram/Facebook — max 150 chars + CTA)

## GOOGLE ADS COPY
Keyword: "subscription tracker no bank login"
Headline 1 (30 chars): 
Headline 2 (30 chars): 
Headline 3 (30 chars): 
Description (90 chars): 

## BEST TIME TO POST TODAY
LinkedIn: [time]
Twitter: [time]
Reason: [why]
""")

    task = new_task(
        agent="Marketing agent",
        task_type="content_creation",
        title=f"Content batch — {angle[:40]} — {day}",
        output=output,
        manager="VP Revenue",
    )
    save_task(task)
    print(f"[MARKETING] Created task {task['id']}")
    return task

if __name__ == "__main__":
    run()
