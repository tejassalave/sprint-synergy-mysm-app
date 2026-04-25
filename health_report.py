"""SprintSynergy — Scheduled Health Report

A standalone Python program that:
  1. Connects to your Jira-compatible board.
  2. Computes the SAFe Program Dashboard (predictability + velocity +
     flow + feature progress) plus key Scrum metrics (Say-Do for the
     latest sprint, throughput trend, defect ratio).
  3. Renders a clean HTML email body and a plain-text fallback.
  4. Optionally emails the report via SMTP.
  5. Optionally writes the HTML report to disk.

Designed to be run unattended on a schedule:
  • Linux / Mac        cron
  • Windows            Task Scheduler
  • Cloud              GitHub Actions, Render Cron, Replit Scheduled Deploy

Run it ad-hoc:
    python health_report.py --board 34 --project AES --last-n 5

Email it daily at 8 AM via cron:
    0 8 * * *  cd /path/to/sprint_synergy_mysm_app && /usr/bin/python3 health_report.py --email

Config priority for every value (highest wins):
    1. Command-line flag           (e.g.  --board 99)
    2. Environment variable        (e.g.  SS_BOARD=99)
    3. config.ini  [jira] / [email] / [report]
"""

from __future__ import annotations

import argparse
import configparser
import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from typing import Any

# Make the bundled engine modules importable when this script is invoked
# from any working directory (cron, Task Scheduler, etc.)
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import ss_lib  # noqa: E402
import ss_metrics  # noqa: E402

CFG_PATH = os.path.join(HERE, "config.ini")


# ============================================================
#  Config loading (CLI > env > config.ini)
# ============================================================


def _read_ini() -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    if os.path.exists(CFG_PATH):
        cp.read(CFG_PATH, encoding="utf-8")
    return cp


def _pick(
    cli_val,
    env_key: str,
    ini_section: str,
    ini_key: str,
    ini: configparser.ConfigParser,
    default=None,
):
    if cli_val not in (None, ""):
        return cli_val
    if env_key and os.environ.get(env_key):
        return os.environ[env_key]
    if ini.has_section(ini_section) and ini.get(ini_section, ini_key, fallback=None):
        return ini.get(ini_section, ini_key)
    return default


def build_config(args) -> dict[str, Any]:
    ini = _read_ini()
    cfg = {
        "jira_url": _pick(args.jira_url, "SS_JIRA_URL", "jira", "jira_url", ini),
        "email": _pick(args.jira_email, "SS_JIRA_EMAIL", "jira", "email", ini),
        "api_token": _pick(args.jira_token, "SS_JIRA_TOKEN", "jira", "api_token", ini),
        "board_id": int(_pick(args.board, "SS_BOARD", "report", "board_id", ini, 34)),
        "project_key": _pick(
            args.project, "SS_PROJECT", "report", "project_key", ini, "AES"
        ),
        "last_n": int(_pick(args.last_n, "SS_LAST_N", "report", "last_n", ini, 5)),
        # Email
        "smtp_host": _pick(args.smtp_host, "SS_SMTP_HOST", "email", "smtp_host", ini),
        "smtp_port": int(
            _pick(args.smtp_port, "SS_SMTP_PORT", "email", "smtp_port", ini, 587)
        ),
        "smtp_user": _pick(args.smtp_user, "SS_SMTP_USER", "email", "smtp_user", ini),
        "smtp_pass": _pick(args.smtp_pass, "SS_SMTP_PASS", "email", "smtp_pass", ini),
        "smtp_tls": str(
            _pick(args.smtp_tls, "SS_SMTP_TLS", "email", "smtp_tls", ini, "true")
        ).lower()
        == "true",
        "mail_from": _pick(args.mail_from, "SS_MAIL_FROM", "email", "mail_from", ini),
        "mail_to": _pick(args.mail_to, "SS_MAIL_TO", "email", "mail_to", ini),
    }
    return cfg


# ============================================================
#  Compute metrics
# ============================================================


def gather_metrics(cfg: dict[str, Any]) -> dict[str, Any]:
    creds = {
        "jira_url": cfg["jira_url"],
        "email": cfg["email"],
        "api_token": cfg["api_token"],
    }
    board = int(cfg["board_id"])
    project = cfg["project_key"]
    last_n = int(cfg["last_n"])

    out: dict[str, Any] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "board_id": board,
        "project": project,
        "last_n": last_n,
    }

    out["dashboard"] = ss_metrics.safe_program_dashboard(
        board,
        project,
        last_n=last_n,
        creds=creds,
    )
    out["throughput"] = ss_metrics.scrum_throughput(board, last_n=last_n, creds=creds)
    out["goal_success"] = ss_metrics.scrum_sprint_goal_success(
        board,
        last_n=last_n,
        creds=creds,
    )

    # Latest active or most-recent sprint for Say-Do + defect ratio
    latest_sid = None
    sp = ss_lib.list_sprints(board, state="active", creds=creds)
    if sp.get("ok") and sp.get("sprints"):
        latest_sid = sp["sprints"][0]["id"]
    else:
        sp = ss_lib.list_sprints(board, state="closed", creds=creds)
        if sp.get("ok") and sp.get("sprints"):
            latest_sid = sp["sprints"][-1]["id"]

    if latest_sid:
        out["latest_sprint_id"] = latest_sid
        out["say_do"] = ss_metrics.scrum_commitment_reliability(latest_sid, creds=creds)
        out["defect_ratio"] = ss_metrics.scrum_defect_ratio(latest_sid, creds=creds)

    return out


# ============================================================
#  Render
# ============================================================


def _val(d: dict | None, key: str, default="—"):
    if not isinstance(d, dict) or not d.get("ok"):
        return default
    v = d.get(key)
    return default if v is None else v


def render_text(report: dict[str, Any]) -> str:
    db = report.get("dashboard") or {}
    pp = db.get("predictability") or {}
    vel = db.get("velocity") or {}
    flow = db.get("flow") or {}
    feat = db.get("features") or {}
    say_do = report.get("say_do") or {}
    defects = report.get("defect_ratio") or {}
    gs = report.get("goal_success") or {}

    lines = [
        f"SprintSynergy — Health Report",
        f"Generated: {report['generated_at']}",
        f"Board: {report['board_id']}   Project: {report['project']}   Window: last {report['last_n']} sprints",
        "=" * 60,
        "",
        "PROGRAM HEALTH (SAFe)",
        f"  Predictability       : {_val(pp, 'program_predictability_pct')}%   (target 80–100%)",
        f"  PI Velocity (total)  : {_val(vel, 'total_completed_points')} pts",
        f"  PI Avg / sprint      : {_val(vel, 'avg_points_per_sprint')} pts",
        f"  Flow Velocity        : {_val(flow, 'flow_velocity')}",
        f"  Flow Time (days)     : {_val(flow, 'flow_time_days')}",
        f"  Flow Load            : {_val(flow, 'flow_load')}",
        f"  Flow Efficiency      : {_val(flow, 'flow_efficiency_pct')}%",
        f"  Features tracked     : {len((feat or {}).get('features', []))}",
        "",
        "LATEST SPRINT (Scrum)",
        f"  Sprint ID            : {report.get('latest_sprint_id', '—')}",
        f"  Say-Do Ratio         : {_val(say_do, 'say_do_ratio_pct')}%   (target 80–100%)",
        f"  Defect Ratio         : {_val(defects, 'defect_ratio_pct')}%",
        "",
        "GOAL SUCCESS RATE",
        f"  Successful sprints   : {_val(gs, 'successful')}/{_val(gs, 'total', 'n')}",
        f"  Success rate         : {_val(gs, 'success_rate_pct')}%",
        "",
        "— end of report —",
    ]
    return "\n".join(lines)


def render_html(report: dict[str, Any]) -> str:
    db = report.get("dashboard") or {}
    pp = db.get("predictability") or {}
    vel = db.get("velocity") or {}
    flow = db.get("flow") or {}
    feat = db.get("features") or {}
    say_do = report.get("say_do") or {}
    defects = report.get("defect_ratio") or {}
    gs = report.get("goal_success") or {}

    def card(label: str, value: Any, hint: str = "") -> str:
        return (
            f'<td style="padding:14px 18px;border:1px solid #e5e7eb;border-radius:8px;'
            f'background:#f9fafb;vertical-align:top;min-width:160px;">'
            f'<div style="font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;">{label}</div>'
            f'<div style="font-size:24px;color:#111827;font-weight:700;margin:4px 0;">{value}</div>'
            f'<div style="font-size:11px;color:#9ca3af;">{hint}</div>'
            f"</td>"
        )

    return f"""\
<html>
  <body style="font-family:Segoe UI, Helvetica, Arial, sans-serif; color:#1f2937; max-width:760px;">
    <h2 style="color:#1f3a68;margin-bottom:4px;">SprintSynergy — Health Report</h2>
    <div style="color:#6b7280;font-size:13px;">
      Generated {report["generated_at"]} • Board {report["board_id"]} •
      Project {report["project"]} • Window: last {report["last_n"]} sprints
    </div>
    <h3 style="margin-top:24px;color:#1f3a68;">Program Health (SAFe)</h3>
    <table cellspacing="8" cellpadding="0" style="border-collapse:separate;">
      <tr>
        {card("Predictability", f"{_val(pp, 'program_predictability_pct')}%", "Target 80–100%")}
        {card("PI Velocity", f"{_val(vel, 'total_completed_points')} pts", f"Avg {_val(vel, 'avg_points_per_sprint')}/sprint")}
        {card("Flow Efficiency", f"{_val(flow, 'flow_efficiency_pct')}%", f"Time {_val(flow, 'flow_time_days')}d")}
      </tr>
      <tr>
        {card("Flow Velocity", _val(flow, "flow_velocity"), "")}
        {card("Flow Load (WIP)", _val(flow, "flow_load"), "")}
        {card("Features tracked", len((feat or {}).get("features", [])), "")}
      </tr>
    </table>
    <h3 style="margin-top:28px;color:#1f3a68;">Latest Sprint (Scrum)</h3>
    <table cellspacing="8" cellpadding="0" style="border-collapse:separate;">
      <tr>
        {card("Sprint ID", report.get("latest_sprint_id", "—"), "")}
        {card("Say-Do Ratio", f"{_val(say_do, 'say_do_ratio_pct')}%", "Target 80–100%")}
        {card("Defect Ratio", f"{_val(defects, 'defect_ratio_pct')}%", "Lower is better")}
      </tr>
    </table>
    <h3 style="margin-top:28px;color:#1f3a68;">Goal Success Rate</h3>
    <table cellspacing="8" cellpadding="0" style="border-collapse:separate;">
      <tr>
        {card("Successful sprints", f"{_val(gs, 'successful')}/{_val(gs, 'total', 'n')}", "")}
        {card("Success rate", f"{_val(gs, 'success_rate_pct')}%", "")}
      </tr>
    </table>
    <p style="color:#9ca3af;font-size:12px;margin-top:30px;">
      Generated by SprintSynergy Health Report — sprint_synergy_mysm_app/health_report.py
    </p>
  </body>
</html>
"""


# ============================================================
#  Email
# ============================================================


def send_email(
    cfg: dict[str, Any], subject: str, text_body: str, html_body: str
) -> None:
    required = ["smtp_host", "smtp_user", "smtp_pass", "mail_from", "mail_to"]
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        raise RuntimeError(
            "Cannot send email — missing config: "
            + ", ".join(missing)
            + ". Set them via flags, environment variables, or config.ini [email]."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["mail_from"]
    msg["To"] = cfg["mail_to"]
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if cfg["smtp_tls"]:
        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=30) as s:
            s.starttls()
            s.login(cfg["smtp_user"], cfg["smtp_pass"])
            s.send_message(msg)
    else:
        with smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=30) as s:
            s.login(cfg["smtp_user"], cfg["smtp_pass"])
            s.send_message(msg)


# ============================================================
#  CLI
# ============================================================


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="SprintSynergy daily/weekly health report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--board", type=int, help="Jira board ID")
    p.add_argument(
        "--project", type=str, help="Jira project key (for SAFe feature progress)"
    )
    p.add_argument("--last-n", type=int, help="Sprints to include in PI window")
    p.add_argument("--jira-url", help="Jira base URL")
    p.add_argument("--jira-email", help="Jira email")
    p.add_argument("--jira-token", help="Jira API token")
    p.add_argument("--email", action="store_true", help="Send the report by email")
    p.add_argument("--save-html", metavar="PATH", help="Also write HTML report to PATH")
    p.add_argument(
        "--save-text", metavar="PATH", help="Also write plain-text report to PATH"
    )
    p.add_argument("--smtp-host"), p.add_argument("--smtp-port", type=int)
    p.add_argument("--smtp-user"), p.add_argument("--smtp-pass")
    p.add_argument("--smtp-tls", choices=["true", "false"])
    p.add_argument("--mail-from"), p.add_argument("--mail-to")
    args = p.parse_args(argv)

    cfg = build_config(args)
    for k in ("jira_url", "email", "api_token"):
        if not cfg.get(k):
            print(f"❌ Missing Jira credential: {k}", file=sys.stderr)
            return 2

    print(
        f"⏳ Generating health report for board {cfg['board_id']} / project {cfg['project_key']}…",
        file=sys.stderr,
    )
    report = gather_metrics(cfg)

    text = render_text(report)
    html = render_html(report)

    if args.save_text:
        with open(args.save_text, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ Wrote {args.save_text}", file=sys.stderr)
    if args.save_html:
        with open(args.save_html, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ Wrote {args.save_html}", file=sys.stderr)

    if args.email:
        subject = f"[SprintSynergy] Health Report — {report['generated_at']}"
        send_email(cfg, subject, text, html)
        print(f"📧 Sent email to {cfg['mail_to']}", file=sys.stderr)

    if not args.email and not args.save_html and not args.save_text:
        # Default: print plain text to stdout
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
