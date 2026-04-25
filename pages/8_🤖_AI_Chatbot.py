"""SprintSynergy — AI Chatbot Page"""
import json, os
import streamlit as st
from utils import init_state, render_sidebar_status, get_creds

st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="wide")
init_state(); render_sidebar_status()
st.title("🤖 AI Chatbot")
st.caption("Chat with Claude to manage your sprints using all 24 SprintSynergy tools.")
st.divider()

# ── Check keys ────────────────────────────────────────────
akey = st.session_state.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY","")
if not akey:
    st.warning("⚠️ Anthropic API key not set. Go to **🔧 Configuration → AI Settings** and add your key.")
    st.stop()

creds = get_creds()
if not all(creds.values()):
    st.warning("⚠️ Jira credentials not set. Go to **🔧 Configuration** first.")
    st.stop()

# ── Init chat history ──────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# ── Sidebar controls ───────────────────────────────────────
with st.sidebar:
    st.markdown("### AI Settings")
    board_id = st.number_input("Default Board ID",
        value=st.session_state.get("board_id",34), key="chat_board")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_messages = []
        st.rerun()
    st.markdown("---")
    st.markdown("**Example questions:**")
    examples = [
        "Show velocity trend for board 34 last 5 sprints",
        "Create 3 sprints on board 34 starting 2026-06-01",
        "What is the Say-Do ratio for board 34?",
        "List all active sprints on board 34",
        "Run the SAFe program dashboard for board 34",
    ]
    for ex in examples:
        if st.button(f"💬 {ex[:45]}...", key=f"ex_{ex[:20]}", use_container_width=True):
            st.session_state.chat_messages.append({"role":"user","content":ex})
            st.rerun()

# ── Render chat history ────────────────────────────────────
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], list):
            for block in msg["content"]:
                if hasattr(block,"type") and block.type == "text":
                    st.markdown(block.text)
        else:
            st.markdown(str(msg["content"]))

# ── Chat input ─────────────────────────────────────────────
user_input = st.chat_input("Ask Claude to manage your sprints...")

if user_input:
    st.session_state.chat_messages.append({"role":"user","content":user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Claude is thinking..."):
            try:
                import anthropic
                from ss_ai import CLAUDE_TOOLS, dispatch_tool

                client = anthropic.Anthropic(api_key=akey)
                messages = [m for m in st.session_state.chat_messages if isinstance(m["content"], str)]

                # Agentic loop
                max_rounds = 8
                for _ in range(max_rounds):
                    resp = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=2048,
                        system=(
                            "You are SprintSynergy AI — an expert Agile coach and Jira automation assistant. "
                            f"Default board_id is {board_id}. "
                            "Use the available tools to answer questions and take actions. "
                            "Always confirm what you did and show key results clearly. "
                            "If creds are needed, they are already injected by the platform."
                        ),
                        tools=CLAUDE_TOOLS,
                        messages=messages,
                    )

                    messages.append({"role":"assistant","content":resp.content})

                    if resp.stop_reason != "tool_use":
                        break

                    tool_results = []
                    for block in resp.content:
                        if block.type == "tool_use":
                            with st.spinner(f"Running tool: {block.name}..."):
                                result = dispatch_tool(block.name, block.input, creds=creds)
                            tool_results.append({
                                "type":        "tool_result",
                                "tool_use_id": block.id,
                                "content":     json.dumps(result),
                            })
                    messages.append({"role":"user","content":tool_results})

                # Show final text response
                final_text = ""
                for block in resp.content:
                    if hasattr(block,"type") and block.type == "text":
                        final_text += block.text
                if final_text:
                    st.markdown(final_text)
                    st.session_state.chat_messages.append({"role":"assistant","content":final_text})
                else:
                    st.info("Tool executed. No text summary returned.")

            except Exception as e:
                err_msg = f"❌ Error: {e}"
                st.error(err_msg)
                st.session_state.chat_messages.append({"role":"assistant","content":err_msg})
