"""Risk-report rendering (Phase 3): a self-contained HTML report, plus an
optional PDF rendering of it.

HTML is always available (pure stdlib). PDF rendering uses WeasyPrint, which
pulls in native libraries (cairo/pango); it is therefore an *optional* extra —
``pdf_available()`` reports whether it can be used, and ``to_pdf`` raises a clear
error otherwise so the route can return a 503 rather than a 500.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from html import escape
from typing import TYPE_CHECKING, Optional, Sequence

import prompts as _prompts

if TYPE_CHECKING:
    from llm import LLMClient

SEVERITY_ORDER = ["high", "medium", "low"]

# Cap the findings list fed to the LLM so a huge scan can't blow up the prompt.
MAX_FINDINGS_FOR_NARRATIVE = 80


def format_findings(risks: Sequence[dict]) -> str:
    """One line per finding, for the narrative prompt."""
    return "\n".join(
        f"- [{r.get('severity', '?')}] {r.get('type', '?')}: {r.get('target', '?')}"
        f" ({r.get('file', '')}) — {r.get('details', '')}"
        for r in risks[:MAX_FINDINGS_FOR_NARRATIVE]
    ) or "- No risks detected."


def build_narrative(llm: "LLMClient", risks: Sequence[dict]) -> str:
    """LLM executive summary of the risk findings (Phase 4 item 4)."""
    prompt = _prompts.render("narrative_report", findings=format_findings(risks))
    return llm.generate(prompt, temperature=0.3)


def build_html_report(risks: Sequence[dict], title: str = "Codebase Risk Report",
                      narrative: Optional[str] = None) -> str:
    by_sev = Counter(r.get("severity", "unknown") for r in risks)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    narrative_html = ""
    if narrative:
        # Preserve paragraph breaks from the model's prose; escape its content.
        paras = "".join(f"<p>{escape(p.strip())}</p>" for p in narrative.split("\n\n") if p.strip())
        narrative_html = f'<section class="narrative"><h2>Summary</h2>{paras}</section>'

    summary_cells = "".join(
        f'<div class="card sev-{escape(s)}"><div class="n">{by_sev.get(s, 0)}</div>'
        f'<div class="l">{escape(s)}</div></div>'
        for s in SEVERITY_ORDER
    )

    rows = "".join(
        "<tr>"
        f"<td>{escape(str(r.get('severity', '')))}</td>"
        f"<td>{escape(str(r.get('type', '')))}</td>"
        f"<td>{escape(str(r.get('target', '')))}</td>"
        f"<td>{escape(str(r.get('file', '')))}</td>"
        f"<td>{escape(str(r.get('details', '')))}</td>"
        "</tr>"
        for r in risks
    ) or '<tr><td colspan="5">No risks detected.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; color: #1f2937; margin: 2rem; }}
  h1 {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
  .meta {{ color: #6b7280; margin-bottom: 1.5rem; }}
  .cards {{ display: flex; gap: 1rem; margin-bottom: 1.5rem; }}
  .card {{ border-radius: 8px; padding: 1rem 1.25rem; min-width: 90px; text-align: center; }}
  .card .n {{ font-size: 1.8rem; font-weight: 700; }}
  .card .l {{ text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
  .sev-high {{ background: #fee2e2; color: #991b1b; }}
  .sev-medium {{ background: #fef3c7; color: #92400e; }}
  .sev-low {{ background: #e0f2fe; color: #075985; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #e5e7eb; }}
  th {{ background: #f9fafb; }}
  .narrative {{ background: #f9fafb; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.5rem; }}
  .narrative h2 {{ font-size: 1.1rem; margin-top: 0; }}
</style></head>
<body>
  <h1>{escape(title)}</h1>
  <div class="meta">Generated {generated} &middot; {len(risks)} finding(s)</div>
  {narrative_html}
  <div class="cards">{summary_cells}</div>
  <table>
    <thead><tr><th>Severity</th><th>Type</th><th>Target</th><th>File</th><th>Details</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body></html>"""


def pdf_available() -> bool:
    try:
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


def to_pdf(html: str) -> bytes:
    if not pdf_available():
        raise RuntimeError(
            "PDF rendering requires WeasyPrint and its native libraries "
            "(install the 'weasyprint' extra). HTML export is always available."
        )
    import weasyprint

    return weasyprint.HTML(string=html).write_pdf()
