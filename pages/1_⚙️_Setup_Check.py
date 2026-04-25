"""SprintSynergy — Setup Check Page"""
import sys, importlib, streamlit as st
from utils import init_state, render_sidebar_status, get_creds

st.set_page_config(page_title="Setup Check", page_icon="⚙️", layout="wide")
init_state()
render_sidebar_status()

st.title("⚙️ Setup Check")
st.caption("Verify your environment before using SprintSynergy.")
st.divider()

# ── Python version ─────────────────────────────────────────
st.subheader("1. Python Version")
major, minor = sys.version_info[:2]
if major == 3 and minor >= 10:
    st.success(f"✅ Python {major}.{minor} — OK (3.10+ required)")
else:
    st.error(f"❌ Python {major}.{minor} — upgrade to 3.10 or newer")

# ── Required packages ──────────────────────────────────────
st.subheader("2. Required Packages")
PACKAGES = ["streamlit","requests","pandas","anthropic","fastapi","uvicorn","dotenv"]
cols = st.columns(4)
for i, pkg in enumerate(PACKAGES):
    name = "python_dotenv" if pkg == "dotenv" else pkg
    with cols[i % 4]:
        try:
            importlib.import_module(name)
            st.success(f"✅ {pkg}")
        except ImportError:
            st.error(f"❌ {pkg}")
st.caption("Run `pip install -r requirements.txt` to install any missing packages.")

# ── Credentials ────────────────────────────────────────────
st.subheader("3. Credentials")
creds = get_creds()
c1, c2, c3 = st.columns(3)
with c1:
    if creds.get("jira_url"):
        st.success(f"✅ Jira URL\n`{creds['jira_url']}`")
    else:
        st.error("❌ Jira URL not set")
with c2:
    if creds.get("email"):
        st.success(f"✅ Email\n`{creds['email']}`")
    else:
        st.error("❌ Email not set")
with c3:
    if creds.get("api_token"):
        st.success("✅ API Token set")
    else:
        st.error("❌ API Token not set")

# ── Jira connection test ───────────────────────────────────
st.subheader("4. Jira Connection Test")
if not all(creds.values()):
    st.warning("⚠️ Fill in credentials on the **🔧 Configuration** page first.")
else:
    if st.button("🔌 Test Jira Connection", type="primary"):
        import requests as req
        with st.spinner("Connecting to Jira..."):
            try:
                r = req.get(
                    f"{creds['jira_url']}/rest/api/3/myself",
                    auth=(creds["email"], creds["api_token"]),
                    headers={"Accept": "application/json"}, timeout=10)
                if r.status_code == 200:
                    user = r.json()
                    st.success(f"✅ Connected as **{user.get('displayName','?')}** ({user.get('emailAddress','?')})")
                else:
                    st.error(f"❌ Connection failed — HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                st.error(f"❌ Connection error: {e}")

# ── AI key check ───────────────────────────────────────────
st.subheader("5. Claude AI Key")
import os
akey = st.session_state.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY","")
if akey and akey.startswith("sk-ant"):
    st.success("✅ Anthropic API key is set — AI Chatbot will work")
else:
    st.warning("⚠️ Anthropic API key not set — AI Chatbot page will be disabled. Set it in 🔧 Configuration.")

st.divider()
st.info("If all 5 checks are green — you're ready. Open **📅 Sprint Management** to get started.")
