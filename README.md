# OpsRunner AI Agent System

Runs 24/7 on GitHub Actions. Zero server cost. Minimal Claude API usage.

## Setup (10 minutes)

### Step 1 — Add API key to GitHub Secrets
1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `ANTHROPIC_API_KEY`
4. Value: your key from console.anthropic.com
5. Click **Add secret**

### Step 2 — Update dashboard with your GitHub username
Edit `dashboard/index.html` line 3:
```
const GITHUB_USER = "YOUR_GITHUB_USERNAME";  // ← change this
```

### Step 3 — Enable GitHub Actions
Go to your repo → **Actions** tab → Click **Enable workflows**

### Step 4 — View your dashboard
Open `dashboard/index.html` in Chrome (double-click the file)

## Agent schedule

| Agent | Runs every | Claude calls | ~Daily cost |
|-------|-----------|-------------|-------------|
| Sales | 1 hour | 1 per run | ~$0.05 |
| Marketing | 2 hours | 1 per run | ~$0.03 |
| Finance | 8 hours | 1 per run | ~$0.01 |
| Client success | 4 hours | 1 per run | ~$0.02 |
| Tech | 6 hours | 1 per run | ~$0.01 |
| Manager review | after each | 0 (rule-based) | free |
| **Total** | | **~20-25/day** | **~$0.12/day** |

## Manually trigger any agent
Go to **Actions** tab → click agent → **Run workflow**

## File structure
```
.github/workflows/     ← GitHub Actions schedules
agents/
  base.py             ← shared utilities
  sales.py            ← lead gen + cold emails
  marketing.py        ← LinkedIn + Twitter posts
  finance.py          ← revenue models + forecasts
  client.py           ← onboarding + retention emails
  tech.py             ← product roadmap + sprints
  manager.py          ← auto-review (no API calls)
dashboard/
  index.html          ← open this in Chrome
data/
  tasks.json          ← all agent outputs stored here
```
