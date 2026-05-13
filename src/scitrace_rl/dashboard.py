from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from .utils import write_text


def render_dashboard(trace: dict[str, Any], report_markdown: str, path: Path) -> None:
    validations = "\n".join(
        f"""        <tr>
          <td>{escape(item['name'])}</td>
          <td><span class="pill {escape(item['status'])}">{escape(item['status'])}</span></td>
          <td>{item['score']:.3f}</td>
          <td>{escape(item['message'])}</td>
        </tr>"""
        for item in trace["validations"]
    )
    tools = "\n".join(
        f"""        <li>
          <strong>{escape(tool['name'])}</strong>
          <span>{escape(tool['status'])}</span>
          <code>{escape(tool['output_hash'][:12])}</code>
        </li>"""
        for tool in trace["tools"]
    )
    artifacts = "\n".join(
        f"<li><strong>{escape(item['kind'])}</strong>: {escape(item['summary'])} <code>{escape(item['sha256'][:12])}</code></li>"
        for item in trace["artifacts"]
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SciTrace-RL Demo Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #16211f;
      --muted: #64706d;
      --line: #dce4e0;
      --panel: #f7faf8;
      --accent: #0f766e;
      --warn: #a16207;
      --bad: #b42318;
    }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: #ffffff;
    }}
    header {{
      padding: 36px min(6vw, 72px) 20px;
      border-bottom: 1px solid var(--line);
    }}
    main {{
      display: grid;
      grid-template-columns: minmax(280px, 420px) minmax(0, 1fr);
      gap: 28px;
      padding: 28px min(6vw, 72px) 48px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 4vw, 48px);
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    section {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin-bottom: 18px;
      background: var(--panel);
    }}
    .metric {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
    }}
    .metric:last-child {{ border-bottom: 0; }}
    .metric span {{ color: var(--muted); }}
    .metric strong {{ font-size: 20px; }}
    ul {{
      padding-left: 18px;
      margin: 0;
    }}
    li {{
      margin: 8px 0;
      line-height: 1.45;
    }}
    li span {{
      margin-left: 8px;
      color: var(--muted);
    }}
    code {{
      background: #eaf1ee;
      padding: 2px 5px;
      border-radius: 4px;
      font-size: 12px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border-radius: 8px;
      overflow: hidden;
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid var(--line);
      padding: 11px;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{ background: #edf5f1; }}
    .pill {{
      display: inline-block;
      min-width: 48px;
      text-align: center;
      border-radius: 999px;
      padding: 3px 8px;
      background: #dff3ed;
      color: var(--accent);
      font-weight: 700;
      font-size: 12px;
    }}
    .pill.warn {{ background: #fff4d6; color: var(--warn); }}
    .pill.fail {{ background: #ffe4e0; color: var(--bad); }}
    .pill.skip {{ background: #edf0ef; color: var(--muted); }}
    pre {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #101817;
      color: #eaf7f2;
      border-radius: 8px;
      padding: 18px;
      line-height: 1.45;
      font-size: 13px;
    }}
    @media (max-width: 860px) {{
      main {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>SciTrace-RL</h1>
    <p>Trace, validation, and reward infrastructure for scientific AI agents.</p>
  </header>
  <main>
    <aside>
      <section>
        <h2>Run Metrics</h2>
        <div class="metric"><span>Trace ID</span><strong>{escape(trace['trace_id'][:14])}</strong></div>
        <div class="metric"><span>Reward</span><strong>{trace['reward']['reward']:.3f}</strong></div>
        <div class="metric"><span>Quality</span><strong>{trace['reward']['quality_score']:.3f}</strong></div>
        <div class="metric"><span>Tool Calls</span><strong>{trace['metrics']['total_tool_calls']}</strong></div>
      </section>
      <section>
        <h2>Tool Timeline</h2>
        <ul>{tools}</ul>
      </section>
      <section>
        <h2>Artifacts</h2>
        <ul>{artifacts}</ul>
      </section>
    </aside>
    <article>
      <section>
        <h2>Validation Scorecard</h2>
        <table>
          <thead><tr><th>Gate</th><th>Status</th><th>Score</th><th>Message</th></tr></thead>
          <tbody>{validations}</tbody>
        </table>
      </section>
      <section>
        <h2>Generated Report</h2>
        <pre>{escape(report_markdown)}</pre>
      </section>
    </article>
  </main>
</body>
</html>
"""
    write_text(path, html)
