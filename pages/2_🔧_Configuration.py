"""SprintSynergy — Configuration Page"""
import os
import streamlit as st
from utils import init_state, render_sidebar_status, save_config_to_disk, get_creds

st.set_page_config(page_title="Configuration", page_icon="🔧", layout="wide")
init_state()
render_sidebar_status()

st.title("🔧 Configuration")
st.caption("Connect SprintSynergy to your Jira instance. Credentials are stored in session only — never hardcoded.")
st.divider()

tab1, tab2, tab3 = st.tabs(["🔐 Jira Credentials", "📋 Board Settings", "🤖 AI Settings"])

with tab1:
    st.subheader("Jira Connection")
    st.info("Your credentials are kept in memory only. Use 'Save to disk' for local persistence (config.ini — never committed to GitHub).")

    col1, col2 = st.columns(2)
    with col1:
        jira_url = st.text_input("Jira URL",
            value=st.session_state.get("jira_url",""),
            placeholder="https://yourorg.atlassian.net",
            help="Your Jira Cloud base URL — no trailing slash")
        email = st.text_input("Email",
            value=st.session_state.get("email",""),
            placeholder="you@example.com")
    with col2:
        api_token = st.text_input("API Token",
            value=st.session_state.get("api_token",""),
            type="password",
            placeholder="ATATT3x...",
            help="Generate at: id.atlassian.com → Security → API Tokens")
        st.markdown("&nbsp;")
        st.markdown("[🔗 Generate API Token](https://id.atlassian.com/manage-profile/security/api-tokens)")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("💾 Save to Session", type="primary", use_container_width=True):
            st.session_state["jira_url"]  = jira_url.strip().rstrip("/")
            st.session_state["email"]     = email.strip()
            st.session_state["api_token"] = api_token.strip()
            st.success("✅ Saved to session. Active until you close the browser.")
    with c2:
        if st.button("💿 Save to Disk (config.ini)", use_container_width=True):
            st.session_state["jira_url"]  = jira_url.strip().rstrip("/")
            st.session_state["email"]     = email.strip()
            st.session_state["api_token"] = api_token.strip()
            path = save_config_to_disk()
            st.success(f"✅ Saved to `{path}` — persists across restarts.")
    with c3:
        if st.button("🔌 Test Connection", use_container_width=True):
            import requests as req
            creds = {"jira_url": jira_url.strip().rstrip("/"),
                     "email": email.strip(), "api_token": api_token.strip()}
            if not all(creds.values()):
                st.error("Fill in all 3 fields first.")
            else:
                with st.spinner("Testing..."):
                    try:
                        r = req.get(f"{creds['jira_url']}/rest/api/3/myself",
                                    auth=(creds["email"], creds["api_token"]),
                                    headers={"Accept":"application/json"}, timeout=10)
                        if r.status_code == 200:
                            u = r.json()
                            st.success(f"✅ Connected as **{u.get('displayName','?')}**")
                        else:
                            st.error(f"❌ HTTP {r.status_code}: {r.text[:150]}")
                    except Exception as e:
                        st.error(f"❌ {e}")

with tab2:
    st.subheader("Default Board Settings")
    col1, col2 = st.columns(2)
    with col1:
        board_id = st.number_input("Default Board ID",
            value=int(st.session_state.get("board_id", 34)),
            min_value=1, step=1,
            help="Number from your board URL: /boards/34 → 34")
        project_key = st.text_input("Project Key",
            value=st.session_state.get("project_key","AES"),
            placeholder="AES")
    with col2:
        sprint_prefix = st.text_input("Sprint Name Prefix",
            value=st.session_state.get("sprint_prefix","AES Sprint"),
            placeholder="AES Sprint")
        duration_days = st.selectbox("Default Sprint Duration",
            options=[7,14,21,28],
            index=1,
            format_func=lambda x: f"{x} days ({x//7} week{'s' if x>7 else ''})")

    sp_fields = st.text_input("Story Points Custom Fields (comma-separated)",
        value=st.session_state.get("story_points_fields","customfield_10016, customfield_10026, customfield_10004"),
        help="Jira custom field IDs for story points. Add yours if velocity shows 0.")

    if st.button("💾 Save Board Settings", type="primary"):
        st.session_state["board_id"]            = int(board_id)
        st.session_state["project_key"]         = project_key.strip().upper()
        st.session_state["sprint_prefix"]       = sprint_prefix.strip()
        st.session_state["duration_days"]       = duration_days
        st.session_state["story_points_fields"] = sp_fields.strip()
        st.success("✅ Board settings saved to session.")

with tab3:
    st.subheader("AI / Claude Settings")
    st.info("The Claude API key enables the AI Chatbot page. It is stored in session memory only.")
    akey = st.text_input("Anthropic API Key",
        value=st.session_state.get("anthropic_api_key",""),
        type="password", placeholder="sk-ant-...")
    if st.button("💾 Save AI Key", type="primary"):
        st.session_state["anthropic_api_key"] = akey.strip()
        st.success("✅ AI key saved.")
    st.markdown("[🔗 Get an Anthropic API Key](https://console.anthropic.com/api-keys)")
