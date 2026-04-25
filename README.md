# SprintSynergy — AI-Enabled Jira Automation Platform

A complete sprint management platform with a **Streamlit UI**, a **FastAPI plugin layer**, and **24 AI-callable tools** for sprint CRUD, Scrum metrics, SAFe metrics, and Claude AI chat.

---

## Architecture

```
Streamlit UI  (app.py)
      ↓
FastAPI layer  (sprint_synergy_api.py)   ←  external integrations plug in here
      ↓
Core Engine  (ss_lib.py · ss_metrics.py · ss_ai.py)
      ↓
Jira REST API
```

---

## File Reference

| File | Role |
|---|---|
| `app.py` | Streamlit entry point |
| `sprint_synergy_api.py` | FastAPI REST API — 24 tools, API-key auth |
| `ss_lib.py` | Jira library — 13 functions, env-var credentials |
| `ss_metrics.py` | Scrum + SAFe metrics — 11 functions |
| `ss_ai.py` | Claude/OpenAI tool schemas + `dispatch_tool()` |
| `utils.py` | Streamlit session-state helpers |
| `health_report.py` | Scheduled HTML health report generator |
| `.env.template` | Copy to `.env` and fill in credentials |
| `config.template.ini` | Copy to `config.ini` for local use |
| `requirements.txt` | All Python dependencies |

---

## Quick Start — Streamlit UI

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/sprint-synergy-mysm-app.git
cd sprint-synergy-mysm-app

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set credentials (choose one method)

# Method A: environment variables
export JIRA_URL=https://yourorg.atlassian.net
export JIRA_EMAIL=you@example.com
export JIRA_API_TOKEN=your_token
export ANTHROPIC_API_KEY=sk-ant-your_key

# Method B: .env file
cp .env.template .env
# Edit .env and fill in your values

# Method C: config.ini (local only)
cp config.template.ini config.ini
# Edit config.ini and fill in your values

# 4. Run the UI
streamlit run app.py
```

Browser opens at **http://localhost:8501**

---

## Quick Start — FastAPI Layer

```bash
# Run the API server
uvicorn sprint_synergy_api:app --reload --port 8000

# Health check
curl http://localhost:8000/

# List all tools
curl http://localhost:8000/tools

# Run a tool
curl -X POST http://localhost:8000/tool \
     -H "x-api-key: CHANGE_ME_SECRET_KEY" \
     -H "Content-Type: application/json" \
     -d '{
           "tool": "velocity_trend",
           "args": {"board_id": 34, "last_n": 5},
           "creds": {
             "jira_url":  "https://yourorg.atlassian.net",
             "email":     "you@example.com",
             "api_token": "your_token"
           }
         }'
```

---

## Credential Priority

For every Jira call, credentials are resolved in this order:

1. `creds=` dict passed directly to the function (Streamlit / API layer)
2. Environment variables: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
3. `.env` file (loaded automatically via python-dotenv)
4. `config.ini` on disk (local only — in `.gitignore`)

---

## Security

- `config.ini` and `.env` are in `.gitignore` — **never committed**
- The API layer requires an `x-api-key` header on every request
- Set `API_KEY` as an environment variable in production
- No credentials are hardcoded anywhere in the source files

---

## AI Tools Available (24 total)

| Category | Tools |
|---|---|
| Sprint management | list_sprints, create_sprint, create_sprint_series, rename_sprint, delete_sprint, start_sprint, close_sprint |
| Issues | list_sprint_issues, move_issues_to_sprint, validate_sprint, validate_and_close_sprint |
| Reports | sprint_report, velocity_trend |
| Scrum metrics | scrum_commitment_reliability, scrum_throughput, scrum_cycle_time, scrum_defect_ratio, scrum_sprint_goal_success, scrum_sprint_burndown |
| SAFe metrics | safe_pi_predictability, safe_pi_velocity, safe_flow_metrics, safe_feature_progress, safe_program_dashboard |

---

*Built by Core Catalyst HQ — Sprint Synergy Platform*
