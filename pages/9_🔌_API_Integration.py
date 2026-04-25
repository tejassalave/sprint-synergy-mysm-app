"""SprintSynergy — API Integration Page"""
import streamlit as st
from utils import init_state, render_sidebar_status

st.set_page_config(page_title="API Integration", page_icon="🔌", layout="wide")
init_state(); render_sidebar_status()
st.title("🔌 API Integration")
st.caption("How to call SprintSynergy from your own tools, Lovable frontend, or external systems.")
st.divider()

tab1, tab2, tab3 = st.tabs(["🚀 Quick Start","📋 All Endpoints","💻 Code Examples"])

with tab1:
    st.subheader("Start the API Server")
    st.code("uvicorn sprint_synergy_api:app --reload --port 8000", language="bash")
    st.markdown("Then open **http://localhost:8000/docs** for the interactive Swagger UI.")
    st.divider()
    st.subheader("Health Check")
    st.code('curl http://localhost:8000/', language="bash")
    st.subheader("List All 24 Tools")
    st.code('curl http://localhost:8000/tools', language="bash")
    st.subheader("Run a Tool")
    st.code('''curl -X POST http://localhost:8000/tool \\
     -H "x-api-key: CHANGE_ME_SECRET_KEY" \\
     -H "Content-Type: application/json" \\
     -d '{
           "tool": "velocity_trend",
           "args": {"board_id": 34, "last_n": 5},
           "creds": {
             "jira_url":  "https://yourorg.atlassian.net",
             "email":     "you@example.com",
             "api_token": "your_token"
           }
         }' ''', language="bash")

with tab2:
    st.subheader("All Available Endpoints")
    endpoints = [
        ("GET",  "/",         "Health check — returns status and tool count"),
        ("GET",  "/tools",    "List all 24 tool names"),
        ("POST", "/tool",     "Run any tool — pass tool name, args, and Jira creds"),
    ]
    import pandas as pd
    st.dataframe(pd.DataFrame(endpoints, columns=["Method","Path","Description"]),
                 use_container_width=True)

    st.subheader("All 24 Tool Names")
    tools = [
        ("Sprint Management", ["list_sprints","create_sprint","create_sprint_series",
                               "rename_sprint","delete_sprint","start_sprint","close_sprint"]),
        ("Issues",            ["list_sprint_issues","move_issues_to_sprint",
                               "validate_sprint","validate_and_close_sprint"]),
        ("Reports",           ["sprint_report","velocity_trend"]),
        ("Scrum Metrics",     ["scrum_commitment_reliability","scrum_throughput",
                               "scrum_cycle_time","scrum_defect_ratio",
                               "scrum_sprint_goal_success","scrum_sprint_burndown"]),
        ("SAFe Metrics",      ["safe_pi_predictability","safe_pi_velocity",
                               "safe_flow_metrics","safe_feature_progress","safe_program_dashboard"]),
    ]
    for cat, names in tools:
        with st.expander(f"**{cat}** ({len(names)} tools)"):
            for n in names:
                st.code(n)

with tab3:
    st.subheader("Python Example")
    st.code('''import requests

API_URL = "http://localhost:8000"
API_KEY = "CHANGE_ME_SECRET_KEY"
HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}

def run_tool(tool, args, creds):
    r = requests.post(f"{API_URL}/tool",
        headers=HEADERS,
        json={"tool": tool, "args": args, "creds": creds})
    return r.json()

creds = {
    "jira_url":  "https://yourorg.atlassian.net",
    "email":     "you@example.com",
    "api_token": "your_token"
}

# Get velocity trend
result = run_tool("velocity_trend", {"board_id": 34, "last_n": 5}, creds)
print(result)

# Create 3 sprints
result = run_tool("create_sprint_series", {
    "board_id": 34, "prefix": "AES Sprint",
    "start_date": "2026-06-01", "start_number": 6,
    "num_sprints": 3, "duration_days": 14
}, creds)
print(result)''', language="python")

    st.subheader("JavaScript / Lovable Example")
    st.code('''const API_URL = "http://localhost:8000";
const API_KEY = "CHANGE_ME_SECRET_KEY";

async function runTool(tool, args, creds) {
  const response = await fetch(`${API_URL}/tool`, {
    method: "POST",
    headers: {
      "x-api-key": API_KEY,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ tool, args, creds })
  });
  return response.json();
}

// Example: get program dashboard
const result = await runTool(
  "safe_program_dashboard",
  { board_id: 34, sprints_per_pi: 5 },
  { jira_url: "https://yourorg.atlassian.net",
    email: "you@example.com",
    api_token: "your_token" }
);
console.log(result);''', language="javascript")
