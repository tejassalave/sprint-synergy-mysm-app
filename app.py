"""SprintSynergy — Streamlit web UI

Wraps the entire SprintSynergy Python toolkit (sprint CRUD, Scrum + SAFe
metrics, AI chat) in a friendly browser interface.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py --server.port 5000
"""

from __future__ import annotations

import streamlit as st

from utils import init_state, render_sidebar_status, creds_ready

st.set_page_config(
    page_title="SprintSynergy",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_state()
render_sidebar_status()

st.title("🏃 SprintSynergy")
st.subheader("A friendly UI for every SprintSynergy command — local or web.")

st.markdown(
    """
SprintSynergy turns the official Jira REST API into a full sprint-management
workbench: create sprints, move issues, run reports, compute Scrum & SAFe
metrics, and chat with Claude about your board.

Use the sidebar to navigate:

| Page | What it does |
| --- | --- |
| **⚙️ Setup Check** | Verifies Python, packages, credentials, and Jira reachability. Run this first. |
| **🔧 Configuration** | Connect to **any** Jira-compatible instance (Cloud, Data Center, Stacks, etc.). |
| **📅 Sprint Management** | Create, rename, start, close, or delete sprints. |
| **📋 Issues & Validation** | List sprint issues, move issues, validate before closing. |
| **📊 Sprint Reports** | Per-sprint completion stats and multi-sprint velocity trends. |
| **📈 Scrum Metrics** | Say-do ratio, throughput, cycle time, defect ratio, goal success, burndown. |
| **🚀 SAFe Metrics** | PI predictability, PI velocity, flow metrics, feature progress, program dashboard. |
| **🤖 AI Chatbot** | Ask Claude to manage your sprints — backed by the same tools. |
| **🔌 API Integration** | How to call SprintSynergy from your own Supabase + Claude tool. |
"""
)

st.divider()

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Sprint & Issue tools", "13")
with c2:
    st.metric("Scrum metrics", "6")
with c3:
    st.metric("SAFe metrics", "5")

st.caption(
    "Total: 24 AI-callable tools. Same engine powers the UI pages, the "
    "Claude chatbot, and the API integration endpoint."
)

st.divider()

if not creds_ready():
    st.info(
        "👉 Start by opening **🔧 Configuration** in the sidebar to connect "
        "this app to your Jira instance.",
        icon="ℹ️",
    )
else:
    st.success(
        "You're connected. Pick any page from the sidebar to begin.",
        icon="✅",
    )

with st.expander("Run this app locally on Windows"):
    st.markdown(
        """
1. Download / copy the entire `sprint_synergy_app/` folder anywhere on your PC.
2. Install Python 3.10 or newer if you don't have it.
3. Open Command Prompt in that folder and run:
   ```
   pip install -r requirements.txt
   streamlit run app.py
   ```
4. Your browser will open at http://localhost:8501. Done.

Your credentials live in `config.ini` (saved when you click **Save to disk**
on the Configuration page), so you only have to fill them in once.
"""
    )
