"""Static, pre-laid-out dependency-graph widget (canvas, zero-dependency).

The layout is computed ONCE on the server (deterministic force-directed) and
embedded as fixed x/y coordinates. The browser only draws and handles
pan / zoom / drag / hover / select / legend-filter / search - there is NO
continuous animation, so nodes never drift on their own.
"""
from __future__ import annotations

import json
import math
import random

PALETTE = [
    "#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#B07AA1", "#76B7B2",
    "#EDC948", "#FF9DA7", "#9C755F", "#72B7B2", "#86BCB6", "#D37295",
    "#FABFD2", "#B6992D", "#499894", "#D7B5A6", "#79706E", "#8CD17D",
]


def _layout(nodes, links, iterations=420, seed=42):
    """Deterministic force-directed layout. Mutates nodes with x,y in [-W,W]."""
    n = len(nodes)
    if n == 0:
        return
    rnd = random.Random(seed)
    idx = {node["id"]: i for i, node in enumerate(nodes)}
    # seed positions in community clusters (stable, tidy start)
    comms = {}
    for node in nodes:
        comms.setdefault(node.get("community", -1), []).append(node)
    ncl = max(len(comms), 1)
    for ci, (_, group) in enumerate(sorted(comms.items())):
        cx = math.cos(ci / ncl * 6.2831853) * 380
        cy = math.sin(ci / ncl * 6.2831853) * 380
        for node in group:
            node["x"] = cx + rnd.uniform(-70, 70)
            node["y"] = cy + rnd.uniform(-70, 70)

    edges = [(idx[l["source"]], idx[l["target"]]) for l in links
             if l["source"] in idx and l["target"] in idx]

    area = 900.0 * 900.0
    k = math.sqrt(area / n)          # ideal edge length
    temp = 180.0
    cool = temp / (iterations + 1)

    px = [node["x"] for node in nodes]
    py = [node["y"] for node in nodes]

    for _ in range(iterations):
        dx = [0.0] * n
        dy = [0.0] * n
        # repulsion (O(n^2); n capped at ~160 so this is fast)
        for i in range(n):
            xi, yi = px[i], py[i]
            for j in range(i + 1, n):
                ddx = xi - px[j]
                ddy = yi - py[j]
                dist2 = ddx * ddx + ddy * ddy + 0.01
                dist = math.sqrt(dist2)
                force = (k * k) / dist2 * dist
                fx = ddx / dist * force
                fy = ddy / dist * force
                dx[i] += fx; dy[i] += fy
                dx[j] -= fx; dy[j] -= fy
        # attraction along edges
        for a, b in edges:
            ddx = px[a] - px[b]
            ddy = py[a] - py[b]
            dist = math.sqrt(ddx * ddx + ddy * ddy) + 0.01
            force = (dist * dist) / k
            fx = ddx / dist * force
            fy = ddy / dist * force
            dx[a] -= fx; dy[a] -= fy
            dx[b] += fx; dy[b] += fy
        # gentle gravity to centre
        for i in range(n):
            dx[i] -= px[i] * 0.012
            dy[i] -= py[i] * 0.012
        # apply with temperature cap
        for i in range(n):
            d = math.sqrt(dx[i] * dx[i] + dy[i] * dy[i]) + 0.01
            disp = min(d, temp)
            px[i] += dx[i] / d * disp
            py[i] += dy[i] / d * disp
        temp -= cool

    for i, node in enumerate(nodes):
        node["x"] = round(px[i], 1)
        node["y"] = round(py[i], 1)


def graph_widget(graph, communities=None, height=620, with_panel=True):
    communities = communities or []
    comm_name = {c["id"]: c["name"] for c in communities}
    nodes = [dict(nd) for nd in graph.get("nodes", [])]
    links = graph.get("links", [])
    iters = 400 if len(nodes) <= 60 else max(110, int(24000 / max(len(nodes), 1)))
    _layout(nodes, links, iterations=iters)

    comm_count = {}
    for nd in nodes:
        comm_count[nd.get("community", -1)] = comm_count.get(nd.get("community", -1), 0) + 1
    legend = []
    for cid in sorted(comm_count, key=lambda c: comm_count[c], reverse=True):
        color = PALETTE[(cid % len(PALETTE) + len(PALETTE)) % len(PALETTE)] if cid >= 0 else "#888"
        legend.append({"id": cid, "name": comm_name.get(cid, "misc"),
                       "color": color, "count": comm_count[cid]})

    payload = json.dumps({"nodes": nodes, "links": links, "legend": legend,
                          "palette": PALETTE})
    panel = _PANEL if with_panel else ""
    return _TEMPLATE.replace("__H__", str(height)).replace("__PANEL__", panel).replace(
        "__DATA__", payload)


_PANEL = """
    <div id='ginfo'>
      <h4>Click a node</h4>
      <div id='ginfo-body' class='gmuted'>Select a file to see its connections.</div>
    </div>"""

_TEMPLATE = """
<div class='gwrap'>
  <div class='gleft'>
    <input id='gsearch' placeholder='Search files...' autocomplete='off'>
    <div class='gctrls'>
      <button type='button' id='gfit'>Fit</button>
      <button type='button' id='greset'>Reset view</button>
    </div>
    <div id='glegend'></div>
    __PANEL__
  </div>
  <div class='gcanvaswrap'>
    <canvas id='gcanvas'></canvas>
    <div id='gtip'></div>
    <div id='ghint'>Drag a node to move it &middot; scroll to zoom &middot; drag background to pan</div>
  </div>
</div>
<style>
.gwrap{display:flex;border:1px solid #2a3340;border-radius:12px;overflow:hidden;background:#0f1419;height:__H__px}
.gleft{width:240px;flex-shrink:0;background:#141a22;border-right:1px solid #2a3340;display:flex;flex-direction:column;overflow:hidden}
.gleft #gsearch{margin:12px;width:calc(100% - 24px);padding:8px 10px;border-radius:7px;border:1px solid #2a3340;background:#0f1419;color:#e6edf3;font-size:13px}
.gctrls{display:flex;gap:6px;padding:0 12px 10px}
.gctrls button{flex:1;padding:6px 0;font-size:12px;border:1px solid #2a3340;background:#1a2029;color:#cbd5e1;border-radius:7px;cursor:pointer}
.gctrls button:hover{background:#222a35}
#glegend{padding:6px 10px;overflow-y:auto;max-height:240px;border-top:1px solid #2a3340}
.lg{display:flex;align-items:center;gap:8px;padding:4px 6px;border-radius:5px;cursor:pointer;font-size:12px}
.lg:hover{background:#222a35}.lg.off{opacity:.35}
.lg .dot{width:11px;height:11px;border-radius:50%;flex-shrink:0}
.lg .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#cbd5e1}
.lg .ct{color:#7a8696;font-size:11px}
#ginfo{flex:1;overflow-y:auto;padding:12px;border-top:1px solid #2a3340}
#ginfo h4{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:#8b97a7}
#ginfo-body{font-size:12px;line-height:1.6;color:#cbd5e1}
#ginfo-body b{color:#e6edf3}.gmuted{color:#8b97a7}
.nbr{display:block;padding:3px 6px;margin:2px 0;border-left:3px solid #333;border-radius:3px;font-size:12px;color:#9ecbff;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nbr:hover{background:#222a35}
.gcanvaswrap{position:relative;flex:1}
#gcanvas{width:100%;height:100%;display:block;cursor:grab;background:radial-gradient(circle at 50% 42%,#141c27,#0f1419)}
#gtip{position:absolute;display:none;pointer-events:none;background:#222a35;border:1px solid #3a4453;border-radius:7px;padding:7px 10px;font-size:12px;color:#e6edf3;max-width:260px;z-index:5}
#ghint{position:absolute;left:10px;bottom:8px;color:#5e6b7a;font-size:11px;pointer-events:none}
@media(max-width:760px){.gwrap{flex-direction:column;height:auto}.gleft{width:100%}.gcanvaswrap{height:440px}}
</style>
<script>
(function(){
var D=__DATA__;var LEG=D.legend,PAL=D.palette;
var cv=document.getElementById('gcanvas');if(!cv)return;var ctx=cv.getContext('2d');
var tip=document.getElementById('gtip');
function colr(c){return c>=0?PAL[((c%PAL.length)+PAL.length)%PAL.length]:'#888';}
var nodes=D.nodes.map(function(n){return {id:n.id,label:n.label,comm:(n.community==null?-1:n.community),
  deg:n.degree||0,ent:n.entities||1,loc:n.loc||0,cc:n.max_complexity||0,
  r:Math.max(5,Math.min(26,4+Math.sqrt((n.entities||1))*1.8)),
  x:n.x||0,y:n.y||0,color:colr(n.community==null?-1:n.community)};});
var idx={};nodes.forEach(function(n,i){idx[n.id]=i;});
var links=D.links.filter(function(l){return l.source in idx&&l.target in idx;})
  .map(function(l){return {s:idx[l.source],t:idx[l.target],type:l.type};});
var adj={};nodes.forEach(function(n){adj[n.id]=[];});
links.forEach(function(l){adj[nodes[l.s].id].push(nodes[l.t].id);adj[nodes[l.t].id].push(nodes[l.s].id);});

var DPR=window.devicePixelRatio||1,W=0,H=0;
function resize(){var r=cv.getBoundingClientRect();W=r.width;H=r.height;cv.width=W*DPR;cv.height=H*DPR;draw();}
var scale=1,ox=0,oy=0,drag=null,pan=false,lx=0,ly=0,sel=null,hideC={},hlids=null;
function active(n){return !hideC[n.comm];}
function isNbr(n){return sel&&adj[sel.id]&&adj[sel.id].indexOf(n.id)>=0;}

function draw(){
  ctx.setTransform(DPR,0,0,DPR,0,0);ctx.clearRect(0,0,W,H);
  ctx.translate(ox,oy);ctx.scale(scale,scale);
  ctx.lineWidth=0.8/scale;
  for(var i=0;i<links.length;i++){var a=nodes[links[i].s],b=nodes[links[i].t];
    if(!active(a)||!active(b))continue;
    var dim=(sel&&sel!==a&&sel!==b)||(hlids&&!hlids[a.id]&&!hlids[b.id]);
    ctx.strokeStyle=dim?'rgba(120,130,150,0.05)':(links[i].type==='import'?'rgba(120,150,210,0.32)':'rgba(180,150,210,0.32)');
    ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}
  for(var j=0;j<nodes.length;j++){var n=nodes[j];if(!active(n))continue;
    var hl=hlids?hlids[n.id]:false;var dim=(sel&&sel!==n&&!isNbr(n))||(hlids&&!hl);
    ctx.globalAlpha=dim?0.22:1;
    ctx.beginPath();ctx.arc(n.x,n.y,n.r,0,6.2832);ctx.fillStyle=n.color;ctx.fill();
    ctx.lineWidth=((n===sel||hl)?2.6:1)/scale;ctx.strokeStyle=(n===sel||hl)?'#fff':'rgba(0,0,0,0.5)';ctx.stroke();
    if(scale>0.9||n.r>=14||n===sel||hl){ctx.globalAlpha=dim?0.4:1;ctx.fillStyle='#e3eaf2';
      ctx.font='600 '+(11/Math.max(scale,0.6))+'px sans-serif';ctx.fillText(n.label,n.x+n.r+3,n.y+3.5);}
    ctx.globalAlpha=1;}
}
function fit(){var xs=nodes.filter(active);if(!xs.length)return;
  var a=1e9,b=1e9,c=-1e9,d=-1e9;xs.forEach(function(n){a=Math.min(a,n.x-n.r);b=Math.min(b,n.y-n.r);c=Math.max(c,n.x+n.r);d=Math.max(d,n.y+n.r);});
  var gw=c-a+80,gh=d-b+80;scale=Math.min(W/gw,H/gh,2.4)||1;
  ox=W/2-(a+c)/2*scale;oy=H/2-(b+d)/2*scale;draw();}
window.addEventListener('resize',resize);resize();setTimeout(fit,30);

document.getElementById('gfit').onclick=fit;
document.getElementById('greset').onclick=function(){scale=1;fit();};

var lw=document.getElementById('glegend');
function esc(s){return (s+'').replace(/[&<>]/g,function(m){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[m];});}
lw.innerHTML=LEG.map(function(g){return "<div class='lg' data-c='"+g.id+"'><span class='dot' style='background:"+g.color+"'></span>"
  +"<span class='nm'>"+esc(g.name)+"</span><span class='ct'>"+g.count+"</span></div>";}).join('');
lw.querySelectorAll('.lg').forEach(function(el){el.onclick=function(){var c=parseInt(el.dataset.c,10);
  hideC[c]=!hideC[c];el.classList.toggle('off',hideC[c]);draw();};});

var sb=document.getElementById('gsearch');
sb.oninput=function(){var q=sb.value.trim().toLowerCase();if(!q){hlids=null;draw();return;}
  hlids={};nodes.forEach(function(n){if(n.id.toLowerCase().indexOf(q)>=0)hlids[n.id]=true;});draw();};

var infoBody=document.getElementById('ginfo-body');
function select(n){sel=n;draw();if(!infoBody)return;
  var nb=(adj[n.id]||[]).slice(0,50);
  infoBody.innerHTML="<div><b>"+esc(n.id)+"</b></div>"
    +"<div class='gmuted'>"+n.ent+" entities &middot; "+n.loc+" LOC &middot; cc "+n.cc+" &middot; "+n.deg+" connections</div>"
    +"<h4 style='margin-top:10px'>Connected to ("+nb.length+")</h4>"
    +(nb.length?nb.map(function(id){return "<span class='nbr' data-id='"+esc(id)+"'>"+esc(id)+"</span>";}).join(''):"<span class='gmuted'>none</span>");
  infoBody.querySelectorAll('.nbr').forEach(function(el){el.onclick=function(){var t=nodes[idx[el.dataset.id]];if(t){select(t);ox=W/2-t.x*scale;oy=H/2-t.y*scale;draw();}};});}

function tw(ev){var r=cv.getBoundingClientRect();return {x:(ev.clientX-r.left-ox)/scale,y:(ev.clientY-r.top-oy)/scale,px:ev.clientX-r.left,py:ev.clientY-r.top};}
function pick(p){for(var i=nodes.length-1;i>=0;i--){var n=nodes[i];if(!active(n))continue;var dx=n.x-p.x,dy=n.y-p.y;if(dx*dx+dy*dy<=(n.r+4)*(n.r+4))return n;}return null;}
cv.addEventListener('mousedown',function(ev){var p=tw(ev),n=pick(p);if(n){drag=n;select(n);cv.style.cursor='grabbing';}else{pan=true;lx=ev.clientX;ly=ev.clientY;}});
window.addEventListener('mousemove',function(ev){var p=tw(ev);
  if(drag){drag.x=p.x;drag.y=p.y;draw();}
  else if(pan){ox+=ev.clientX-lx;oy+=ev.clientY-ly;lx=ev.clientX;ly=ev.clientY;draw();}
  else{var n=pick(p);if(n){tip.style.display='block';tip.style.left=(p.px+14)+'px';tip.style.top=(p.py+10)+'px';
    tip.innerHTML='<b>'+esc(n.id)+'</b><br>'+n.ent+' entities, '+n.deg+' connections';}else tip.style.display='none';}});
window.addEventListener('mouseup',function(){drag=null;pan=false;cv.style.cursor='grab';});
cv.addEventListener('wheel',function(ev){ev.preventDefault();var p=tw(ev),f=ev.deltaY<0?1.12:0.89,ns=Math.max(0.12,Math.min(7,scale*f));
  ox=p.px-(p.px-ox)*(ns/scale);oy=p.py-(p.py-oy)*(ns/scale);scale=ns;draw();},{passive:false});
})();
</script>
"""
