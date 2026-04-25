"""SprintSynergy — Issues and Validation Page"""
import streamlit as st
from utils import init_state, render_sidebar_status, require_creds, get_creds, show_result
import ss_lib

st.set_page_config(page_title="Issues & Validation", page_icon="📋", layout="wide")
init_state(); render_sidebar_status()
st.title("📋 Issues & Validation")
st.caption("List sprint issues, move issues between sprints, and validate before closing.")
st.divider()
if not require_creds(): st.stop()
creds = get_creds()

tab1, tab2, tab3 = st.tabs(["📄 List Issues","➡️ Move Issues","✅ Validate & Close"])

with tab1:
    st.subheader("List Sprint Issues")
    col1, col2 = st.columns(2)
    with col1:
        li_sprint = st.number_input("Sprint ID", min_value=1, key="li_sprint")
        li_extra  = st.checkbox("Include extra fields (assignee, dates)", key="li_extra")
    if st.button("🔍 List Issues", type="primary"):
        with st.spinner("Fetching issues..."):
            res = ss_lib.list_sprint_issues(int(li_sprint), extra_fields=li_extra, creds=creds)
        if res["ok"]:
            issues = res["issues"]
            st.success(f"Found {len(issues)} issue(s)")
            if issues:
                import pandas as pd
                rows = []
                for it in issues:
                    f = it.get("fields",{})
                    row = {"Key": it.get("key",""),
                           "Type": (f.get("issuetype") or {}).get("name",""),
                           "Status": (f.get("status") or {}).get("name",""),
                           "Summary": f.get("summary","")[:80]}
                    if li_extra:
                        row["Assignee"] = (f.get("assignee") or {}).get("displayName","Unassigned")
                    rows.append(row)
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.error(res.get("error"))

with tab2:
    st.subheader("Move Issues to Another Sprint")
    col1, col2 = st.columns(2)
    with col1:
        mv_target = st.number_input("Target Sprint ID", min_value=1, key="mv_target")
    with col2:
        mv_keys_raw = st.text_area("Issue Keys (one per line or comma-separated)",
            placeholder="AES-12\nAES-13\nAES-14", key="mv_keys")
    if st.button("➡️ Move Issues", type="primary"):
        keys = [k.strip() for k in mv_keys_raw.replace(",","\n").split("\n") if k.strip()]
        if not keys:
            st.warning("Enter at least one issue key.")
        else:
            with st.spinner(f"Moving {len(keys)} issues..."):
                res = ss_lib.move_issues_to_sprint(int(mv_target), keys, creds=creds)
            show_result(res, f"✅ Moved {res.get('moved',0)} issues to Sprint {mv_target}.")

with tab3:
    st.subheader("Validate Sprint Before Closing")
    col1, col2, col3 = st.columns(3)
    with col1:
        val_sprint = st.number_input("Sprint ID to validate", min_value=1, key="val_sprint")
    with col2:
        val_target = st.number_input("Move open issues to Sprint ID (optional)", min_value=0, key="val_target")
    with col3:
        val_force = st.checkbox("Force close even if open issues remain", key="val_force")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔍 Validate Only", use_container_width=True):
            with st.spinner("Validating..."):
                res = ss_lib.validate_sprint(int(val_sprint), creds=creds)
            if res["ok"]:
                if res["ready_to_close"]:
                    st.success(f"✅ Sprint is ready to close — all {res['total']} issues are Done.")
                else:
                    st.warning(f"⚠️ {res['open_count']} open issues, {res['done_count']} done.")
                    import pandas as pd
                    if res["open_issues"]:
                        st.dataframe(pd.DataFrame(res["open_issues"]), use_container_width=True)
            else:
                st.error(res.get("error"))
    with col_b:
        if st.button("✅ Validate & Close", type="primary", use_container_width=True):
            with st.spinner("Validating and closing..."):
                res = ss_lib.validate_and_close_sprint(
                    int(val_sprint),
                    target_sprint_id=int(val_target) if val_target else None,
                    force=val_force, creds=creds)
            action = res.get("action","?")
            if action in ("closed","moved_then_closed","force_closed"):
                st.success(f"✅ Action: {action}. Sprint {val_sprint} is now closed.")
            elif action == "blocked":
                st.warning(f"⚠️ Blocked: {res.get('message','?')}")
            else:
                show_result(res)
