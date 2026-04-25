"""SprintSynergy — Scrum Metrics Page"""
import streamlit as st
from utils import init_state, render_sidebar_status, require_creds, get_creds
import ss_metrics

st.set_page_config(page_title="Scrum Metrics", page_icon="📈", layout="wide")
init_state(); render_sidebar_status()
st.title("📈 Scrum Metrics")
st.caption("Say-Do ratio, throughput, cycle time, defect ratio, goal success, and burndown.")
st.divider()
if not require_creds(): st.stop()
creds    = get_creds()
board_id = st.session_state.get("board_id", 34)

def _metric_card(res, key, label, suffix="", good_above=None, good_below=None):
    if not res.get("ok"):
        st.error(res.get("error","Error")); return
    val = res.get(key)
    if val is None:
        st.warning(f"{label}: no data"); return
    delta = None
    if good_above and isinstance(val,(int,float)):
        delta = "✅ Good" if val >= good_above else f"⚠️ Below target ({good_above}{suffix})"
    st.metric(label, f"{val}{suffix}", delta=delta)

tabs = st.tabs(["🎯 Say-Do","📦 Throughput","⏱️ Cycle Time","🐛 Defect Ratio","🏁 Goal Success","🔥 Burndown"])

with tabs[0]:
    st.subheader("Commitment Reliability (Say-Do Ratio)")
    st.caption("Measures whether the team completes what they committed to. Target: 80–100%")
    col1,_ = st.columns([1,3])
    with col1:
        sd_board = st.number_input("Board ID", value=board_id, key="sd_board")
        sd_n     = st.number_input("Last N sprints", value=5, min_value=1, key="sd_n")
        run = st.button("Calculate Say-Do", type="primary", key="sd_run")
    if run:
        with st.spinner("Calculating..."):
            res = ss_metrics.scrum_commitment_reliability(int(sd_board), last_n=int(sd_n), creds=creds)
        if res.get("ok"):
            c1,c2,c3 = st.columns(3)
            c1.metric("Say-Do Ratio", f"{res.get('say_do_ratio_pct','?')}%",
                      delta="✅ Good" if (res.get('say_do_ratio_pct') or 0)>=80 else "⚠️ Below target 80%")
            c2.metric("Committed SP", res.get("total_committed_points","?"))
            c3.metric("Completed SP", res.get("total_completed_points","?"))
        else:
            st.error(res.get("error"))

with tabs[1]:
    st.subheader("Sprint Throughput")
    st.caption("Number of issues completed per sprint over the last N sprints.")
    col1,_ = st.columns([1,3])
    with col1:
        tp_board = st.number_input("Board ID", value=board_id, key="tp_board")
        tp_n     = st.number_input("Last N sprints", value=5, min_value=1, key="tp_n")
        run = st.button("Calculate Throughput", type="primary", key="tp_run")
    if run:
        with st.spinner("Calculating..."):
            res = ss_metrics.scrum_throughput(int(tp_board), last_n=int(tp_n), creds=creds)
        if res.get("ok"):
            c1,c2,c3 = st.columns(3)
            c1.metric("Avg Throughput/Sprint", res.get("avg_throughput","?"))
            c2.metric("Total Issues Completed", res.get("total_completed","?"))
            c3.metric("Sprints Analysed", res.get("sprint_count","?"))
            if res.get("per_sprint"):
                import pandas as pd
                df = pd.DataFrame(res["per_sprint"])
                if not df.empty:
                    st.bar_chart(df.set_index("name")["completed"])
        else:
            st.error(res.get("error"))

with tabs[2]:
    st.subheader("Cycle Time")
    st.caption("Average, median, and P85 days from issue created to resolved in a sprint.")
    col1,_ = st.columns([1,3])
    with col1:
        ct_sprint = st.number_input("Sprint ID", min_value=1, key="ct_sprint")
        run = st.button("Calculate Cycle Time", type="primary", key="ct_run")
    if run:
        with st.spinner("Calculating..."):
            res = ss_metrics.scrum_cycle_time(int(ct_sprint), creds=creds)
        if res.get("ok"):
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Issues Measured", res.get("issues_measured","?"))
            c2.metric("Avg Cycle Time",  f"{res.get('avg_days','?')} days")
            c3.metric("Median",          f"{res.get('median_days','?')} days")
            c4.metric("P85",             f"{res.get('p85_days','?')} days")
        else:
            st.error(res.get("error"))

with tabs[3]:
    st.subheader("Defect Ratio")
    st.caption("Percentage of issues that are bugs across the last N sprints.")
    col1,_ = st.columns([1,3])
    with col1:
        dr_board = st.number_input("Board ID", value=board_id, key="dr_board")
        dr_n     = st.number_input("Last N sprints", value=5, min_value=1, key="dr_n")
        run = st.button("Calculate Defect Ratio", type="primary", key="dr_run")
    if run:
        with st.spinner("Calculating..."):
            res = ss_metrics.scrum_defect_ratio(int(dr_board), last_n=int(dr_n), creds=creds)
        if res.get("ok"):
            c1,c2,c3 = st.columns(3)
            c1.metric("Defect Ratio", f"{res.get('defect_ratio_pct','?')}%",
                      delta="✅ Low" if (res.get('defect_ratio_pct') or 100) < 20 else "⚠️ High defect rate")
            c2.metric("Total Bugs",   res.get("total_bugs","?"))
            c3.metric("Total Issues", res.get("total_issues","?"))
        else:
            st.error(res.get("error"))

with tabs[4]:
    st.subheader("Sprint Goal Success Rate")
    st.caption("Percentage of sprints where completion rate ≥ 80%.")
    col1,_ = st.columns([1,3])
    with col1:
        gs_board = st.number_input("Board ID", value=board_id, key="gs_board")
        gs_n     = st.number_input("Last N sprints", value=5, min_value=1, key="gs_n")
        run = st.button("Calculate Goal Success", type="primary", key="gs_run")
    if run:
        with st.spinner("Calculating..."):
            res = ss_metrics.scrum_sprint_goal_success(int(gs_board), last_n=int(gs_n), creds=creds)
        if res.get("ok"):
            c1,c2,c3 = st.columns(3)
            c1.metric("Success Rate", f"{res.get('success_rate_pct','?')}%")
            c2.metric("Successful",   res.get("successful","?"))
            c3.metric("Total",        res.get("total","?"))
        else:
            st.error(res.get("error"))

with tabs[5]:
    st.subheader("Sprint Burndown Snapshot")
    st.caption("Total, burned, and remaining story points and issue counts for a sprint.")
    col1,_ = st.columns([1,3])
    with col1:
        bd_sprint = st.number_input("Sprint ID", min_value=1, key="bd_sprint")
        run = st.button("Get Burndown", type="primary", key="bd_run")
    if run:
        with st.spinner("Loading..."):
            res = ss_metrics.scrum_sprint_burndown(int(bd_sprint), creds=creds)
        if res.get("ok"):
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total SP",     res.get("total_points","?"))
            c2.metric("Burned SP",    res.get("burned_points","?"))
            c3.metric("Remaining SP", res.get("remaining_points","?"))
            c4.metric("% Burned",     f"{res.get('burned_pct','?')}%")
            cc1,cc2,cc3 = st.columns(3)
            cc1.metric("Total Issues",  res.get("total_issues","?"))
            cc2.metric("Done",          res.get("done_issues","?"))
            cc3.metric("Remaining",     res.get("remaining_issues","?"))
        else:
            st.error(res.get("error"))
