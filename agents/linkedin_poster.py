"""
LinkedIn Poster — 4 posts per week on a fixed content calendar
Monday: Problem/Stats post
Wednesday: Product story post  
Friday: Social proof / results post
Sunday: OpsRunner / accounting firms post
"""
import sys, os, json, uuid, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.base import call_claude, PRODUCTS

POSTS_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "posts.json")
TASKS_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tasks.json")

# Weekly content calendar — which day posts what
WEEKLY_CALENDAR = {
    0: {  # Monday
        "type":  "problem_stats",
        "angle": "Subscription blindness — Americans spend $219/mo, 2.5x what they think. 59.9% have unused subscriptions.",
        "goal":  "Problem awareness — make people realise they have this problem",
        "cta":   "Upload your bank statement free at leakly-psi.vercel.app",
    },
    2: {  # Wednesday
        "type":  "product_story",
        "angle": "How Leakly finds hidden subscriptions in your bank statement — no bank login, no credentials, upload PDF/Excel/CSV.",
        "goal":  "Product education — show how it works in simple terms",
        "cta":   "Try it free — leakly-psi.vercel.app",
    },
    4: {  # Friday
        "type":  "social_proof",
        "angle": "What users discover when they upload their first statement — real examples of hidden charges found (Netflix price hike, forgotten Spotify, unused gym app).",
        "goal":  "Social proof — show real results to build trust",
        "cta":   "What will YOU find? leakly-psi.vercel.app",
    },
    6: {  # Sunday
        "type":  "opsrunner",
        "angle": "Accounting firms spend $30K-$80K/month on staff for work that AI can do. OpsRunner automates 9 departments — reconciliation, categorisation, compliance, reporting.",
        "goal":  "B2B awareness — target accounting firm owners",
        "cta":   "Book a demo — singhjaspal3460@gmail.com",
    },
}

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

    # Save to tasks.json for dashboard
    tasks = []
    if os.path.exists(TASKS_DB):
        try:
            with open(TASKS_DB) as f:
                tasks = json.load(f)
        except:
            tasks = []
    tasks.insert(0, {
        "id": post["id"], "agent": "Marketing agent",
        "manager": "VP Revenue", "task_type": "linkedin_post",
        "title": f"LinkedIn post — {post['type']} — {post['post_date']}",
        "output": f"POST TYPE: {post['type'].upper()}\nSCHEDULED: {post['post_date']}\n\n=== LINKEDIN POST ===\n\n{post['linkedin']}\n\n=== TWITTER/X THREAD ===\n\n{post['twitter']}\n\n=== BEST TIME TO POST ===\n{post['timing']}",
        "status": "completed", "created_at": post["created_at"],
        "updated_at": post["created_at"],
        "revision_note": "Auto-approved", "approved_by": "CEO (auto)",
    })
    with open(TASKS_DB, "w") as f:
        json.dump(tasks[:500], f, indent=2, default=str)

def run():
    now     = datetime.datetime.utcnow()
    weekday = now.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun

    # Only create post on scheduled days
    if weekday not in WEEKLY_CALENDAR:
        day_name = now.strftime("%A")
        print(f"[LINKEDIN] {day_name} is not a post day. Schedule: Mon/Wed/Fri/Sun")
        return None

    cal = WEEKLY_CALENDAR[weekday]
    day_name = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")

    # Check if we already posted today
    posts = load_posts()
    today = now.strftime("%Y-%m-%d")
    already_posted = any(p.get("post_date","")[:10] == today for p in posts)
    if already_posted:
        print(f"[LINKEDIN] Already posted today ({today}) — skipping")
        return None

    print(f"[LINKEDIN] Creating {cal['type']} post for {day_name} {date_str}")

    system = f"""You are a LinkedIn content expert for Leakly and OpsRunner.
{PRODUCTS}
Key stats: Americans spend $219/mo on subscriptions (2.5x their estimate). 59.9% have unused paid subs. $2,628/year average.
Write posts that stop scrolling. Hook on line 1. Data + story. Short paragraphs. Human voice.
Never start with "I'm excited" or "Thrilled to share". Be direct and specific."""

    prompt = f"""Create a complete LinkedIn content package for {day_name} {date_str}.

POST TYPE: {cal['type']}
ANGLE: {cal['angle']}
GOAL: {cal['goal']}
CTA: {cal['cta']}

## LINKEDIN POST
Requirements:
- Line 1: scroll-stopping hook (stat, question, or bold statement — NOT "I")  
- Lines 2-10: value through story, data, or insight
- Use line breaks between every 1-2 sentences (LinkedIn formatting)
- End with ONE clear CTA
- Max 1300 characters
- Max 3 hashtags at the very end

## TWITTER/X THREAD (7 tweets)
- Tweet 1: hook that makes people tap "Read more" 
- Tweets 2-6: one insight per tweet, max 270 chars each
- Tweet 7: CTA with URL
- Number each tweet: 1/7, 2/7 etc

## BEST TIME TO POST
LinkedIn: [exact time in IST and why]
Twitter: [exact time in IST and why]

## WHY THIS ANGLE TODAY
One sentence explaining why {day_name} is the right day for this content."""

    result = call_claude(system, prompt)

    # Parse sections
    sections = result.split("##")
    linkedin = twitter = timing = why = ""
    for s in sections:
        su = s.upper()
        if "LINKEDIN POST" in su:
            linkedin = s.split("\n",1)[1].strip() if "\n" in s else s.strip()
        elif "TWITTER" in su:
            twitter = s.split("\n",1)[1].strip() if "\n" in s else s.strip()
        elif "BEST TIME" in su:
            timing = s.split("\n",1)[1].strip() if "\n" in s else s.strip()
        elif "WHY THIS" in su:
            why = s.split("\n",1)[1].strip() if "\n" in s else s.strip()

    post = {
        "id":         str(uuid.uuid4())[:8],
        "type":       cal["type"],
        "angle":      cal["angle"],
        "goal":       cal["goal"],
        "linkedin":   linkedin or result,
        "twitter":    twitter,
        "timing":     timing,
        "why_today":  why,
        "status":     "ready",
        "post_date":  now.isoformat(),
        "char_count": len(linkedin),
        "created_at": now.isoformat(),
    }

    save_post(post)
    print(f"[LINKEDIN] ✓ {cal['type']} post created — {len(linkedin)} chars")
    return post

if __name__ == "__main__":
    run()
