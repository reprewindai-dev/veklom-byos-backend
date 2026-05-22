# Phase 3 Agent Setup — Quick Start

## 1. Install Dependencies

```bash
cd agents/phase3-user-acquisition
pip install -r requirements-agents.txt
```

## 2. Set Environment Variables

Add these to your Coolify environment or `.env` file:

```bash
# Required for ALL agents
OPENAI_API_KEY=sk-...

# Required for Agent 042 (Community / Reddit)
# Get from: https://www.reddit.com/prefs/apps → Create App → Script
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# Required for Agent 041 (Content / dev.to publishing)
# Get from: https://dev.to/settings/extensions
DEVTO_API_KEY=your_devto_api_key
```

## 3. Test With Dry Run First

```bash
# Test community agent (no posts made)
python agent_042_community.py --dry-run

# Test content agent (generates but doesn't publish)
python agent_041_content.py --dry-run

# Check all agent status
python run_all_agents.py --status
```

## 4. Run Live

```bash
# Run community agent RIGHT NOW (live)
python agent_042_community.py

# Run with weekly post
python agent_042_community.py --weekly-post

# Run content publisher (publishes one post to dev.to)
python agent_041_content.py

# Generate Product Hunt launch kit
python agent_044_product_hunt.py

# Generate paid growth assets
python agent_043_paid_growth.py
```

## 5. Run the Full Scheduler (Continuous)

```bash
# Starts scheduler — runs agents automatically on schedule
# Community agent: every 6 hours
# Content/SEO: every Monday morning
python run_all_agents.py
```

To keep it running permanently on Hetzner/Coolify:
```bash
# Using nohup
nohup python run_all_agents.py > /var/log/veklom_agents.log 2>&1 &

# Or add as a systemd service (recommended for production)
# See: /infra/ for systemd service templates
```

## 6. Monitor Activity

Each agent writes a `.jsonl` log file:
```bash
tail -f agent_042_activity.jsonl   # Community agent live log
tail -f agent_041_activity.jsonl   # Content agent live log
tail -f agent_040_activity.jsonl   # SEO agent live log

# View scheduler status
python run_all_agents.py --status
```

## Agent Outputs

| Agent | Output Location | What's Created |
|-------|----------------|----------------|
| 040 SEO | `seo_reports/` | Weekly SEO audit + recommendations |
| 041 Content | `generated_posts/` | Markdown blog posts + dev.to publish |
| 042 Community | `agent_042_activity.jsonl` | Reddit reply log |
| 043 Paid Growth | `paid_growth_assets/` | Keywords JSON + ad copy + strategy |
| 044 Product Hunt | `ph_launch_kit/` | Full PH launch kit Markdown |
