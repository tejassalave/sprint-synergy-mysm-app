"""SprintSynergy — SAFe Metrics Page"""
import streamlit as st
from utils import init_state, render_sidebar_status, require_creds, get_creds
import ss_metrics

st.set_page_config(page_title="SAFe Metrics", page_icon="🚀", layout="wide")
init_state(); render_sidebar_status()
st.title("🚀 SAFe Metrics")
st.caption("PI Predictability, PI Velocity, Flow Metrics, Feature Progress, and Program Dashboard.")
st.divider()
if not require_creds(): st.stop()
creds    = get_creds()
board_id = st.session_state.get("board_id", 34)
proj     = st.session_state.get("project_key","AES")

tabs = st.tabs(["🎯 PI Predictability","⚡ PI Velocity","🌊 Flow Metrics","🗺️ Feature Progress","📊 Program Dashboard"])

with tabs[0]:
    st.subheader("PI Predictability")
    st.caption("Average ratio of completed vs committed story points across the last PI. SAFe target: 80–100%")
    col1,_ = st.columns([1,3])
    with col1:
        pp_board = st.number_input("Board ID", value=board_id, key="pp_board")
        pp_spi   = st.number_input("Sprints per PI", value=5, min_value=2, key="pp_spi")
        run = st.button("Calculate", type="primary", key="pp_run")
    if run:
        with st.spinner():
            res = ss_metrics.safe_pi_predictability(int(pp_board), sprints_per_pi=int(pp_spi), creds=creds)
        if res.get("ok"):
            val = res.get("program_predictability_pct",0)
            c1,c2,c3 = st.columns(3)
            c1.metric("PI Predictability", f"{val}%",
                      delta="✅ On target" if val>=80 else "⚠️ Below 80% target")
            c2.metric("Sprints Analysed", res.get("sprint_count","?"))
            c3.metric("Avg Say-Do/Sprint", f"{res.get('avg_say_do_pct','?')}%")
        else:
            st.error(res.get("error"))

with tabs[1]:
    st.subheader("PI Velocity")
    st.caption("Total story points delivered across the last Program Increment.")
    col1,_ = st.columns([1,3])
    with col1:
        pv_board = st.number_input("Board ID", value=board_id, key="pv_board")
        pv_spi   = st.number_input("Sprints per PI", value=5, min_value=2, key="pv_spi")
        run = st.button("Calculate", type="primary", key="pv_run")
    if run:
        with st.spinner():
            res = ss_metrics.safe_pi_velocity(int(pv_board), sprints_per_pi=int(pv_spi), creds=creds)
        if res.get("ok"):
            c1,c2,c3 = st.columns(3)
            c1.metric("PI Total Velocity",     res.get("total_completed_points","?"))
            c2.metric("Avg Points / Sprint",   res.get("avg_points_per_sprint","?"))
            c3.metric("Sprints in PI",         res.get("sprint_count","?"))
            if res.get("sprints"):
                import pandas as pd
                df = pd.DataFrame(res["sprints"])
                if not df.empty and "name" in df.columns:
                    st.bar_chart(df.set_index("name")["completed_points"])
        else:
            st.error(res.get("error"))

with tabs[2]:
    st.subheader("Flow Metrics")
    st.caption("Flow Velocity, Flow Time, Flow Load (WIP), Flow Efficiency, and Flow Distribution.")
    col1,_ = st.columns([1,3])
    with col1:
        fm_board = st.number_input("Board ID", value=board_id, key="fm_board")
        fm_n     = st.number_input("Last N sprints", value=5, min_value=2, key="fm_n")
        run = st.button("Calculate", type="primary", key="fm_run")
    if run:
        with st.spinner():
            res = ss_metrics.safe_flow_metrics(int(fm_board), last_n=int(fm_n), creds=creds)
        if res.get("ok"):
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Flow Velocity",    res.get("flow_velocity","?"))
            c2.metric("Flow Time (days)", res.get("flow_time_days","?"))
            c3.metric("Flow Load (WIP)",  res.get("flow_load","?"))
            c4.metric("Flow Efficiency",  f"{res.get('flow_efficiency_pct','?')}%")
            if res.get("flow_distribution"):
                st.subheader("Flow Distribution")
                import pandas as pd
                dist = res["flow_distribution"]
                df_dist = pd.DataFrame(list(dist.items()), columns=["Type","Count"])
                st.bar_chart(df_dist.set_index("Type"))
        else:
            st.error(res.get("error"))

with tabs[3]:
    st.subheader("Feature / Epic Progress")
    st.caption("Completion status of all features and epics across the board.")
    col1,_ = st.columns([1,3])
    with col1:
        fp_board = st.number_input("Board ID", value=board_id, key="fp_board")
        run = st.button("Load Progress", type="primary", key="fp_run")
    if run:
        with st.spinner():
            res = ss_metrics.safe_feature_progress(int(fp_board), creds=creds)
        if res.get("ok"):
            features = res.get("features",[])
            c1,c2 = st.columns(2)
            c1.metric("Features Tracked", len(features))
            c2.metric("Avg Completion",   f"{res.get('avg_completion_pct','?')}%")
            if features:
                import pandas as pd
                df = pd.DataFrame(features)
                if not df.empty:
                    cols_show = [c for c in ["key","summary","completion_pct","done","total"] if c in df.columns]
                    st.dataframe(df[cols_show], use_container_width=True)
        else:
            st.error(res.get("error"))

with tabs[4]:
    st.subheader("SAFe Program Dashboard")
    st.caption("One-call summary: PI Predictability + PI Velocity + Flow Metrics + Feature Progress.")
    col1,_ = st.columns([1,3])
    with col1:
        pd_board = st.number_input("Board ID", value=board_id, key="pd_board")
        pd_spi   = st.number_input("Sprints per PI", value=5, min_value=2, key="pd_spi")
        run = st.button("🚀 Load Dashboard", type="primary", key="pd_run")
    if run:
        with st.spinner("Loading program dashboard..."):
            res = ss_metrics.safe_program_dashboard(int(pd_board), sprints_per_pi=int(pd_spi), creds=creds)
        if res.get("ok"):
            pp  = res.get("predictability") or {}
            vel = res.get("velocity") or {}
            flw = res.get("flow") or {}
            ft  = res.get("features") or {}
            st.subheader("Program Health Summary")
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("PI Predictability",  f"{pp.get('program_predictability_pct','?')}%")
            c2.metric("PI Total Velocity",  vel.get("total_completed_points","?"))
            c3.metric("Flow Efficiency",    f"{flw.get('flow_efficiency_pct','?')}%")
            c4.metric("Features Tracked",   len((ft or {}).get("features",[])))
            cc1,cc2,cc3 = st.columns(3)
            cc1.metric("Avg SP / Sprint",   vel.get("avg_points_per_sprint","?"))
            cc2.metric("Flow Velocity",     flw.get("flow_velocity","?"))
            cc3.metric("Flow Load (WIP)",   flw.get("flow_load","?"))
        else:
            st.error(res.get("error"))
