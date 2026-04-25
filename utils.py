"""Shared helpers for the SprintSynergy Streamlit app.

Keeps Jira credentials in st.session_state so every page can read/write
them without touching disk. Optionally persists them to config.ini for
local-only use.
"""
from __future__ import annotations
import configparser, os
from typing import Any
import streamlit as st
import ss_lib

CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
_DEFAULT_BOARD_ID = 34
_DEFAULT_PROJECT  = "AES"

def init_state() -> None:
    if st.session_state.get("_ss_inited"):
        return
    cfg = ss_lib._load_config()
    st.session_state.setdefault("jira_url",   cfg.get("jira_url",""))
    st.session_state.setdefault("email",      cfg.get("email",""))
    st.session_state.setdefault("api_token",  cfg.get("api_token",""))
    st.session_state.setdefault("story_points_fields",
        ", ".join(cfg.get("story_points_fields", ss_lib.DEFAULT_STORY_POINT_FIELDS)))
    st.session_state.setdefault("board_id",      _DEFAULT_BOARD_ID)
    st.session_state.setdefault("project_key",   _DEFAULT_PROJECT)
    st.session_state.setdefault("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY",""))
    st.session_state["_ss_inited"] = True

def get_creds() -> dict[str, Any]:
    return {
        "jira_url":  st.session_state.get("jira_url","").strip(),
        "email":     st.session_state.get("email","").strip(),
        "api_token": st.session_state.get("api_token","").strip(),
    }

def creds_ready() -> bool:
    c = get_creds()
    return bool(c["jira_url"] and c["email"] and c["api_token"])

def require_creds() -> bool:
    if creds_ready():
        return True
    st.warning("Jira credentials are not set. Open the **🔧 Configuration** page "
               "and fill them in to start using this page.", icon="🔐")
    return False

def apply_story_point_fields() -> None:
    raw    = st.session_state.get("story_points_fields","")
    fields = [f.strip() for f in raw.split(",") if f.strip()]
    if fields:
        ss_lib.STORY_POINTS_FIELDS = fields

def save_config_to_disk() -> str:
    cp = configparser.ConfigParser()
    cp["jira"] = {
        "jira_url":  st.session_state.get("jira_url","").strip(),
        "email":     st.session_state.get("email","").strip(),
        "api_token": st.session_state.get("api_token","").strip(),
    }
    cp["story_points"] = {
        "fields": st.session_state.get("story_points_fields",
                  ", ".join(ss_lib.DEFAULT_STORY_POINT_FIELDS)),
    }
    with open(CFG_PATH,"w",encoding="utf-8") as f:
        cp.write(f)
    ss_lib.CONFIG = ss_lib._load_config()
    return CFG_PATH

def render_sidebar_status() -> None:
    with st.sidebar:
        st.markdown("### Connection")
        if creds_ready():
            host = st.session_state["jira_url"].replace("https://","").replace("http://","")
            st.success(f"Connected:\n`{host}`")
            st.caption(f"Email: `{st.session_state['email']}`")
            st.caption(f"Board: `{st.session_state['board_id']}`")
        else:
            st.error("Not configured")
        st.markdown("---")

def show_result(result: dict, success_msg: str | None = None) -> None:
    if not isinstance(result,dict):
        st.write(result); return
    if result.get("ok"):
        if success_msg: st.success(success_msg)
        st.json(result,expanded=False)
    else:
        st.error(result.get("error","Unknown error"))
        with st.expander("Full response"):
            st.json(result)
