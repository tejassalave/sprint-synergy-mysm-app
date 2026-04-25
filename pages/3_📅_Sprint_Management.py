"""SprintSynergy — Sprint Management Page"""
import streamlit as st
from utils import init_state, render_sidebar_status, require_creds, get_creds, show_result
import ss_lib

st.set_page_config(page_title="Sprint Management", page_icon="📅", layout="wide")
init_state()
render_sidebar_status()
st.title("📅 Sprint Management")
st.caption("Create, rename, start, close, and delete sprints on any Jira board.")
st.divider()
if not require_creds(): st.stop()

creds    = get_creds()
board_id = st.session_state.get("board_id", 34)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 List Sprints","➕ Create Sprint","🔁 Create Sprint Series","✏️ Rename/Delete","▶️ Start / Close"])

# ── Tab 1: List ────────────────────────────────────────────
with tab1:
    st.subheader("List Sprints")
    col1, col2 = st.columns(2)
    with col1:
        bid   = st.number_input("Board ID", value=board_id, min_value=1, key="ls_board")
        state = st.selectbox("State", ["all","active","closed","future"], key="ls_state")
    if st.button("🔍 List Sprints", type="primary"):
        with st.spinner("Fetching sprints..."):
            res = ss_lib.list_sprints(int(bid), state=None if state=="all" else state, creds=creds)
        if res["ok"]:
            sprints = res["sprints"]
            st.success(f"Found {len(sprints)} sprint(s)")
            if sprints:
                import pandas as pd
                df = pd.DataFrame([{
                    "ID": s.get("id"), "Name": s.get("name"),
                    "State": s.get("state",""),
                    "Start": (s.get("startDate") or "")[:10],
                    "End":   (s.get("endDate") or "")[:10],
                    "Goal":  (s.get("goal") or "")[:60]
                } for s in sprints])
                st.dataframe(df, use_container_width=True)
        else:
            st.error(res.get("error"))

# ── Tab 2: Create single sprint ────────────────────────────
with tab2:
    st.subheader("Create a Single Sprint")
    col1, col2 = st.columns(2)
    with col1:
        cs_board = st.number_input("Board ID", value=board_id, min_value=1, key="cs_board")
        cs_name  = st.text_input("Sprint Name", value=f"{st.session_state.get('sprint_prefix','AES Sprint')} 3", key="cs_name")
        cs_goal  = st.text_input("Sprint Goal (optional)", key="cs_goal")
    with col2:
        cs_start = st.date_input("Start Date", key="cs_start")
        cs_end   = st.date_input("End Date",   key="cs_end")
    if st.button("➕ Create Sprint", type="primary"):
        with st.spinner("Creating sprint..."):
            res = ss_lib.create_sprint(
                int(cs_board), cs_name,
                cs_start.strftime("%Y-%m-%d"), cs_end.strftime("%Y-%m-%d"),
                goal=cs_goal, creds=creds)
        show_result(res, f"✅ Sprint '{cs_name}' created!")

# ── Tab 3: Create series ───────────────────────────────────
with tab3:
    st.subheader("Create Sprint Series (multiple back-to-back sprints)")
    col1, col2 = st.columns(2)
    with col1:
        ser_board  = st.number_input("Board ID", value=board_id, min_value=1, key="ser_board")
        ser_prefix = st.text_input("Sprint Prefix", value=st.session_state.get("sprint_prefix","AES Sprint"), key="ser_prefix")
        ser_start  = st.date_input("First Sprint Start Date", key="ser_start")
        ser_num    = st.number_input("First Sprint Number", value=3, min_value=1, key="ser_num")
    with col2:
        ser_count  = st.number_input("Number of Sprints to Create", value=3, min_value=1, max_value=20, key="ser_count")
        ser_days   = st.selectbox("Sprint Duration", [7,14,21,28], index=1,
                                  format_func=lambda x: f"{x} days", key="ser_days")
        ser_goal   = st.text_input("Goal (applied to all sprints)", key="ser_goal")

    st.info(f"Will create: {ser_prefix} {ser_num} through {ser_prefix} {int(ser_num)+int(ser_count)-1}")
    if st.button("🚀 Create Sprint Series", type="primary"):
        with st.spinner(f"Creating {ser_count} sprints..."):
            res = ss_lib.create_sprint_series(
                int(ser_board), ser_prefix,
                ser_start.strftime("%Y-%m-%d"),
                int(ser_num), int(ser_count),
                duration_days=int(ser_days), goal=ser_goal, creds=creds)
        if res["ok"]:
            st.success(f"✅ Created {res['created']} of {res['total']} sprints.")
            for r in res["results"]:
                if r["ok"]: st.write(f"  ✅ {r['sprint']['name']}")
                else:       st.write(f"  ❌ {r.get('error','?')}")
        else:
            st.error(f"Partial failure — {res['created']}/{res['total']} created.")

# ── Tab 4: Rename / Delete ─────────────────────────────────
with tab4:
    st.subheader("Rename or Delete a Sprint")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Rename**")
        ren_id   = st.number_input("Sprint ID to rename", min_value=1, key="ren_id")
        ren_name = st.text_input("New name", key="ren_name")
        if st.button("✏️ Rename", type="primary"):
            res = ss_lib.rename_sprint(int(ren_id), ren_name, creds=creds)
            show_result(res, f"✅ Sprint {ren_id} renamed to '{ren_name}'")
    with col2:
        st.markdown("**Delete**")
        del_id = st.number_input("Sprint ID to delete", min_value=1, key="del_id")
        st.warning("⚠️ Deletion is permanent. Active sprints must be closed first.")
        if st.button("🗑️ Delete Sprint", type="secondary"):
            res = ss_lib.delete_sprint(int(del_id), creds=creds)
            show_result(res, f"✅ Sprint {del_id} deleted.")

# ── Tab 5: Start / Close ───────────────────────────────────
with tab5:
    st.subheader("Start or Close a Sprint")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Start a future sprint**")
        start_id = st.number_input("Sprint ID to start", min_value=1, key="start_id")
        if st.button("▶️ Start Sprint", type="primary"):
            res = ss_lib.start_sprint(int(start_id), creds=creds)
            show_result(res, f"✅ Sprint {start_id} is now Active.")
    with col2:
        st.markdown("**Close an active sprint**")
        close_id = st.number_input("Sprint ID to close", min_value=1, key="close_id")
        if st.button("⏹️ Close Sprint", type="secondary"):
            res = ss_lib.close_sprint(int(close_id), creds=creds)
            show_result(res, f"✅ Sprint {close_id} closed.")
