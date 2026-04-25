"""
SprintSynergy library — pure functions, no input() prompts, no print().

Credential priority (highest wins):
  1. creds= dict passed per-call  (Streamlit session_state / API layer)
  2. Environment variables         JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
  3. .env file                     (loaded via python-dotenv if present)
  4. config.ini                    (local only — never committed to git)
"""
from __future__ import annotations
import os, configparser
from datetime import datetime, timedelta
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

_HERE     = os.path.dirname(os.path.abspath(__file__))
_CFG_PATH = os.path.join(_HERE, "config.ini")

DEFAULT_STORY_POINT_FIELDS = ["customfield_10016","customfield_10026","customfield_10004"]

def _load_config():
    cfg = {}
    env_url   = os.environ.get("JIRA_URL","").strip().rstrip("/")
    env_email = os.environ.get("JIRA_EMAIL","").strip()
    env_token = os.environ.get("JIRA_API_TOKEN","").strip()
    if env_url:   cfg["jira_url"]  = env_url
    if env_email: cfg["email"]     = env_email
    if env_token: cfg["api_token"] = env_token
    if os.path.exists(_CFG_PATH):
        try:
            cp = configparser.ConfigParser()
            cp.read(_CFG_PATH, encoding="utf-8")
            if "jira" in cp:
                if not cfg.get("jira_url"):  cfg["jira_url"]  = cp["jira"].get("jira_url","").strip().rstrip("/")
                if not cfg.get("email"):     cfg["email"]     = cp["jira"].get("email","").strip()
                if not cfg.get("api_token"): cfg["api_token"] = cp["jira"].get("api_token","").strip()
            fields_raw = cp.get("story_points","fields",fallback=", ".join(DEFAULT_STORY_POINT_FIELDS))
            cfg["story_points_fields"] = [f.strip() for f in fields_raw.split(",") if f.strip()] or list(DEFAULT_STORY_POINT_FIELDS)
        except Exception:
            pass
    cfg.setdefault("story_points_fields", list(DEFAULT_STORY_POINT_FIELDS))
    return cfg

CONFIG              = _load_config()
DEFAULT_HEADERS     = {"Accept":"application/json","Content-Type":"application/json"}
DONE_STATUSES       = {"done","closed","resolved","complete","completed"}
STORY_POINTS_FIELDS = CONFIG.get("story_points_fields", list(DEFAULT_STORY_POINT_FIELDS))

def _ctx(creds=None):
    c = {**CONFIG, **(creds or {})}
    missing = [k for k in ("jira_url","email","api_token") if not c.get(k)]
    if missing:
        raise RuntimeError(
            "Jira credentials not configured. Set JIRA_URL / JIRA_EMAIL / JIRA_API_TOKEN "
            "as environment variables, add them to a .env file, or open the Configuration page. "
            "Missing: " + ", ".join(missing))
    return c["jira_url"].rstrip("/"), (c["email"], c["api_token"])

def _err(r):
    try: return r.json().get("message") or r.text[:200]
    except Exception: return r.text[:200]

def _is_done(fields):
    s = fields.get("status") or {}
    name = (s.get("name") or "").lower()
    cat  = ((s.get("statusCategory") or {}).get("key") or "")
    return name in DONE_STATUSES or cat == "done"

def _story_points(fields):
    for fid in STORY_POINTS_FIELDS:
        v = fields.get(fid)
        if isinstance(v,(int,float)): return float(v)
    return 0.0

# ── SPRINTS ──────────────────────────────────────────────────────────────────

def list_sprints(board_id, state=None, creds=None):
    base,auth = _ctx(creds)
    url = f"{base}/rest/agile/1.0/board/{board_id}/sprint"
    params = {"maxResults":50}
    if state: params["state"] = state
    out = []
    while True:
        params["startAt"] = len(out)
        r = requests.get(url,auth=auth,headers=DEFAULT_HEADERS,params=params)
        if r.status_code != 200: return {"ok":False,"error":f"{r.status_code}: {_err(r)}"}
        data = r.json()
        out.extend(data.get("values",[]))
        if data.get("isLast",True): break
    return {"ok":True,"sprints":out,"count":len(out)}

def create_sprint(board_id, name, start_date, end_date, goal="", creds=None):
    base,auth = _ctx(creds)
    payload = {"name":name,"startDate":f"{start_date}T09:00:00.000Z",
               "endDate":f"{end_date}T09:00:00.000Z","goal":goal,"originBoardId":board_id}
    r = requests.post(f"{base}/rest/agile/1.0/sprint",auth=auth,headers=DEFAULT_HEADERS,json=payload)
    if r.status_code == 201: return {"ok":True,"sprint":r.json()}
    return {"ok":False,"error":f"{r.status_code}: {_err(r)}"}

def create_sprint_series(board_id, prefix, start_date, start_number, num_sprints, duration_days=14, goal="", creds=None):
    start = datetime.strptime(start_date,"%Y-%m-%d")
    results = []
    for i in range(num_sprints):
        end = start + timedelta(days=duration_days)
        res = create_sprint(board_id,name=f"{prefix} {start_number+i}",
                            start_date=start.strftime("%Y-%m-%d"),end_date=end.strftime("%Y-%m-%d"),goal=goal,creds=creds)
        results.append(res); start = end
    ok = sum(1 for r in results if r["ok"])
    return {"ok":ok==num_sprints,"results":results,"created":ok,"total":num_sprints}

def rename_sprint(sprint_id, new_name, creds=None):
    base,auth = _ctx(creds)
    r = requests.post(f"{base}/rest/agile/1.0/sprint/{sprint_id}",auth=auth,headers=DEFAULT_HEADERS,json={"name":new_name})
    if r.status_code in (200,204): return {"ok":True,"sprint_id":sprint_id,"new_name":new_name}
    return {"ok":False,"error":f"{r.status_code}: {_err(r)}"}

def delete_sprint(sprint_id, creds=None):
    base,auth = _ctx(creds)
    r = requests.delete(f"{base}/rest/agile/1.0/sprint/{sprint_id}",auth=auth,headers=DEFAULT_HEADERS)
    if r.status_code in (200,204): return {"ok":True,"sprint_id":sprint_id}
    return {"ok":False,"error":f"{r.status_code}: {_err(r)}"}

def close_sprint(sprint_id, creds=None):
    base,auth = _ctx(creds)
    payload = {"state":"closed","completeDate":datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")}
    r = requests.post(f"{base}/rest/agile/1.0/sprint/{sprint_id}",auth=auth,headers=DEFAULT_HEADERS,json=payload)
    if r.status_code in (200,204): return {"ok":True,"sprint_id":sprint_id,"state":"closed"}
    return {"ok":False,"error":f"{r.status_code}: {_err(r)}"}

def start_sprint(sprint_id, creds=None):
    base,auth = _ctx(creds)
    r = requests.post(f"{base}/rest/agile/1.0/sprint/{sprint_id}",auth=auth,headers=DEFAULT_HEADERS,json={"state":"active"})
    if r.status_code in (200,204): return {"ok":True,"sprint_id":sprint_id,"state":"active"}
    return {"ok":False,"error":f"{r.status_code}: {_err(r)}"}

# ── ISSUES ───────────────────────────────────────────────────────────────────

def list_sprint_issues(sprint_id, extra_fields=False, creds=None):
    base,auth = _ctx(creds)
    fields = ["summary","status","issuetype"]
    if extra_fields: fields += ["assignee","created","resolutiondate"]
    fields += STORY_POINTS_FIELDS
    issues, start_at = [], 0
    while True:
        r = requests.get(f"{base}/rest/agile/1.0/sprint/{sprint_id}/issue",
                         auth=auth,headers=DEFAULT_HEADERS,
                         params={"startAt":start_at,"maxResults":100,"fields":",".join(fields)})
        if r.status_code != 200: return {"ok":False,"error":f"{r.status_code}: {_err(r)}"}
        data = r.json(); batch = data.get("issues",[])
        issues.extend(batch); start_at += len(batch)
        if start_at >= data.get("total",len(issues)) or not batch: break
    return {"ok":True,"issues":issues,"count":len(issues)}

def move_issues_to_sprint(target_sprint_id, issue_keys, creds=None):
    base,auth = _ctx(creds)
    url = f"{base}/rest/agile/1.0/sprint/{target_sprint_id}/issue"
    moved, failed = 0, []
    for i in range(0,len(issue_keys),50):
        batch = issue_keys[i:i+50]
        r = requests.post(url,auth=auth,headers=DEFAULT_HEADERS,json={"issues":batch})
        if r.status_code in (200,204): moved += len(batch)
        else: failed.append({"batch":batch,"error":f"{r.status_code}: {_err(r)}"})
    return {"ok":not failed,"moved":moved,"failed":failed,"total":len(issue_keys)}

def validate_sprint(sprint_id, creds=None):
    res = list_sprint_issues(sprint_id,creds=creds)
    if not res["ok"]: return res
    done, opens = [], []
    for it in res["issues"]:
        f = it.get("fields",{})
        rec = {"key":it.get("key",""),"type":(f.get("issuetype") or {}).get("name",""),
               "status":(f.get("status") or {}).get("name",""),"summary":f.get("summary","")}
        (done if _is_done(f) else opens).append(rec)
    total = len(res["issues"])
    return {"ok":True,"ready_to_close":len(opens)==0,"total":total,
            "done_count":len(done),"open_count":len(opens),"open_issues":opens,"done_issues":done}

def validate_and_close_sprint(sprint_id, target_sprint_id=None, force=False, creds=None):
    v = validate_sprint(sprint_id,creds=creds)
    if not v["ok"]: return v
    if v["ready_to_close"]:
        c = close_sprint(sprint_id,creds=creds); return {**v,"action":"closed","close_result":c}
    if target_sprint_id:
        keys = [o["key"] for o in v["open_issues"]]
        m = move_issues_to_sprint(target_sprint_id,keys,creds=creds)
        if not m["ok"]: return {**v,"action":"move_failed","move_result":m}
        c = close_sprint(sprint_id,creds=creds); return {**v,"action":"moved_then_closed","move_result":m,"close_result":c}
    if force:
        c = close_sprint(sprint_id,creds=creds); return {**v,"action":"force_closed","close_result":c}
    return {**v,"action":"blocked","message":f"{v['open_count']} open issue(s). Pass target_sprint_id or force=True."}

# ── REPORTS ──────────────────────────────────────────────────────────────────

def sprint_report(sprint_id, creds=None):
    base,auth = _ctx(creds)
    sprint_r = requests.get(f"{base}/rest/agile/1.0/sprint/{sprint_id}",auth=auth,headers=DEFAULT_HEADERS)
    if sprint_r.status_code != 200: return {"ok":False,"error":f"{sprint_r.status_code}: {_err(sprint_r)}"}
    sprint = sprint_r.json()
    issues_res = list_sprint_issues(sprint_id,extra_fields=True,creds=creds)
    if not issues_res["ok"]: return issues_res
    issues = issues_res["issues"]
    rows, completed = [], 0
    cmt_pts = done_pts = 0.0; types = {}
    for it in issues:
        f = it.get("fields",{}); done = _is_done(f); pts = _story_points(f)
        cmt_pts += pts
        if done: completed += 1; done_pts += pts
        tp = (f.get("issuetype") or {}).get("name",""); types[tp] = types.get(tp,0)+1
        rows.append({"key":it.get("key",""),"type":tp,"status":(f.get("status") or {}).get("name",""),
                     "assignee":(f.get("assignee") or {}).get("displayName","Unassigned"),
                     "story_points":pts,"result":"Completed" if done else "Carried Over","summary":f.get("summary","")})
    total = len(issues)
    return {"ok":True,"sprint_id":sprint_id,"sprint_name":sprint.get("name"),"state":sprint.get("state"),
            "start_date":(sprint.get("startDate") or "")[:10],"end_date":(sprint.get("endDate") or "")[:10],
            "complete_date":(sprint.get("completeDate") or "")[:10],"total_issues":total,
            "completed_issues":completed,"carried_over":total-completed,
            "completion_rate":round(completed/total*100,1) if total else 0.0,
            "committed_points":round(cmt_pts,1),"completed_points":round(done_pts,1),
            "velocity":round(done_pts,1),"type_breakdown":types,"issues":rows}

def velocity_trend(board_id, last_n=5, creds=None):
    res = list_sprints(board_id,state="closed",creds=creds)
    if not res["ok"]: return res
    closed = sorted(res["sprints"],key=lambda s:s.get("completeDate") or s.get("endDate") or "")
    selected = closed[-last_n:]; summaries = []
    for s in selected:
        rep = sprint_report(s["id"],creds=creds)
        if not rep["ok"]: continue
        summaries.append({"sprint_id":rep["sprint_id"],"name":rep["sprint_name"],"end_date":rep["end_date"],
                          "total":rep["total_issues"],"completed":rep["completed_issues"],"carried":rep["carried_over"],
                          "completion_rate":rep["completion_rate"],"committed_points":rep["committed_points"],
                          "completed_points":rep["completed_points"],"velocity":rep["velocity"]})
    if not summaries:
        return {"ok":True,"sprints":[],"average_velocity":0,"highest_velocity":0,"lowest_velocity":0,"trend":"n/a"}
    vels = [s["velocity"] for s in summaries]
    trend = "flat"
    if len(vels) >= 2:
        if vels[-1] > vels[0]: trend = "up"
        elif vels[-1] < vels[0]: trend = "down"
    return {"ok":True,"count":len(summaries),"sprints":summaries,
            "average_velocity":round(sum(vels)/len(vels),1),"highest_velocity":max(vels),
            "lowest_velocity":min(vels),"trend":trend,
            "trend_delta":round(vels[-1]-vels[0],1) if len(vels)>=2 else 0}
