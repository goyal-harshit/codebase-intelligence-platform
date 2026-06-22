"""Multi-page web app renderer for one analysis (server-side, zero-dependency).

Each page is a separate route; a shared left-nav lets you click into the
section you want. Built for onboarding to large/old codebases.
"""
from __future__ import annotations

import html
import json

from .report import _table, _bars, _e
from . import qa
from .graph_html import graph_widget
from . import llm

NAV = [
    ("overview", "Overview"),
    ("graph", "Architecture Graph"),
    ("modules", "Modules"),
    ("functions", "Functions"),
    ("ask", "Ask the Code"),
    ("risks", "Risks"),
    ("dependencies", "Dependencies"),
    ("git", "History & Owners"),
    ("hotspots", "Hotspots"),
]


def page(analysis, base, active, inner, repo_label):
    nav = "".join(
        "<a href='%s/%s' class='%s'>%s</a>" % (base, slug, "on" if slug == active else "", _e(name))
        for slug, name in NAV)
    hs = analysis.health_score
    grade = hs.get("grade", "?")
    gcolor = {"A": "#1f9d55", "B": "#5fb336", "C": "#d69e2e",
              "D": "#dd6b20", "F": "#e53e3e"}.get(grade, "#888")
    return _LAYOUT.format(
        repo=_e(repo_label), nav=nav, inner=inner, base=base,
        grade=_e(grade), gcolor=gcolor, score=_e(hs.get("overall", "?")))


# ---- pages ----

def overview_page(a):
    ov, hs = a.overview, a.health_score
    kpis = [
        ("Files", ov.get("files_analyzed", 0)),
        ("Functions/Methods", ov.get("functions_and_methods", 0)),
        ("Classes", ov.get("classes", 0)),
        ("Lines of Code", "{:,}".format(ov.get("total_lines_of_code", 0))),
        ("Avg Complexity", a.complexity.get("average", 0)),
        ("Doc Coverage", "%s%%" % a.documentation.get("coverage_pct")),
    ]
    kpi = "".join("<div class='kpi'><div class='kv'>%s</div><div class='kl'>%s</div></div>"
                  % (_e(v), _e(l)) for l, v in kpis)
    sq = a.index.get("suggested_questions", [])
    sq_html = "".join(
        "<a class='chip' href='#' onclick=\"go(this)\">%s</a>" % _e(q) for q in sq)
    langs = _table(["Language", "Files", "Entities"],
                   [[k, v["files"], v["entities"]] for k, v in a.languages.items()])
    health = _bars(hs.get("components", {}), "#4f86f7")
    return (
        "<h1>Overview</h1>"
        "<p class='lead'>Start here. This codebase has <b>%d</b> files and <b>%d</b> functions. "
        "Use the left nav to explore, or jump straight to a question below.</p>"
        % (ov.get("files_analyzed", 0), ov.get("functions_and_methods", 0))
        + "<div class='kpis'>" + kpi + "</div>"
        + "<div class='card'><h3>New here? Ask the code</h3>"
          "<div class='chips'>" + sq_html + "</div>"
          "<script>function go(el){location.href='ask?q='+encodeURIComponent(el.textContent)}</script></div>"
        + "<div class='grid2'><div class='card'><h3>Health</h3>" + health + "</div>"
        + "<div class='card'><h3>Languages</h3>" + langs + "</div></div>"
    )


def graph_page(a):
    g = a.graph
    widget = graph_widget(g, a.index.get("communities", []), height=640)
    return (
        "<h1>Architecture Graph</h1>"
        "<p class='lead'>%d files, %d dependencies. Each bubble is a file (size = how connected it is, "
        "color = its module). The layout settles and stops &mdash; drag bubbles, click one to inspect its "
        "connections, use the legend to focus a module, or search.</p>"
        % (g.get("node_count", 0), g.get("link_count", 0))
        + widget
    )


def modules_page(a, base):
    comms = a.index.get("communities", [])
    gfiles = a.index.get("god_files", [])
    gfuncs = a.index.get("god_functions", [])
    god = ("<div class='grid2'><div class='card'><h3>God Files (most connected)</h3>"
           + _table(["File", "Connections", "Entities"],
                    [[g["file"], g["degree"], g["entities"]] for g in gfiles])
           + "</div><div class='card'><h3>Key Functions (most called)</h3>"
           + _table(["Function", "File", "Callers"],
                    [["<a href='%s/function/%s'>%s</a>" % (base, g["id"], _e(g["name"])), g["file"], g["callers"]]
                     for g in gfuncs]) + "</div></div>")
    blocks = ""
    for c in comms[:25]:
        files = "".join("<li>%s</li>" % _e(f) for f in c["files"][:30])
        blocks += ("<div class='card'><h3>Module: %s <span class='muted'>(%d files, %d entities)</span></h3>"
                   "<p class='muted'>Hub file: %s</p><ul class='filelist'>%s</ul></div>"
                   % (_e(c["name"]), c["size"], c["entities"], _e(c["hub_file"]), files))
    return ("<h1>Modules</h1>"
            "<p class='lead'>Files grouped into communities by how tightly they depend on each "
            "other &mdash; a fast map of the codebase's natural sub-systems.</p>"
            + god + blocks)


def functions_page(a, base):
    ents = a.index.get("entities", {})
    funcs = [e for e in ents.values() if e["type"] in ("function", "method", "class")]
    funcs.sort(key=lambda e: (-len(e["callers"]), e["file"], e["line"]))
    rows = [["<a href='%s/function/%s'>%s</a>" % (base, e["id"], _e(e["name"])),
             e["type"], e["file"], e["line"], e["complexity"],
             len(e["callers"]), len(e["callees"])] for e in funcs[:600]]
    return ("<h1>Functions &amp; Classes</h1>"
            "<p class='lead'>Every function/class, ranked by how many places use it. "
            "Type to filter, click any to see what it does and who calls it.</p>"
            "<input id='ffilter' placeholder='Filter by name or file...' "
            "style='width:100%;max-width:420px;margin-bottom:10px' "
            "oninput=\"filt(this.value)\">"
            "<div id='ftable'>"
            + _table(["Name", "Type", "File", "Line", "Complexity", "Callers", "Callees"], rows)
            + "</div>"
            "<script>function filt(q){q=q.toLowerCase();var t=document.querySelectorAll('#ftable tbody tr');"
            "t.forEach(function(r){r.style.display=r.textContent.toLowerCase().indexOf(q)>=0?'':'none'})}</script>")


def function_detail_page(a, eid, base):
    ents = a.index.get("entities", {})
    e = ents.get(eid)
    if not e:
        return "<h1>Not found</h1><p>That entity is not in the index.</p>"
    callers = [ents[c] for c in e["callers"] if c in ents]
    callees = [ents[c] for c in e["callees"] if c in ents]
    blast = _transitive_callers(ents, eid)
    doc = "<div class='doc'>%s</div>" % _e(e["docstring"]) if e["docstring"] else \
          "<p class='muted'>No docstring.</p>"
    def link(x):
        return "<a href='%s/function/%s'>%s</a>" % (base, x["id"], _e(x["name"]))
    callers_t = _table(["Caller", "File", "Line"],
                       [[link(c), c["file"], c["line"]] for c in callers],
                       "Nothing in this repo calls it (entry point / public API).")
    callees_t = _table(["Calls", "File", "Line"],
                       [[link(c), c["file"], c["line"]] for c in callees], "Calls nothing in-repo.")
    return (
        "<p><a href='%s/functions'>&larr; All functions</a></p>" % base
        + "<h1>%s</h1>" % _e(e["name"])
        + "<p class='lead'><code>%s</code></p>" % _e(e["signature"] or e["name"])
        + "<div class='kpis'>"
          "<div class='kpi'><div class='kv'>%s:%d</div><div class='kl'>Location</div></div>"
          "<div class='kpi'><div class='kv'>%d</div><div class='kl'>Complexity</div></div>"
          "<div class='kpi'><div class='kv'>%d</div><div class='kl'>Lines</div></div>"
          "<div class='kpi'><div class='kv'>%d</div><div class='kl'>Direct callers</div></div>"
          "<div class='kpi'><div class='kv'>%d</div><div class='kl'>Blast radius</div></div>"
          "</div>" % (_e(e["file"]), e["line"], e["complexity"], e["loc"], len(callers), blast)
        + "<div class='card'><h3>What it is</h3>" + doc + "</div>"
        + "<div class='grid2'><div class='card'><h3>Who calls this</h3>" + callers_t + "</div>"
        + "<div class='card'><h3>What this calls</h3>" + callees_t + "</div></div>"
    )


def ask_page(a, base, q="", use_llm=False):
    sq = a.index.get("suggested_questions", [])
    chips = "".join("<a class='chip' href='%s/ask?q=%s'>%s</a>"
                    % (base, html.escape(s, quote=True).replace(' ', '%20'), _e(s)) for s in sq)
    llm_on = llm.available()
    toggle = ""
    if llm_on:
        checked = "checked" if use_llm else ""
        toggle = ("<label class='llm'><input type='checkbox' name='llm' value='1' %s "
                  "onchange='this.form.submit()'> Use local LLM (%s) for a written explanation</label>"
                  % (checked, _e(llm.MODEL)))
    else:
        toggle = ("<div class='muted' style='font-size:12px;margin-top:6px'>Tip: run Ollama "
                  "(<code>ollama serve</code> + <code>ollama pull qwen2.5-coder</code>) to enable "
                  "AI-written explanations here. Built-in answers work without it.</div>")
    result = ""
    if q:
        r = qa.answer(a.index, q)
        ai_html = ""
        if use_llm and llm_on:
            try:
                ctx = llm.build_context(a.index, r)
                ans = llm.explain(q, ctx)
                ai_html = ("<div class='card ai'><h3>AI explanation <span class='muted'>(%s)</span></h3>"
                           "<div class='doc'>%s</div></div>" % (_e(llm.MODEL), _e(ans)))
            except Exception as exc:
                ai_html = "<div class='card'><p class='muted'>LLM call failed: %s</p></div>" % _e(exc)
        result = ai_html + "<div class='card'><h3>From the code graph</h3><p>%s</p>" % _e(r.get("answer", ""))
        ent = r.get("entity")
        if ent:
            result += "<p><a href='%s/function/%s'>Open %s &rarr;</a></p>" % (base, ent["id"], _e(ent["name"]))
        for key, title in (("callers", "Callers"), ("callees", "Callees")):
            if r.get(key):
                result += "<h4>%s</h4>" % title + _result_table(r[key], base)
        if r.get("results"):
            result += _result_table(r["results"], base)
        result += "</div>"
    return (
        "<h1>Ask the Code</h1>"
        "<p class='lead'>Plain-English questions about this codebase. Try "
        "&ldquo;what does X do&rdquo;, &ldquo;who calls X&rdquo;, &ldquo;where is X&rdquo;, "
        "&ldquo;what is in &lt;file&gt;&rdquo;. Answers come from the code graph; turn on the "
        "local LLM for a written explanation.</p>"
        "<form method='get' action='%s/ask'>"
        "<div style='display:flex;gap:10px'>"
        "<input name='q' value='%s' placeholder='Ask anything...' style='flex:1' autofocus>"
        "<button type='submit'>Ask</button></div>%s</form>"
        % (base, html.escape(q, quote=True), toggle)
        + "<div class='chips'>" + chips + "</div>"
        + result
    )


def _result_table(rows, base):
    return _table(["Name", "Type", "File", "Line", "Callers"],
                  [["<a href='%s/function/%s'>%s</a>" % (base, r["id"], _e(r["name"])),
                    r["type"], r["file"], r["line"], r.get("callers", 0)] for r in rows])


def risks_page(a):
    from .report import render_html  # reuse the rich risk rendering blocks
    r = a.risks
    s = r["summary"]
    summ = _bars({k.replace("_", " ").title(): v for k, v in s.items()}, "#e53e3e")
    dc = r["dead_code"]
    body = "<div class='card'>" + summ + "</div>"
    body += _risk_card("God Objects", ["Class", "File", "Line", "Methods"],
                       [[x["name"], x["file"], x["line"], x["methods"]] for x in r["god_objects"]])
    body += _risk_card("Dead code (unused private symbols): %d" % dc["count"],
                       ["Function", "File", "Line", "LOC"],
                       [[x["name"], x["file"], x["line"], x["loc"]] for x in dc["items"]])
    body += _risk_card("High Complexity (>15)", ["Function", "File", "Line", "Complexity"],
                       [[x["name"], x["file"], x["line"], x["complexity"]] for x in r["high_complexity"]])
    body += _risk_card("Long Methods (>100 LOC)", ["Function", "File", "Line", "LOC"],
                       [[x["name"], x["file"], x["line"], x["loc"]] for x in r["long_methods"]])
    body += _risk_card("Shotgun Surgery", ["Function", "File", "Line", "Caller Files"],
                       [[x["name"], x["file"], x["line"], x["called_from_files"]] for x in r["shotgun_surgery"]])
    return "<h1>Risks</h1><p class='lead'>Architecture smells worth a closer look.</p>" + body


def _risk_card(title, headers, rows):
    return "<div class='card'><h3>%s</h3>%s</div>" % (_e(title), _table(headers, rows))


def deps_page(a):
    dep = a.dependencies
    circ = dep["circular_dependencies"]
    circ_html = ("".join("<li>%s</li>" % _e(" -> ".join(c) + " -> " + c[0]) for c in circ)
                 if circ else "<p class='muted'>No circular dependencies.</p>")
    return ("<h1>Dependencies</h1>"
            "<p class='lead'>%d internal modules, %d external packages, %d circular.</p>"
            % (dep["internal_modules"], dep["external_dependencies"], dep["circular_dependency_count"])
            + "<div class='grid2'><div class='card'><h3>Most Depended-On</h3>"
            + _table(["Module", "Dependents"], [[x["module"], x["depended_on_by"]] for x in dep["most_depended_on"]])
            + "</div><div class='card'><h3>Top External Packages</h3>"
            + _table(["Package", "Sites"], [[x["package"], x["import_sites"]] for x in dep["top_external"]])
            + "</div></div><div class='card'><h3>Circular Dependencies</h3><ul>" + circ_html + "</ul></div>")


def git_page(a):
    g = a.git
    if not g.get("available"):
        return "<h1>History &amp; Owners</h1><p class='muted'>No git history for this source.</p>"
    return ("<h1>History &amp; Owners</h1>"
            "<p class='lead'>%d commits, %d contributors, bus factor <b>%s</b> (%s &rarr; %s).</p>"
            % (g["total_commits"], g["contributors"], g["project_bus_factor"],
               _e(g.get("first_commit")), _e(g.get("last_commit")))
            + "<div class='grid2'><div class='card'><h3>Top Contributors</h3>"
            + _table(["Author", "Commits"], [[x["author"], x["commits"]] for x in g["top_contributors"]])
            + "</div><div class='card'><h3>Most-Churned Files</h3>"
            + _table(["File", "Commits"], [[x["file"], x["commits"]] for x in g["file_churn"]])
            + "</div></div><div class='card'><h3>Knowledge-Risk Files (single owner)</h3>"
            + _table(["File", "Owner", "Ownership %", "Commits"],
                     [[x["file"], x["sole_owner"], x["ownership_pct"], x["commits"]] for x in g["knowledge_risk_files"]])
            + "</div>")


def hotspots_page(a):
    return ("<h1>Hotspots</h1>"
            "<p class='lead'>Files that are both complex and frequently changed &mdash; refactor here first.</p>"
            "<div class='card'>"
            + _table(["File", "Max Complexity", "Commits", "Hotspot Score"],
                     [[x["file"], x["max_complexity"], x["commits"], x["hotspot_score"]] for x in a.hotspots])
            + "</div>")


def _transitive_callers(ents, eid):
    seen, stack = set(), [eid]
    while stack:
        n = stack.pop()
        for c in ents.get(n, {}).get("callers", []):
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return len(seen)


_GRAPH_JS = """
<script>
(function(){
  var cv=document.getElementById('depgraph'); if(!cv||!window.GRAPH) return;
  var ctx=cv.getContext('2d'), tip=document.getElementById('gtip'); var W=cv.width,H=cv.height;
  var pal=['#4f86f7','#9f7aea','#1f9d55','#d69e2e','#e53e3e','#38b2ac','#ed64a6','#dd6b20','#667eea','#48bb78','#f56565','#4fd1c5'];
  var nodes=GRAPH.nodes.map(function(n){return {id:n.id,label:n.label,comm:n.community||0,
    r:Math.max(4,Math.min(22,3+Math.sqrt((n.entities||1))*1.6)),
    x:W/2+(Math.random()-0.5)*W*0.6,y:H/2+(Math.random()-0.5)*H*0.6,vx:0,vy:0,info:n,
    color:pal[((n.community||0)%pal.length+pal.length)%pal.length]};});
  var idx={}; nodes.forEach(function(n,i){idx[n.id]=i;});
  var links=GRAPH.links.filter(function(l){return l.source in idx&&l.target in idx;})
    .map(function(l){return {s:idx[l.source],t:idx[l.target],type:l.type};});
  var scale=1,ox=0,oy=0,drag=null,pan=false,lx=0,ly=0,hover=null,hlq='';
  function tick(){for(var i=0;i<nodes.length;i++){var a=nodes[i];
    for(var j=i+1;j<nodes.length;j++){var b=nodes[j];var dx=a.x-b.x,dy=a.y-b.y,d2=dx*dx+dy*dy+0.01,d=Math.sqrt(d2);
      var f=1500/d2,fx=dx/d*f,fy=dy/d*f;a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy;}}
    links.forEach(function(l){var a=nodes[l.s],b=nodes[l.t];var dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)+0.01;
      var f=(d-95)*0.012,fx=dx/d*f,fy=dy/d*f;a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy;});
    nodes.forEach(function(n){n.vx+=(W/2-n.x)*0.0009;n.vy+=(H/2-n.y)*0.0009;
      if(n!==drag){n.x+=n.vx*0.85;n.y+=n.vy*0.85;}n.vx*=0.86;n.vy*=0.86;});}
  function draw(){ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,W,H);ctx.setTransform(scale,0,0,scale,ox,oy);
    ctx.lineWidth=0.6/scale;links.forEach(function(l){var a=nodes[l.s],b=nodes[l.t];
      ctx.strokeStyle=l.type==='import'?'rgba(79,134,247,0.25)':'rgba(159,122,234,0.25)';
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();});
    nodes.forEach(function(n){var m=hlq&&n.id.toLowerCase().indexOf(hlq)>=0;
      ctx.beginPath();ctx.arc(n.x,n.y,n.r,0,6.2832);ctx.fillStyle=n.color;
      ctx.globalAlpha=(hover&&hover!==n)||(hlq&&!m)?0.35:1;ctx.fill();ctx.globalAlpha=1;
      ctx.lineWidth=(m?2.5:1)/scale;ctx.strokeStyle=m?'#fff':'#0f1419';ctx.stroke();
      if(scale>1.1||n.r>=12||m){ctx.fillStyle='#cbd5e1';ctx.font=(11/scale)+'px sans-serif';ctx.fillText(n.label,n.x+n.r+2,n.y+3);}});}
  function loop(){tick();draw();requestAnimationFrame(loop);}loop();
  window.hl=function(v){hlq=(v||'').toLowerCase();};
  function tw(ev){var rc=cv.getBoundingClientRect();var sx=cv.width/rc.width,sy=cv.height/rc.height;
    return {x:((ev.clientX-rc.left)*sx-ox)/scale,y:((ev.clientY-rc.top)*sy-oy)/scale,px:ev.clientX-rc.left,py:ev.clientY-rc.top};}
  function pick(p){for(var i=nodes.length-1;i>=0;i--){var n=nodes[i];var dx=n.x-p.x,dy=n.y-p.y;if(dx*dx+dy*dy<=(n.r+3)*(n.r+3))return n;}return null;}
  cv.addEventListener('mousedown',function(ev){var p=tw(ev),n=pick(p);if(n){drag=n;}else{pan=true;lx=ev.clientX;ly=ev.clientY;}});
  window.addEventListener('mousemove',function(ev){var p=tw(ev);
    if(drag){drag.x=p.x;drag.y=p.y;drag.vx=0;drag.vy=0;}
    else if(pan){ox+=ev.clientX-lx;oy+=ev.clientY-ly;lx=ev.clientX;ly=ev.clientY;}
    else{var n=pick(p);hover=n;if(n){tip.style.display='block';tip.style.left=(p.px+12)+'px';tip.style.top=(p.py+8)+'px';
      tip.innerHTML='<b>'+n.info.id+'</b><br>'+(n.info.entities||0)+' entities, '+(n.info.loc||0)+' LOC, '+(n.info.degree||0)+' connections';}else tip.style.display='none';}});
  window.addEventListener('mouseup',function(){drag=null;pan=false;});
  cv.addEventListener('wheel',function(ev){ev.preventDefault();var p=tw(ev),f=ev.deltaY<0?1.1:0.9,ns=Math.max(0.2,Math.min(5,scale*f));
    ox=p.px-(p.px-ox)*(ns/scale);oy=p.py-(p.py-oy)*(ns/scale);scale=ns;},{passive:false});
})();
</script>
"""

_LAYOUT = """<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{repo} - Codebase Intelligence</title><style>
*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0f1419;color:#e6edf3;line-height:1.5}}
.shell{{display:flex;min-height:100vh}}
.side{{width:230px;flex-shrink:0;background:#141a22;border-right:1px solid #2a3340;padding:18px 0;position:sticky;top:0;height:100vh;overflow:auto}}
.brand{{padding:0 18px 14px;border-bottom:1px solid #2a3340;margin-bottom:10px}}
.brand .r{{font-weight:700;font-size:15px;word-break:break-word}}
.brand .g{{display:inline-block;margin-top:6px;padding:2px 10px;border-radius:6px;color:#fff;font-weight:700;font-size:12px;background:{gcolor}}}
.side a{{display:block;padding:10px 18px;color:#b9c4d0;text-decoration:none;font-size:14px;border-left:3px solid transparent}}
.side a:hover{{background:#1a2029;color:#fff}}.side a.on{{background:#1a2029;color:#fff;border-left-color:#4f86f7}}
.dl{{padding:12px 18px;border-top:1px solid #2a3340;margin-top:10px}}
.dl a{{display:inline-block;padding:6px 0;color:#9ecbff;font-size:13px;border:0}}
.main{{flex:1;padding:26px 34px;max-width:1180px}}
h1{{font-size:24px;margin:0 0 6px}}h3{{font-size:15px;margin:0 0 10px;color:#cbd5e1}}h4{{margin:16px 0 6px;color:#cbd5e1}}
.lead{{color:#8b97a7;margin:0 0 18px}}.muted{{color:#8b97a7}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin:14px 0}}
.kpi{{background:#1a2029;border:1px solid #2a3340;border-radius:10px;padding:14px}}
.kv{{font-size:22px;font-weight:700}}.kl{{color:#8b97a7;font-size:12px;text-transform:uppercase;letter-spacing:.04em;margin-top:3px}}
.card{{background:#1a2029;border:1px solid #2a3340;border-radius:11px;padding:18px;margin:14px 0}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}@media(max-width:900px){{.grid2{{grid-template-columns:1fr}}.side{{width:180px}}}}
table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{text-align:left;padding:7px 9px;border-bottom:1px solid #2a3340}}
th{{color:#8b97a7;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}tr:hover td{{background:#222a35}}
a{{color:#4f86f7}}td a{{color:#9ecbff}}
input,button{{padding:10px 13px;border-radius:9px;border:1px solid #2a3340;background:#0f1419;color:#e6edf3;font-size:14px}}
button{{background:#4f86f7;color:#fff;border:0;font-weight:600;cursor:pointer}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0}}
.chip{{display:inline-block;padding:7px 12px;background:#222a35;border:1px solid #2a3340;border-radius:18px;color:#9ecbff;text-decoration:none;font-size:13px;cursor:pointer}}
.chip:hover{{background:#2c3644}}
.bars{{display:flex;flex-direction:column;gap:7px}}.bar-row{{display:grid;grid-template-columns:150px 1fr 48px;align-items:center;gap:10px;font-size:12px}}
.bar-label{{color:#8b97a7}}.bar-track{{background:#222a35;border-radius:5px;height:13px;overflow:hidden}}.bar-fill{{display:block;height:100%}}.bar-val{{text-align:right}}
.filelist{{columns:2;font-size:13px;color:#b9c4d0}}.doc{{white-space:pre-wrap;font-size:14px}}
.empty{{color:#8b97a7;font-style:italic;font-size:13px}}code{{background:#0f1419;padding:2px 6px;border-radius:5px}}
</style></head><body><div class='shell'>
<nav class='side'><div class='brand'><div class='r'>{repo}</div><div class='g'>Health {score}/100 &middot; {grade}</div></div>
{nav}
<div class='dl'><div class='muted' style='font-size:11px;text-transform:uppercase'>Share</div>
<a href='{base}/download.html'>Download HTML report</a><br><a href='{base}/download.json'>Download JSON</a></div>
</nav>
<main class='main'>{inner}</main></div></body></html>"""
