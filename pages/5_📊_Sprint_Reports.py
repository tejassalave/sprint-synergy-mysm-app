"""SprintSynergy — Sprint Reports Page"""
import streamlit as st
from utils import init_state, render_sidebar_status, require_creds, get_creds
import ss_lib

st.set_page_config(page_title="Sprint Reports", page_icon="📊", layout="wide")
init_state(); render_sidebar_status()
st.title("📊 Sprint Reports")
st.caption("Per-sprint completion stats and multi-sprint velocity trend.")
st.divider()
if not require_creds(): st.stop()
creds    = get_creds()
board_id = st.session_state.get("board_id", 34)

tab1, tab2 = st.tabs(["📋 Sprint Report","📈 Velocity Trend"])

with tab1:
    st.subheader("Sprint Report")
    col1, col2 = st.columns([1,3])
    with col1:
        sr_id = st.number_input("Sprint ID", min_value=1, key="sr_id")
        run   = st.button("📊 Generate Report", type="primary")
    if run:
        with st.spinner("Generating report..."):
            res = ss_lib.sprint_report(int(sr_id), creds=creds)
        if res["ok"]:
            st.subheader(f"📋 {res['sprint_name']} — {res['state'].title()}")
            st.caption(f"Start: {res['start_date']}  →  End: {res['end_date']}")
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total Issues",     res["total_issues"])
            c2.metric("Completed",        res["completed_issues"])
            c3.metric("Completion Rate",  f"{res['completion_rate']}%")
            c4.metric("Velocity (SP)",    res["velocity"])
            cc1,cc2 = st.columns(2)
            cc1.metric("Committed SP",    res["committed_points"])
            cc2.metric("Completed SP",    res["completed_points"])
            if res.get("type_breakdown"):
                st.subheader("Issue Type Breakdown")
                import pandas as pd
                df_types = pd.DataFrame(list(res["type_breakdown"].items()),columns=["Type","Count"])
                st.bar_chart(df_types.set_index("Type"))
            if res.get("issues"):
                st.subheader("Issue Detail")
                import pandas as pd
                df = pd.DataFrame([{k:v for k,v in i.items() if k!="summary"} for i in res["issues"]])
                df["summary"] = [i["summary"][:70] for i in res["issues"]]
                st.dataframe(df, use_container_width=True)
        else:
            st.error(res.get("error"))

with tab2:
    st.subheader("Velocity Trend")
    col1, col2 = st.columns([1,3])
    with col1:
        vt_board  = st.number_input("Board ID", value=board_id, min_value=1, key="vt_board")
        vt_last_n = st.number_input("Last N sprints", value=5, min_value=2, max_value=20, key="vt_n")
        run_vt    = st.button("📈 Load Trend", type="primary")
    if run_vt:
        with st.spinner("Loading velocity data..."):
            res = ss_lib.velocity_trend(int(vt_board), last_n=int(vt_last_n), creds=creds)
        if res["ok"] and res.get("sprints"):
            sprints = res["sprints"]
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Average Velocity", res["average_velocity"])
            c2.metric("Highest",          res["highest_velocity"])
            c3.metric("Lowest",           res["lowest_velocity"])
            trend_icon = "📈" if res["trend"]=="up" else ("📉" if res["trend"]=="down" else "➡️")
            c4.metric("Trend", f"{trend_icon} {res['trend'].title()} ({res.get('trend_delta',0):+.1f})")
            import pandas as pd
            df = pd.DataFrame(sprints)
            st.subheader("Velocity Chart")
            st.bar_chart(df.set_index("name")[["committed_points","completed_points"]])
            st.subheader("Completion Rate Chart")
            st.line_chart(df.set_index("name")["completion_rate"])
            st.subheader("Sprint Table")
            st.dataframe(df[["name","end_date","total","completed","velocity","completion_rate"]],
                         use_container_width=True)
        elif res["ok"]:
            st.info("No closed sprints found on this board yet.")
        else:
            st.error(res.get("error"))
