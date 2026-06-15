"""
LinkedIn Auto-Poster — runs every 8 hours via GitHub Actions
Creates and saves posts to posts.json
Note: LinkedIn API requires OAuth — posts saved for manual copy-paste
or use Buffer/Zapier to auto-post from the JSON feed
1 Claude call per run
"""
import sys, os, json, uuid, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import call_claude, PRODUCTS

POSTS_DB  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "posts.json")
TASKS_DB  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tasks.json")

CONTENT_ANGLES = [
    ("stats",      "Subscription blindness stats — $219/mo average, 2.5x what people think"),
    ("privacy",    "Why privacy-first matters — no bank login, no credentials stored"),
    ("story",      "Real story: found $2,400/year in forgotten subscriptions using Leakly"),
    ("opsrunner",  "Accounting firms spending $30K-$80K/month on staff that AI can replace"),
    ("india",      "India market: Jio, Airtel, Swiggy, Zomato subscriptions piling up"),
    ("hook",       "Controversial take on subscription economy and personal finance"),
    ("howto",      "Step by step: how to find hidden subscriptions in your bank statement"),
    ("comparison", "Leakly vs Rocket Money — why no bank login changes everything"),
]

def load_posts():
    if not os.path.exists(POSTS_DB):
        return []
    try:
        with open(POSTS_DB) as f:
            return json.load(f)
    except:
        return []

def save_post(post):
    posts = load_posts()
    posts.insert(0, post)
    os.makedirs(os.path.dirname(POSTS_DB), exist_ok=True)
    with open(POSTS_DB, "w") as f:
        json.dump(posts[:200], f, indent=2, default=str)

    # Also save to tasks.json so it appears in main dashboard
    tasks = []
    if os.path.exists(TASKS_DB):
        try:
            with open(TASKS_DB) as f:
                tasks = json.load(f)
        except:
            tasks = []
    task = {
        "id": post["id"],
        "agent": "Marketing agent",
        "manager": "VP Revenue",
        "task_type": "linkedin_post",
        "title": f"LinkedIn post — {post['angle']}",
        "output": f"LINKEDIN POST:\n\n{post['linkedin']}\n\n---\n\nTWITTER THREAD:\n\n{post['twitter']}",
        "status": "completed",
        "created_at": post["created_at"],
        "updated_at": post["created_at"],
        "revision_note": "Auto-approved",
        "approved_by": "CEO (auto)",
    }
    tasks.insert(0, task)
    with open(TASKS_DB, "w") as f:
        json.dump(tasks[:500], f, indent=2, default=str)

def run():
    now   = datetime.datetime.utcnow()
    hour  = now.hour
    angle_key, angle_desc = CONTENT_ANGLES[(hour // 8) % len(CONTENT_ANGLES)]

    system = f"""You are a LinkedIn content expert for OpsRunner and Leakly.
{PRODUCTS}
Key stats: Americans spend $219/mo on subscriptions (2.5x their estimate). 59.9% have unused subs.
Voice: Smart, direct, data-driven. Hook in line 1 — make people stop scrolling.
Never use hashtag spam. Max 3 relevant hashtags. Short punchy paragraphs."""

    prompt = f"""Create today's content batch. Angle: {angle_desc}

## LINKEDIN POST (max 1300 chars)
Line 1: scroll-stopping hook (no "I" start, no "Excited to share")
Lines 2-8: value, data, or story
Last line: clear CTA
[3 line breaks between sections — LinkedIn formatting]

## TWITTER THREAD (7 tweets)
Tweet 1: hook that makes people click "show more"
Tweets 2-6: one insight each, max 270 chars
Tweet 7: CTA with link to https://leakly-psi.vercel.app

## BEST TIME TO POST TODAY
LinkedIn: [specific time and why]
Twitter: [specific time and why]"""

    result = call_claude(system, prompt)

    # Parse sections
    sections = result.split("##")
    linkedin = ""
    twitter  = ""
    timing   = ""
    for s in sections:
        if "LINKEDIN" in s.upper():
            linkedin = s.replace("LINKEDIN POST", "").replace("(max 1300 chars)", "").strip()
        elif "TWITTER" in s.upper():
            twitter = s.replace("TWITTER THREAD", "").replace("(7 tweets)", "").strip()
        elif "BEST TIME" in s.upper() or "TIME TO POST" in s.upper():
            timing = s.strip()

    post = {
        "id":         str(uuid.uuid4())[:8],
        "angle":      angle_key,
        "angle_desc": angle_desc,
        "linkedin":   linkedin or result,
        "twitter":    twitter,
        "timing":     timing,
        "status":     "ready",  # ready → posted
        "created_at": now.isoformat(),
        "char_count": len(linkedin),
    }

    save_post(post)
    print(f"[LINKEDIN] Created post: {angle_key} ({len(linkedin)} chars)")
    return post

if __name__ == "__main__":
    run()
