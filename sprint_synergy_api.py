"""
SprintSynergy — FastAPI Plugin Layer
Exposes all 24 SprintSynergy tools as a secure REST API endpoint.

Run:
    uvicorn sprint_synergy_api:app --reload --port 8000

Test health:
    curl http://localhost:8000/

Test a tool:
    curl -X POST http://localhost:8000/tool \
         -H "x-api-key: CHANGE_ME_SECRET_KEY" \
         -H "Content-Type: application/json" \
         -d '{"tool":"velocity_trend","args":{"board_id":34,"last_n":5},
              "creds":{"jira_url":"https://yourorg.atlassian.net",
                       "email":"you@example.com","api_token":"your_token"}}'
"""
from __future__ import annotations
import os
from typing import Any, Dict
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ss_ai import dispatch_tool, list_tool_names

app = FastAPI(
    title="SprintSynergy API",
    description="Secure REST wrapper around all 24 SprintSynergy tools.",
    version="1.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["GET","POST"], allow_headers=["*"])

_API_KEY = os.environ.get("API_KEY", "CHANGE_ME_SECRET_KEY")

def _require_key(x_api_key: str = Header(..., alias="x-api-key")) -> None:
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized — invalid API key")

class ToolRequest(BaseModel):
    tool:  str
    args:  Dict[str, Any] = {}
    creds: Dict[str, str] = {}

@app.get("/", summary="Health check")
def health():
    return {"status":"ok","service":"SprintSynergy API",
            "tools_available":len(list_tool_names())}

@app.get("/tools", summary="List all available tool names")
def get_tools():
    return {"tools":list_tool_names(),"count":len(list_tool_names())}

@app.post("/tool", summary="Run any SprintSynergy tool")
def run_tool(req: ToolRequest, x_api_key: str = Header(..., alias="x-api-key")):
    """
    Run any of the 24 SprintSynergy tools by name.

    Authentication: pass your API key in the x-api-key header.

    Body:
    - tool  — tool name (GET /tools for the full list)
    - args  — tool arguments as a JSON object
    - creds — Jira credentials (jira_url, email, api_token)
    """
    _require_key(x_api_key)
    if req.tool not in list_tool_names():
        raise HTTPException(status_code=404,
            detail=f"Unknown tool '{req.tool}'. GET /tools for the full list.")
    try:
        result = dispatch_tool(req.tool, req.args, creds=req.creds or None)
        return {"status":"success","tool":req.tool,"result":result}
    except Exception as exc:
        return {"status":"error","tool":req.tool,"message":str(exc)}
