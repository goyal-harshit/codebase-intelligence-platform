"""Render a CodebaseAnalysis to a self-contained HTML dashboard and JSON."""
from __future__ import annotations

import datetime as _dt
import html
import json
import os

from .graph_html import graph_widget


def write_json(analysis, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(analysis.to_dict(), f, indent=2)


def write_html(analysis, path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_html(analysis))


def _e(v):
    return html.escape(str(v))


def _table(headers, rows, empty="No items found."):
    if not rows:
        return '<p class="empty">' + empty + '</p>'
    head = "".join("<th>" + _e(h) + "</th>" for h in headers)
    body = ""
    for r in rows:
        body += "<tr>" + "".join("<td>" + _e(c) + "</td>" for c in r) + "</tr>"
    return '<table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table>'


def _bars(data, color="#4f86f7"):
    if not data:
        return '<p class="empty">No data.</p>'
    mx = max(data.values()) or 1
    rows = ""
    for label, val in data.items():
        pct = 100 * val / mx
        rows += ('<div class="bar-row"><span class="bar-label">' + _e(label) + '</span>'
                 '<span class="bar-track"><span class="bar-fill" style="width:%.1f%%;background:%s"></span></span>'
                 '<span class="bar-val">' % (pct, color) + _e(val) + '</span></div>')
    return '<div class="bars">' + rows + '</div>'


def _section(title, body, subtitle=""):
    sub = '<p class="sub">' + _e(subtitle) + '</p>' if subtitle else ""
    return '<section><h2>' + _e(title) + '</h2>' + sub + body + '</section>'


def _sub(title, body):
    return '<div class="subsec"><h4>' + _e(title) + '</h4>' + body + '</div>'


def render_html(a):
    d = a.to_dict()
    ov = d["overview"]
    hs = d["health_score"]
    repo_name = os.path.basename(a.repo_path.rstrip("/\\")) or a.repo_path
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    grade = hs.get("grade", "?")
    grade_color = {"A": "#1f9d55", "B": "#5fb336", "C": "#d69e2e",
                   "D": "#dd6b20", "F": "#e53e3e"}.get(grade, "#888")

    kpis = [
        ("Health Score", "%s/100" % hs.get("overall", "?"), grade_color),
        ("Files", ov.get("files_analyzed", 0), "#4f86f7"),
        ("Functions/Methods", ov.get("functions_and_methods", 0), "#4f86f7"),
        ("Classes", ov.get("classes", 0), "#4f86f7"),
        ("Lines of Code", "{:,}".format(ov.get("total_lines_of_code", 0)), "#4f86f7"),
        ("Avg Complexity", d["complexity"].get("average", 0), "#9f7aea"),
    ]
    kpi_html = "".join(
        '<div class="kpi"><div class="kpi-val" style="color:%s">%s</div>'
        '<div class="kpi-label">%s</div></div>' % (c, _e(v), _e(label))
        for label, v, c in kpis)

    comp = hs.get("components", {})
    health_body = ('<div class="grade-badge" style="background:%s">%s</div>'
                   '<div class="health-detail">%s</div>'
                   % (grade_color, _e(grade), _bars(comp, grade_color)))

    lang_body = _table(["Language", "Files", "Entities"],
                       [[k, v["files"], v["entities"]] for k, v in d["languages"].items()])

    cx = d["complexity"]
    cx_body = ('<div class="grid2"><div>' + _bars(cx["distribution"], "#9f7aea") + '</div><div>'
               + _table(["Function", "File", "Line", "Complexity", "LOC"],
                        [[r["name"], r["file"], r["line"], r["complexity"], r["loc"]]
                         for r in cx["most_complex"][:15]]) + '</div></div>')

    mi = d["maintainability"]
    mi_body = ('<p>Average Maintainability Index: <b>' + _e(mi.get("average_index")) + '</b>/100. '
               + _e(mi.get("grade_distribution")) + '</p>'
               + _table(["File", "MI", "Avg Complexity", "LOC"],
                        [[r["file"], r["mi"], r["avg_complexity"], r["loc"]]
                         for r in mi["lowest_files"][:15]], "No files scored."))

    risks = d["risks"]
    rs = risks["summary"]
    risk_summary = _bars({k.replace("_", " ").title(): v for k, v in rs.items()}, "#e53e3e")
    dc = risks["dead_code"]
    risk_tables = (
        _sub("God Objects (too many methods)",
             _table(["Class", "File", "Line", "Methods"],
                    [[r["name"], r["file"], r["line"], r["methods"]] for r in risks["god_objects"]]))
        + _sub("Dead Code — high confidence (unused private symbols): %s" % dc["count"],
               _table(["Function", "File", "Line", "LOC"],
                      [[r["name"], r["file"], r["line"], r["loc"]] for r in dc["items"]],
                      "No unused private functions.")
               + '<p class="sub">Also %s public functions/methods have no in-repo callers — '
                 'likely external API or entry points (lower confidence, not counted above).</p>'
                 % dc.get("unused_public_api", 0))
        + _sub("High Cyclomatic Complexity (>15)",
               _table(["Function", "File", "Line", "Complexity"],
                      [[r["name"], r["file"], r["line"], r["complexity"]] for r in risks["high_complexity"]]))
        + _sub("Long Methods (>100 LOC)",
               _table(["Function", "File", "Line", "LOC"],
                      [[r["name"], r["file"], r["line"], r["loc"]] for r in risks["long_methods"]]))
        + _sub("Shotgun Surgery (called from many files)",
               _table(["Function", "File", "Line", "Caller Files"],
                      [[r["name"], r["file"], r["line"], r["called_from_files"]] for r in risks["shotgun_surgery"]]))
        + _sub("Deep Inheritance (>=5 levels)",
               _table(["Class", "File", "Depth"],
                      [[r["name"], r["file"], r["depth"]] for r in risks["deep_inheritance"]]))
    )
    risk_body = '<div class="risk-summary">' + risk_summary + '</div>' + risk_tables

    dep = d["dependencies"]
    circ = dep["circular_dependencies"]
    circ_html = ("".join('<li>' + _e(" -> ".join(c) + " -> " + c[0]) + '</li>' for c in circ)
                 if circ else '<p class="empty">No circular dependencies detected.</p>')
    dep_body = (
        '<p>%s internal modules, %s internal edges, %s external packages, <b>%s</b> circular dependencies.</p>'
        % (dep["internal_modules"], dep["internal_dependency_edges"],
           dep["external_dependencies"], dep["circular_dependency_count"])
        + '<div class="grid2"><div><h4>Most Depended-On Modules</h4>'
        + _table(["Module", "Dependents"], [[r["module"], r["depended_on_by"]] for r in dep["most_depended_on"][:12]])
        + '</div><div><h4>Top External Packages</h4>'
        + _table(["Package", "Import Sites"], [[r["package"], r["import_sites"]] for r in dep["top_external"][:12]])
        + '</div></div><h4>Circular Dependencies</h4><ul class="circ">' + circ_html + '</ul>')

    cg = d["call_graph"]
    cg_body = (
        '<div class="grid2"><div><h4>Critical Hubs (most called)</h4>'
        + _table(["Function", "File", "Called By"], [[r["name"], r["file"], r["called_by"]] for r in cg["most_called_functions"][:15]])
        + '</div><div><h4>Blast Radius (change impact)</h4>'
        + _table(["Function", "File", "Direct", "Transitive"],
                 [[r["name"], r["file"], r["directly_affected"], r["transitively_affected"]] for r in cg["blast_radius_top"][:15]])
        + '</div></div>')

    doc = d["documentation"]
    doc_body = (
        '<p>Docstring coverage (Python): <b>%s%%</b> (%s/%s functions).</p>'
        % (_e(doc.get("coverage_pct")), doc.get("documented"), doc.get("python_functions"))
        + _sub("Complex but undocumented",
               _table(["Function", "File", "Line", "Complexity"],
                      [[r["name"], r["file"], r["line"], r["complexity"]] for r in doc["undocumented_complex"]])))

    # Interactive dependency graph widget (stable, color-coded, legend).
    graph_body = graph_widget(d.get("graph", {"nodes": [], "links": []}),
                              a.index.get("communities", []), height=560, with_panel=True)

    git = d["git"]
    if git.get("available"):
        git_body = (
            '<p>%s commits, %s contributors, project bus factor <b>%s</b> (%s -> %s).</p>'
            % (git["total_commits"], git["contributors"], git["project_bus_factor"],
               _e(git.get("first_commit")), _e(git.get("last_commit")))
            + '<div class="grid2"><div><h4>Top Contributors</h4>'
            + _table(["Author", "Commits"], [[r["author"], r["commits"]] for r in git["top_contributors"][:12]])
            + '</div><div><h4>Most-Churned Files</h4>'
            + _table(["File", "Commits"], [[r["file"], r["commits"]] for r in git["file_churn"][:12]])
            + '</div></div><h4>Knowledge-Risk Files (single owner)</h4>'
            + _table(["File", "Sole Owner", "Ownership %", "Commits"],
                     [[r["file"], r["sole_owner"], r["ownership_pct"], r["commits"]] for r in git["knowledge_risk_files"][:12]]))
    else:
        git_body = '<p class="empty">No git history available for this path.</p>'

    hot_body = _table(["File", "Max Complexity", "Commits", "Hotspot Score"],
                      [[r["file"], r["max_complexity"], r["commits"], r["hotspot_score"]] for r in d["hotspots"][:15]])

    sections = (
        _section("Codebase Health", health_body)
        + _section("Languages", lang_body)
        + _section("Complexity Analysis", cx_body,
                   "Average %s, median %s, max %s." % (cx.get("average"), cx.get("median"), cx.get("max")))
        + _section("Maintainability", mi_body)
        + _section("Architecture Risks", risk_body)
        + _section("Dependency Analysis", dep_body)
        + _section("Call Graph & Change Impact", cg_body)
        + _section("Documentation", doc_body)
        + _section("Version Control Insights", git_body)
        + _section("Hotspots (complexity x churn)", hot_body,
                   "Files that are both complex and frequently changed - prioritize for refactoring.")
        + _section("Dependency Graph", graph_body,
                   "Interactive map of how files depend on each other.")
    )
    return _PAGE.format(repo=_e(repo_name), path=_e(a.repo_path), now=_e(now),
                        kpis=kpi_html, sections=sections)


_PAGE = "".join([
"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>",
"<meta name='viewport' content='width=device-width, initial-scale=1'>",
"<title>Codebase Intelligence - {repo}</title><style>",
"*{{box-sizing:border-box}}",
"body{{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#0f1419;color:#e6edf3;line-height:1.5}}",
"header{{padding:28px 36px;background:linear-gradient(135deg,#1a2233,#0f1419);border-bottom:1px solid #2a3340}}",
"header h1{{margin:0 0 4px;font-size:22px}} header .meta{{color:#8b97a7;font-size:13px}}",
".kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;padding:24px 36px}}",
".kpi{{background:#1a2029;border:1px solid #2a3340;border-radius:10px;padding:16px}}",
".kpi-val{{font-size:26px;font-weight:700}} .kpi-label{{color:#8b97a7;font-size:12px;margin-top:4px;text-transform:uppercase;letter-spacing:.04em}}",
"main{{padding:0 36px 60px;max-width:1280px}}",
"section{{background:#1a2029;border:1px solid #2a3340;border-radius:12px;padding:22px 24px;margin:18px 0}}",
"section h2{{margin:0 0 6px;font-size:18px}} section .sub{{color:#8b97a7;font-size:13px;margin:0 0 14px}}",
"h4{{margin:18px 0 8px;font-size:14px;color:#cbd5e1}} .subsec{{margin-top:14px}}",
"table{{width:100%;border-collapse:collapse;font-size:13px;margin:6px 0}}",
"th,td{{text-align:left;padding:7px 10px;border-bottom:1px solid #2a3340}}",
"th{{color:#8b97a7;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}",
"tr:hover td{{background:#222a35}} td{{font-variant-numeric:tabular-nums}}",
".empty{{color:#8b97a7;font-style:italic;font-size:13px}}",
".grid2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}",
"@media(max-width:880px){{.grid2{{grid-template-columns:1fr}}}}",
".bars{{display:flex;flex-direction:column;gap:7px}}",
".bar-row{{display:grid;grid-template-columns:200px 1fr 52px;align-items:center;gap:10px;font-size:12px}}",
".bar-label{{color:#8b97a7}} .bar-track{{background:#222a35;border-radius:5px;height:14px;overflow:hidden}}",
".bar-fill{{display:block;height:100%;border-radius:5px}} .bar-val{{text-align:right;font-variant-numeric:tabular-nums}}",
".grade-badge{{display:inline-flex;align-items:center;justify-content:center;width:64px;height:64px;border-radius:14px;font-size:34px;font-weight:800;color:#fff;float:left;margin-right:20px}}",
".health-detail{{overflow:hidden}} ul.circ{{font-size:13px}} ul.circ li{{margin:3px 0}}",
".risk-summary{{margin-bottom:16px}}",
"</style></head><body><header><h1>Codebase Intelligence Report - {repo}</h1>",
"<div class='meta'>{path} - generated {now}</div></header>",
"<div class='kpis'>{kpis}</div><main>{sections}</main></body></html>",
])


_GRAPH_JS = """
<script>
(function(){
  var cv=document.getElementById('depgraph'); if(!cv||!window.GRAPH) return;
  var ctx=cv.getContext('2d'), tip=document.getElementById('gtip');
  var W=cv.width, H=cv.height;
  var palette=['#4f86f7','#9f7aea','#1f9d55','#d69e2e','#e53e3e','#38b2ac','#ed64a6','#dd6b20','#667eea','#48bb78'];
  var groups={}, gi=0;
  var nodes=GRAPH.nodes.map(function(n){
    if(!(n.group in groups)) groups[n.group]=palette[gi++ % palette.length];
    return {id:n.id,label:n.label,group:n.group,deg:n.degree||0,
            r:Math.max(4,Math.min(20,3+Math.sqrt((n.entities||1))*1.6)),
            x:W/2+(Math.random()-0.5)*W*0.6, y:H/2+(Math.random()-0.5)*H*0.6, vx:0, vy:0,
            color:groups[n.group], info:n};
  });
  var idx={}; nodes.forEach(function(n,i){idx[n.id]=i;});
  var links=GRAPH.links.filter(function(l){return l.source in idx && l.target in idx;})
                       .map(function(l){return {s:idx[l.source],t:idx[l.target],type:l.type};});
  var scale=1, ox=0, oy=0, dragNode=null, panning=false, lastX=0, lastY=0, hover=null;

  function tick(){
    for(var i=0;i<nodes.length;i++){var a=nodes[i];
      for(var j=i+1;j<nodes.length;j++){var b=nodes[j];
        var dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy+0.01, d=Math.sqrt(d2);
        var f=1400/d2; var fx=dx/d*f, fy=dy/d*f;
        a.vx+=fx; a.vy+=fy; b.vx-=fx; b.vy-=fy;}}
    links.forEach(function(l){var a=nodes[l.s], b=nodes[l.t];
      var dx=b.x-a.x, dy=b.y-a.y, d=Math.sqrt(dx*dx+dy*dy)+0.01;
      var f=(d-90)*0.012; var fx=dx/d*f, fy=dy/d*f;
      a.vx+=fx; a.vy+=fy; b.vx-=fx; b.vy-=fy;});
    nodes.forEach(function(n){
      n.vx+=(W/2-n.x)*0.0009; n.vy+=(H/2-n.y)*0.0009;
      if(n!==dragNode){n.x+=n.vx*0.85; n.y+=n.vy*0.85;}
      n.vx*=0.86; n.vy*=0.86;});
  }
  function draw(){
    ctx.setTransform(1,0,0,1,0,0); ctx.clearRect(0,0,W,H);
    ctx.setTransform(scale,0,0,scale,ox,oy);
    ctx.lineWidth=0.6/scale;
    links.forEach(function(l){var a=nodes[l.s], b=nodes[l.t];
      ctx.strokeStyle=l.type==='import'?'rgba(79,134,247,0.28)':'rgba(159,122,234,0.28)';
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();});
    nodes.forEach(function(n){
      ctx.beginPath(); ctx.arc(n.x,n.y,n.r,0,6.2832);
      ctx.fillStyle=n.color; ctx.globalAlpha=(hover&&hover!==n)?0.5:1; ctx.fill();
      ctx.globalAlpha=1; ctx.lineWidth=1/scale; ctx.strokeStyle='#0f1419'; ctx.stroke();
      if(scale>1.1||n.r>=11){ctx.fillStyle='#cbd5e1'; ctx.font=(11/scale)+'px sans-serif';
        ctx.fillText(n.label, n.x+n.r+2, n.y+3);}});
  }
  function loop(){tick(); draw(); requestAnimationFrame(loop);} loop();

  function toWorld(ev){var rc=cv.getBoundingClientRect();
    var sx=cv.width/rc.width, sy=cv.height/rc.height;
    return {x:((ev.clientX-rc.left)*sx-ox)/scale, y:((ev.clientY-rc.top)*sy-oy)/scale,
            px:(ev.clientX-rc.left), py:(ev.clientY-rc.top)};}
  function pick(p){for(var i=nodes.length-1;i>=0;i--){var n=nodes[i];
    var dx=n.x-p.x, dy=n.y-p.y; if(dx*dx+dy*dy<=(n.r+3)*(n.r+3)) return n;} return null;}
  cv.addEventListener('mousedown',function(ev){var p=toWorld(ev); var n=pick(p);
    if(n){dragNode=n; cv.style.cursor='grabbing';} else {panning=true; lastX=ev.clientX; lastY=ev.clientY;}});
  window.addEventListener('mousemove',function(ev){var p=toWorld(ev);
    if(dragNode){dragNode.x=p.x; dragNode.y=p.y; dragNode.vx=0; dragNode.vy=0;}
    else if(panning){ox+=ev.clientX-lastX; oy+=ev.clientY-lastY; lastX=ev.clientX; lastY=ev.clientY;}
    else {var n=pick(p); hover=n;
      if(n){tip.style.display='block'; tip.style.left=(p.px+12)+'px'; tip.style.top=(p.py+8)+'px';
        tip.innerHTML='<b>'+n.info.id+'</b><br>'+n.info.entities+' entities, '+n.info.loc+
          ' LOC, max cc '+n.info.max_complexity+'<br>'+n.deg+' connections';}
      else tip.style.display='none';}});
  window.addEventListener('mouseup',function(){dragNode=null; panning=false; cv.style.cursor='grab';});
  cv.addEventListener('wheel',function(ev){ev.preventDefault();
    var p=toWorld(ev); var f=ev.deltaY<0?1.1:0.9; var ns=Math.max(0.2,Math.min(5,scale*f));
    ox=p.px-(p.px-ox)*(ns/scale); oy=p.py-(p.py-oy)*(ns/scale); scale=ns;},{passive:false});
})();
</script>
"""
