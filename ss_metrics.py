"""
Scrum + SAFe metrics for SprintSynergy.

Local folder:
    D:\\New Volume D Drive Backup\\Trainings_Skills\\AI Project Work\\
    Important Program\\Sprint Synergy Program\\Revised JIRA Config files

All metrics are computed from data we can pull from the Jira REST API
(sprints + issues + story points + status). Where a metric needs data
Jira doesn't natively expose (e.g. daily burndown points, business
value scoring per PI objective), we approximate or skip and clearly
flag it in the result.

Every function returns {"ok": True, ...} or {"ok": False, "error": ...}.
"""

from datetime import datetime
from ss_lib import (
    list_sprints, list_sprint_issues, sprint_report,
    _is_done, _story_points, DONE_STATUSES,
)


# ============================================================
#  Helpers
# ============================================================

def _parse_dt(s):
    if not s: return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None


def _days_between(a, b):
    if not a or not b: return None
    return round((b - a).total_seconds() / 86400, 2)


def _classify_type(name):
    n = (name or "").lower()
    if "bug" in n or "defect" in n: return "defect"
    if "story" in n: return "story"
    if "task" in n: return "task"
    if "epic" in n: return "epic"
    if "spike" in n or "research" in n: return "enabler"
    if "risk" in n: return "risk"
    if "debt" in n or "tech" in n: return "tech_debt"
    return "other"


# ============================================================
#  SCRUM METRICS
# ============================================================

def scrum_commitment_reliability(board_id, last_n=5, creds=None):
    """Say-Do Ratio: completed_points / committed_points across last N closed sprints.
    Industry healthy range: 80–100%."""
    res = list_sprints(board_id, state="closed", creds=creds)
    if not res["ok"]: return res
    closed = sorted(res["sprints"],
                    key=lambda s: s.get("completeDate") or s.get("endDate") or "")
    sel = closed[-last_n:]
    rows = []
    tot_cmt = tot_done = 0.0
    for s in sel:
        rep = sprint_report(s["id"], creds=creds)
        if not rep["ok"]: continue
        ratio = (rep["completed_points"] / rep["committed_points"] * 100
                 if rep["committed_points"] else 0)
        rows.append({
            "sprint": rep["sprint_name"],
            "committed_points": rep["committed_points"],
            "completed_points": rep["completed_points"],
            "say_do_ratio_pct": round(ratio, 1),
        })
        tot_cmt += rep["committed_points"]
        tot_done += rep["completed_points"]
    overall = round(tot_done / tot_cmt * 100, 1) if tot_cmt else 0.0
    health = ("healthy" if 80 <= overall <= 110
              else "under-committing" if overall > 110
              else "over-committing")
    return {"ok": True, "sprints": rows, "overall_say_do_pct": overall,
            "health": health, "benchmark": "80–100% is healthy"}


def scrum_throughput(board_id, last_n=5, creds=None):
    """Throughput: # issues completed per sprint."""
    res = list_sprints(board_id, state="closed", creds=creds)
    if not res["ok"]: return res
    sel = sorted(res["sprints"],
                 key=lambda s: s.get("completeDate") or s.get("endDate") or "")[-last_n:]
    rows = []
    for s in sel:
        rep = sprint_report(s["id"], creds=creds)
        if not rep["ok"]: continue
        rows.append({"sprint": rep["sprint_name"],
                     "throughput": rep["completed_issues"],
                     "total_issues": rep["total_issues"]})
    if not rows:
        return {"ok": True, "sprints": [], "average_throughput": 0}
    avg = round(sum(r["throughput"] for r in rows) / len(rows), 1)
    return {"ok": True, "sprints": rows, "average_throughput": avg}


def scrum_cycle_time(sprint_id, creds=None):
    """Cycle time per completed issue = resolution - created (in days).
    Approximation: Jira doesn't expose 'In Progress' transition without changelog.
    Use this as lead time. Returns avg/median/p85."""
    res = list_sprint_issues(sprint_id, extra_fields=True, creds=creds)
    if not res["ok"]: return res
    times, items = [], []
    for it in res["issues"]:
        f = it.get("fields", {})
        if not _is_done(f): continue
        created = _parse_dt(f.get("created"))
        resolved = _parse_dt(f.get("resolutiondate"))
        d = _days_between(created, resolved)
        if d is None: continue
        times.append(d)
        items.append({"key": it.get("key"), "lead_time_days": d,
                      "summary": (f.get("summary") or "")[:80]})
    if not times:
        return {"ok": True, "count": 0, "note": "No completed issues with timestamps."}
    times_sorted = sorted(times)
    n = len(times_sorted)
    median = times_sorted[n//2] if n % 2 else (times_sorted[n//2-1]+times_sorted[n//2])/2
    p85 = times_sorted[min(n-1, int(0.85*n))]
    return {"ok": True, "count": n,
            "avg_lead_time_days":    round(sum(times)/n, 2),
            "median_lead_time_days": round(median, 2),
            "p85_lead_time_days":    round(p85, 2),
            "min_days": round(min(times), 2),
            "max_days": round(max(times), 2),
            "issues": items,
            "note": "Lead time = created→resolved. True cycle time needs workflow changelog."}


def scrum_defect_ratio(board_id, last_n=5, creds=None):
    """Defect ratio = bugs / total issues across last N sprints."""
    res = list_sprints(board_id, state="closed", creds=creds)
    if not res["ok"]: return res
    sel = sorted(res["sprints"],
                 key=lambda s: s.get("completeDate") or s.get("endDate") or "")[-last_n:]
    rows = []
    tot = bugs = 0
    for s in sel:
        rep = sprint_report(s["id"], creds=creds)
        if not rep["ok"]: continue
        b = sum(n for t, n in rep["type_breakdown"].items()
                if "bug" in t.lower() or "defect" in t.lower())
        rows.append({"sprint": rep["sprint_name"],
                     "total_issues": rep["total_issues"], "defects": b,
                     "defect_ratio_pct": round(b/rep["total_issues"]*100, 1)
                                          if rep["total_issues"] else 0})
        tot += rep["total_issues"]; bugs += b
    overall = round(bugs/tot*100, 1) if tot else 0.0
    return {"ok": True, "sprints": rows, "overall_defect_ratio_pct": overall,
            "total_defects": bugs, "total_issues": tot,
            "benchmark": "Below 15% is generally healthy"}


def scrum_sprint_goal_success(board_id, last_n=5, creds=None):
    """Sprint goal success rate: % of sprints with completion_rate >= 80%."""
    res = list_sprints(board_id, state="closed", creds=creds)
    if not res["ok"]: return res
    sel = sorted(res["sprints"],
                 key=lambda s: s.get("completeDate") or s.get("endDate") or "")[-last_n:]
    rows, success = [], 0
    for s in sel:
        rep = sprint_report(s["id"], creds=creds)
        if not rep["ok"]: continue
        ok = rep["completion_rate"] >= 80
        if ok: success += 1
        rows.append({"sprint": rep["sprint_name"], "goal": s.get("goal", ""),
                     "completion_rate": rep["completion_rate"],
                     "goal_met": ok})
    rate = round(success/len(rows)*100, 1) if rows else 0.0
    return {"ok": True, "sprints": rows, "success_rate_pct": rate,
            "successful": success, "total": len(rows),
            "definition": "Goal met if ≥80% of committed work completed"}


def scrum_sprint_burndown(sprint_id, creds=None):
    """Approximate burndown: shows current remaining work vs ideal.
    Note: True burndown needs daily snapshots; this is a point-in-time view."""
    res = list_sprint_issues(sprint_id, extra_fields=True, creds=creds)
    if not res["ok"]: return res
    total_pts = remaining_pts = 0.0
    total_cnt = remaining_cnt = 0
    for it in res["issues"]:
        f = it.get("fields", {})
        pts = _story_points(f)
        total_pts += pts; total_cnt += 1
        if not _is_done(f):
            remaining_pts += pts; remaining_cnt += 1
    burned = total_pts - remaining_pts
    pct = round(burned/total_pts*100, 1) if total_pts else 0.0
    return {"ok": True, "sprint_id": sprint_id,
            "total_points": round(total_pts, 1),
            "remaining_points": round(remaining_pts, 1),
            "burned_points": round(burned, 1),
            "burned_pct": pct,
            "total_issues": total_cnt,
            "remaining_issues": remaining_cnt,
            "note": "Snapshot only. True burndown chart needs daily history."}


# ============================================================
#  SAFe METRICS  (Program Increment scope = N sprints on the board)
# ============================================================

def safe_pi_predictability(board_id, sprints_per_pi=5, creds=None):
    """SAFe Program Predictability Measure (team-level proxy):
    avg(completed_points / committed_points) across the last PI's sprints.
    SAFe target: 80–100%."""
    res = list_sprints(board_id, state="closed", creds=creds)
    if not res["ok"]: return res
    sel = sorted(res["sprints"],
                 key=lambda s: s.get("completeDate") or s.get("endDate") or "")[-sprints_per_pi:]
    rows, ratios = [], []
    cmt_total = done_total = 0.0
    for s in sel:
        rep = sprint_report(s["id"], creds=creds)
        if not rep["ok"]: continue
        ratio = (rep["completed_points"]/rep["committed_points"]*100
                 if rep["committed_points"] else 0)
        ratios.append(ratio)
        cmt_total += rep["committed_points"]; done_total += rep["completed_points"]
        rows.append({"sprint": rep["sprint_name"],
                     "planned_pts": rep["committed_points"],
                     "actual_pts":  rep["completed_points"],
                     "ratio_pct":   round(ratio, 1)})
    pi_predictability = round(sum(ratios)/len(ratios), 1) if ratios else 0.0
    overall = round(done_total/cmt_total*100, 1) if cmt_total else 0.0
    rating = ("on-track" if 80 <= pi_predictability <= 110
              else "below-target" if pi_predictability < 80
              else "under-committing")
    return {"ok": True, "pi_sprint_count": len(rows), "iterations": rows,
            "pi_predictability_pct": pi_predictability,
            "pi_aggregate_ratio_pct": overall,
            "planned_total_pts": round(cmt_total, 1),
            "actual_total_pts":  round(done_total, 1),
            "rating": rating,
            "safe_benchmark": "80–100% is SAFe target"}


def safe_pi_velocity(board_id, sprints_per_pi=5, creds=None):
    """PI Velocity: sum of team velocity across PI sprints + average per iteration."""
    res = list_sprints(board_id, state="closed", creds=creds)
    if not res["ok"]: return res
    sel = sorted(res["sprints"],
                 key=lambda s: s.get("completeDate") or s.get("endDate") or "")[-sprints_per_pi:]
    rows, vels = [], []
    for s in sel:
        rep = sprint_report(s["id"], creds=creds)
        if not rep["ok"]: continue
        vels.append(rep["velocity"])
        rows.append({"sprint": rep["sprint_name"], "velocity": rep["velocity"]})
    return {"ok": True, "iterations": rows,
            "pi_velocity_total": round(sum(vels), 1),
            "average_iteration_velocity": round(sum(vels)/len(vels), 1) if vels else 0,
            "highest": max(vels) if vels else 0,
            "lowest":  min(vels) if vels else 0}


def safe_flow_metrics(board_id, last_n=5, creds=None):
    """SAFe / Flow Framework metrics across last N sprints:
       • Flow Velocity   — items completed per sprint
       • Flow Time       — avg lead time of completed items
       • Flow Load       — avg WIP (open items in active sprints)
       • Flow Efficiency — completed_pts / committed_pts (proxy)
       • Flow Distribution — % features / defects / enablers / debt / risks
    """
    res = list_sprints(board_id, state="closed", creds=creds)
    if not res["ok"]: return res
    sel = sorted(res["sprints"],
                 key=lambda s: s.get("completeDate") or s.get("endDate") or "")[-last_n:]
    flow_vel = []
    lead_times = []
    cmt_total = done_total = 0.0
    dist = {"feature": 0, "defect": 0, "enabler": 0, "tech_debt": 0,
            "risk": 0, "story": 0, "task": 0, "other": 0}
    wip_open = 0; wip_sprints = 0
    for s in sel:
        issues_res = list_sprint_issues(s["id"], extra_fields=True, creds=creds)
        if not issues_res["ok"]: continue
        completed = open_count = 0
        for it in issues_res["issues"]:
            f = it.get("fields", {})
            cls = _classify_type((f.get("issuetype") or {}).get("name"))
            if cls == "story": dist["feature"] += 1
            elif cls in dist: dist[cls] += 1
            else: dist["other"] += 1
            pts = _story_points(f)
            cmt_total += pts
            if _is_done(f):
                completed += 1; done_total += pts
                created = _parse_dt(f.get("created"))
                resolved = _parse_dt(f.get("resolutiondate"))
                d = _days_between(created, resolved)
                if d is not None: lead_times.append(d)
            else:
                open_count += 1
        flow_vel.append(completed)
        wip_open += open_count; wip_sprints += 1
    total_items = sum(dist.values()) or 1
    distribution_pct = {k: round(v/total_items*100, 1) for k, v in dist.items() if v}
    return {"ok": True,
            "flow_velocity_per_sprint": flow_vel,
            "average_flow_velocity": round(sum(flow_vel)/len(flow_vel), 1) if flow_vel else 0,
            "average_flow_time_days": round(sum(lead_times)/len(lead_times), 2) if lead_times else 0,
            "average_flow_load_wip": round(wip_open/wip_sprints, 1) if wip_sprints else 0,
            "flow_efficiency_pct":  round(done_total/cmt_total*100, 1) if cmt_total else 0,
            "flow_distribution_pct": distribution_pct,
            "note": ("Flow Time uses created→resolved as proxy. "
                     "Flow Distribution maps issue types to SAFe categories: "
                     "Story→Feature, Bug→Defect, Spike→Enabler, etc.")}


def safe_feature_progress(board_id, creds=None):
    """Feature/Epic-level progress across all sprints on the board.
    Counts Epic issuetypes and their resolution status."""
    res = list_sprints(board_id, creds=creds)
    if not res["ok"]: return res
    epics = {}  # key -> {summary, status, done}
    for s in res["sprints"]:
        ir = list_sprint_issues(s["id"], creds=creds)
        if not ir["ok"]: continue
        for it in ir["issues"]:
            f = it.get("fields", {})
            t = ((f.get("issuetype") or {}).get("name") or "").lower()
            if "epic" not in t and "feature" not in t: continue
            k = it.get("key")
            if k in epics: continue
            epics[k] = {
                "key": k,
                "summary": f.get("summary", ""),
                "status":  (f.get("status") or {}).get("name", ""),
                "done":    _is_done(f),
            }
    items = list(epics.values())
    done = sum(1 for e in items if e["done"])
    total = len(items)
    return {"ok": True, "total_features": total, "completed_features": done,
            "in_progress_features": total - done,
            "completion_pct": round(done/total*100, 1) if total else 0,
            "features": items,
            "note": "Counts Epic/Feature issuetypes seen across all sprints on the board."}


def safe_program_dashboard(board_id, sprints_per_pi=5, creds=None):
    """One-call SAFe program-level summary combining the key metrics."""
    pred = safe_pi_predictability(board_id, sprints_per_pi, creds=creds)
    vel  = safe_pi_velocity(board_id, sprints_per_pi, creds=creds)
    flow = safe_flow_metrics(board_id, sprints_per_pi, creds=creds)
    feat = safe_feature_progress(board_id, creds=creds)
    return {"ok": True,
            "predictability": pred if pred["ok"] else {"error": pred.get("error")},
            "pi_velocity":    vel  if vel["ok"]  else {"error": vel.get("error")},
            "flow_metrics":   flow if flow["ok"] else {"error": flow.get("error")},
            "features":       feat if feat["ok"] else {"error": feat.get("error")},
            "summary": {
                "pi_predictability_pct": pred.get("pi_predictability_pct"),
                "pi_velocity_total":     vel.get("pi_velocity_total"),
                "avg_flow_time_days":    flow.get("average_flow_time_days"),
                "feature_completion_pct": feat.get("completion_pct"),
            }}
