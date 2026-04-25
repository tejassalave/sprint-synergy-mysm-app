"""
SprintSynergy as AI-callable tools.

Local folder:
    D:\\New Volume D Drive Backup\\Trainings_Skills\\AI Project Work\\
    Important Program\\Sprint Synergy Program\\Revised JIRA Config files

Two flavors of the same underlying functions from `sprint_synergy_lib`:

  1) CLAUDE_TOOLS         — Anthropic tool-use schema (list of dicts)
  2) OPENAI_TOOLS         — OpenAI function-calling schema (list of dicts)
  3) dispatch_tool(name, args) — runs the matching library function
                                 and returns a JSON-serializable dict

USAGE WITH CLAUDE (Anthropic Python SDK):

    from anthropic import Anthropic
    from sprint_synergy_ai import CLAUDE_TOOLS, dispatch_tool

    client = Anthropic()
    msgs = [{"role": "user", "content": "Show velocity trend for board 34, last 6 sprints"}]
    while True:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=2048,
            tools=CLAUDE_TOOLS,
            messages=msgs,
        )
        msgs.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            print(resp.content[0].text); break
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                result = dispatch_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
        msgs.append({"role": "user", "content": tool_results})

USAGE WITH OPENAI:

    from openai import OpenAI
    from sprint_synergy_ai import OPENAI_TOOLS, dispatch_tool
    client = OpenAI()
    # Same idea — pass tools=OPENAI_TOOLS, then on tool_calls, run
    # dispatch_tool(call.function.name, json.loads(call.function.arguments))
    # and feed the result back as a tool message.

USAGE INSIDE LOVABLE / ANY BACKEND:

    from sprint_synergy_ai import dispatch_tool
    out = dispatch_tool("create_sprint_series",
        {"board_id": 34, "prefix": "AES Sprint",
         "start_date": "2026-08-01", "start_number": 6,
         "num_sprints": 3, "duration_days": 14})
"""

import json
from ss_lib import (
    list_sprints, create_sprint, create_sprint_series, rename_sprint,
    delete_sprint, close_sprint, start_sprint,
    list_sprint_issues, move_issues_to_sprint,
    validate_sprint, validate_and_close_sprint,
    sprint_report, velocity_trend,
)
from ss_metrics import (
    scrum_commitment_reliability, scrum_throughput, scrum_cycle_time,
    scrum_defect_ratio, scrum_sprint_goal_success, scrum_sprint_burndown,
    safe_pi_predictability, safe_pi_velocity, safe_flow_metrics,
    safe_feature_progress, safe_program_dashboard,
)


# ============================================================
#  Shared schema definitions
# ============================================================

_TOOLS = [
    {
        "name": "list_sprints",
        "description": "List sprints on a Jira board, optionally filtered by state.",
        "schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer", "description": "Jira agile board ID."},
                "state": {"type": "string", "enum": ["active", "closed", "future"],
                          "description": "Optional state filter."},
            },
            "required": ["board_id"],
        },
        "fn": list_sprints,
    },
    {
        "name": "create_sprint",
        "description": "Create a single sprint on a board.",
        "schema": {
            "type": "object",
            "properties": {
                "board_id":   {"type": "integer"},
                "name":       {"type": "string"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date":   {"type": "string", "description": "YYYY-MM-DD"},
                "goal":       {"type": "string"},
            },
            "required": ["board_id", "name", "start_date", "end_date"],
        },
        "fn": create_sprint,
    },
    {
        "name": "create_sprint_series",
        "description": "Create N back-to-back sprints starting from a date.",
        "schema": {
            "type": "object",
            "properties": {
                "board_id":      {"type": "integer"},
                "prefix":        {"type": "string", "description": "e.g. 'AES Sprint'"},
                "start_date":    {"type": "string", "description": "YYYY-MM-DD"},
                "start_number":  {"type": "integer", "description": "First sprint number"},
                "num_sprints":   {"type": "integer"},
                "duration_days": {"type": "integer", "description": "Default 14"},
                "goal":          {"type": "string"},
            },
            "required": ["board_id", "prefix", "start_date", "start_number", "num_sprints"],
        },
        "fn": create_sprint_series,
    },
    {
        "name": "rename_sprint",
        "description": "Rename an existing sprint.",
        "schema": {
            "type": "object",
            "properties": {
                "sprint_id": {"type": "integer"},
                "new_name":  {"type": "string"},
            },
            "required": ["sprint_id", "new_name"],
        },
        "fn": rename_sprint,
    },
    {
        "name": "delete_sprint",
        "description": "Delete a sprint. Active sprints must be closed first.",
        "schema": {
            "type": "object",
            "properties": {"sprint_id": {"type": "integer"}},
            "required": ["sprint_id"],
        },
        "fn": delete_sprint,
    },
    {
        "name": "start_sprint",
        "description": "Mark a future sprint as active.",
        "schema": {
            "type": "object",
            "properties": {"sprint_id": {"type": "integer"}},
            "required": ["sprint_id"],
        },
        "fn": start_sprint,
    },
    {
        "name": "close_sprint",
        "description": "Force-close an active sprint without validation. Open issues stay attached.",
        "schema": {
            "type": "object",
            "properties": {"sprint_id": {"type": "integer"}},
            "required": ["sprint_id"],
        },
        "fn": close_sprint,
    },
    {
        "name": "list_sprint_issues",
        "description": "List all issues in a sprint.",
        "schema": {
            "type": "object",
            "properties": {
                "sprint_id":    {"type": "integer"},
                "extra_fields": {"type": "boolean", "description": "Include assignee, dates."},
            },
            "required": ["sprint_id"],
        },
        "fn": list_sprint_issues,
    },
    {
        "name": "move_issues_to_sprint",
        "description": "Move issues to another sprint by issue keys (e.g. ['AES-12','AES-13']).",
        "schema": {
            "type": "object",
            "properties": {
                "target_sprint_id": {"type": "integer"},
                "issue_keys":       {"type": "array", "items": {"type": "string"}},
            },
            "required": ["target_sprint_id", "issue_keys"],
        },
        "fn": move_issues_to_sprint,
    },
    {
        "name": "validate_sprint",
        "description": "Check if a sprint is ready to close. Returns counts of done/open issues.",
        "schema": {
            "type": "object",
            "properties": {"sprint_id": {"type": "integer"}},
            "required": ["sprint_id"],
        },
        "fn": validate_sprint,
    },
    {
        "name": "validate_and_close_sprint",
        "description": ("Smart close: if all issues are done it closes; if target_sprint_id "
                        "is given it moves open issues there first then closes; if force=true "
                        "it closes regardless; otherwise it returns a validation report only."),
        "schema": {
            "type": "object",
            "properties": {
                "sprint_id":        {"type": "integer"},
                "target_sprint_id": {"type": "integer", "description": "Where to move open issues."},
                "force":            {"type": "boolean", "description": "Close even if open issues remain."},
            },
            "required": ["sprint_id"],
        },
        "fn": validate_and_close_sprint,
    },
    {
        "name": "sprint_report",
        "description": "Full sprint report: completed, carried over, velocity, type breakdown.",
        "schema": {
            "type": "object",
            "properties": {"sprint_id": {"type": "integer"}},
            "required": ["sprint_id"],
        },
        "fn": sprint_report,
    },
    {
        "name": "velocity_trend",
        "description": "Compare velocity across the last N closed sprints on a board.",
        "schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer"},
                "last_n":   {"type": "integer", "description": "Default 5"},
            },
            "required": ["board_id"],
        },
        "fn": velocity_trend,
    },

    # ============================================================
    #  SCRUM METRICS
    # ============================================================
    {
        "name": "scrum_commitment_reliability",
        "description": ("Scrum Say-Do Ratio: completed_points / committed_points "
                        "across the last N closed sprints. Healthy range 80–100%."),
        "schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer"},
                "last_n":   {"type": "integer", "description": "Default 5"},
            },
            "required": ["board_id"],
        },
        "fn": scrum_commitment_reliability,
    },
    {
        "name": "scrum_throughput",
        "description": "Scrum Throughput: number of issues completed per sprint over last N sprints.",
        "schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer"},
                "last_n":   {"type": "integer", "description": "Default 5"},
            },
            "required": ["board_id"],
        },
        "fn": scrum_throughput,
    },
    {
        "name": "scrum_cycle_time",
        "description": ("Scrum Cycle/Lead Time for a single sprint: avg, median, p85 days "
                        "from issue created to resolved, for completed issues."),
        "schema": {
            "type": "object",
            "properties": {"sprint_id": {"type": "integer"}},
            "required": ["sprint_id"],
        },
        "fn": scrum_cycle_time,
    },
    {
        "name": "scrum_defect_ratio",
        "description": "Scrum Defect Ratio: bugs / total issues across last N sprints.",
        "schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer"},
                "last_n":   {"type": "integer", "description": "Default 5"},
            },
            "required": ["board_id"],
        },
        "fn": scrum_defect_ratio,
    },
    {
        "name": "scrum_sprint_goal_success",
        "description": ("Scrum Sprint Goal Success Rate: % of last N sprints where "
                        "completion rate ≥ 80%."),
        "schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer"},
                "last_n":   {"type": "integer", "description": "Default 5"},
            },
            "required": ["board_id"],
        },
        "fn": scrum_sprint_goal_success,
    },
    {
        "name": "scrum_sprint_burndown",
        "description": ("Snapshot burndown for a single sprint: total/burned/remaining "
                        "story points and issue counts."),
        "schema": {
            "type": "object",
            "properties": {"sprint_id": {"type": "integer"}},
            "required": ["sprint_id"],
        },
        "fn": scrum_sprint_burndown,
    },

    # ============================================================
    #  SAFe METRICS  (Program Increment = N sprints)
    # ============================================================
    {
        "name": "safe_pi_predictability",
        "description": ("SAFe Program Predictability Measure (team proxy): avg ratio of "
                        "completed_points/committed_points across the last PI's sprints. "
                        "SAFe target 80–100%."),
        "schema": {
            "type": "object",
            "properties": {
                "board_id":       {"type": "integer"},
                "sprints_per_pi": {"type": "integer", "description": "Default 5"},
            },
            "required": ["board_id"],
        },
        "fn": safe_pi_predictability,
    },
    {
        "name": "safe_pi_velocity",
        "description": "SAFe PI Velocity: total story points delivered across the last PI's sprints.",
        "schema": {
            "type": "object",
            "properties": {
                "board_id":       {"type": "integer"},
                "sprints_per_pi": {"type": "integer", "description": "Default 5"},
            },
            "required": ["board_id"],
        },
        "fn": safe_pi_velocity,
    },
    {
        "name": "safe_flow_metrics",
        "description": ("SAFe / Flow Framework metrics over last N sprints: Flow Velocity, "
                        "Flow Time, Flow Load (WIP), Flow Efficiency, Flow Distribution "
                        "(features / defects / enablers / debt / risks)."),
        "schema": {
            "type": "object",
            "properties": {
                "board_id": {"type": "integer"},
                "last_n":   {"type": "integer", "description": "Default 5"},
            },
            "required": ["board_id"],
        },
        "fn": safe_flow_metrics,
    },
    {
        "name": "safe_feature_progress",
        "description": "SAFe Feature/Epic progress across all sprints on the board.",
        "schema": {
            "type": "object",
            "properties": {"board_id": {"type": "integer"}},
            "required": ["board_id"],
        },
        "fn": safe_feature_progress,
    },
    {
        "name": "safe_program_dashboard",
        "description": ("One-call SAFe program-level dashboard combining PI Predictability, "
                        "PI Velocity, Flow Metrics and Feature Progress."),
        "schema": {
            "type": "object",
            "properties": {
                "board_id":       {"type": "integer"},
                "sprints_per_pi": {"type": "integer", "description": "Default 5"},
            },
            "required": ["board_id"],
        },
        "fn": safe_program_dashboard,
    },
]


# ============================================================
#  Schemas formatted for each provider
# ============================================================

CLAUDE_TOOLS = [
    {"name": t["name"], "description": t["description"], "input_schema": t["schema"]}
    for t in _TOOLS
]

OPENAI_TOOLS = [
    {"type": "function",
     "function": {"name": t["name"], "description": t["description"], "parameters": t["schema"]}}
    for t in _TOOLS
]

# Lookup table for dispatch
_FN_MAP = {t["name"]: t["fn"] for t in _TOOLS}


# ============================================================
#  Dispatcher
# ============================================================

def dispatch_tool(name, args, creds=None):
    """Run a tool by name with a dict of args. Returns a dict result.

    Safe to call from anywhere — including AI tool-use loops, web handlers,
    or Lovable function bodies. Catches exceptions and returns them as
    {'ok': False, 'error': ...} so the AI can recover.

    If `creds` (a dict like {"jira_url": ..., "email": ..., "api_token": ...})
    is supplied, it is forwarded to the underlying library function so the
    call uses runtime credentials instead of config.ini values.
    """
    fn = _FN_MAP.get(name)
    if not fn:
        return {"ok": False, "error": f"Unknown tool: {name}"}
    try:
        if isinstance(args, str):
            args = json.loads(args)
        kwargs = dict(args or {})
        if creds and "creds" not in kwargs:
            kwargs["creds"] = creds
        return fn(**kwargs)
    except TypeError as e:
        return {"ok": False, "error": f"Bad arguments for {name}: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def list_tool_names():
    return list(_FN_MAP.keys())


# ============================================================
#  Quick sanity check when run directly
# ============================================================

if __name__ == "__main__":
    print("Available SprintSynergy AI tools:\n")
    for t in _TOOLS:
        print(f"  • {t['name']:<28}  {t['description']}")
    print(f"\n{len(_TOOLS)} tools registered.")
    print("\nClaude schema sample:")
    print(json.dumps(CLAUDE_TOOLS[0], indent=2))
    print("\nOpenAI schema sample:")
    print(json.dumps(OPENAI_TOOLS[0], indent=2))
