#!/usr/bin/env python3
"""Interactive multi-page local web app for the codebase analysis engine.

Zero third-party dependencies. Analyze a path, a dragged folder, or a Git URL;
then navigate Overview / Graph / Modules / Functions / Ask / Risks / etc. on
separate pages. Each analysis also offers downloadable HTML + JSON reports.

    python scripts/serve.py            # open http://127.0.0.1:8500
"""
import argparse
import base64
import hashlib
import html
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from analysis import analyze_repository            # noqa: E402
from analysis.report import render_html            # noqa: E402
from analysis import webapp                         # noqa: E402
from ast_parser.parser import LANGUAGE_MAP          # noqa: E402

ROOT = "."
MAX_UPLOAD_FILES = 4000
MAX_FILE_BYTES = 2_000_000
CACHE = {}   # id -> (analysis, label)


# ----------------------------- landing page -----------------------------

def landing(body="", value=""):
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Codebase Intelligence</title><style>"
        "*{box-sizing:border-box}body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0f1419;color:#e6edf3}"
        ".top{padding:26px 34px;background:linear-gradient(135deg,#1a2233,#0f1419);border-bottom:1px solid #2a3340}"
        ".top h1{margin:0;font-size:22px}.top p{margin:5px 0 0;color:#8b97a7;font-size:13px}"
        ".panels{display:flex;gap:14px;padding:22px 34px;flex-wrap:wrap}"
        ".card{flex:1;min-width:300px;background:#1a2029;border:1px solid #2a3340;border-radius:12px;padding:18px}"
        ".card h3{margin:0 0 12px;font-size:14px;color:#cbd5e1}"
        "form{display:flex;gap:10px;flex-wrap:wrap;margin:0}"
        "input[type=text]{flex:1;min-width:190px;padding:11px 14px;border-radius:9px;border:1px solid #2a3340;background:#0f1419;color:#e6edf3;font-size:14px}"
        "button{padding:11px 20px;border:0;border-radius:9px;background:#4f86f7;color:#fff;font-size:14px;font-weight:600;cursor:pointer}"
        "#drop{border:2px dashed #2a3340;border-radius:10px;padding:24px;text-align:center;color:#8b97a7;cursor:pointer}"
        "#drop.over{border-color:#4f86f7;color:#cbd5e1}"
        ".examples{color:#8b97a7;font-size:12px;margin-top:10px}.examples code{background:#0f1419;padding:2px 7px;border-radius:5px;cursor:pointer;color:#9ecbff}"
        ".err{margin:0 34px 24px;padding:16px;background:#3a1a1f;border:1px solid #e53e3e;border-radius:9px;color:#ffc9c9;font-size:13px;white-space:pre-wrap;font-family:monospace}"
        "#busy{display:none;padding:14px 34px;color:#9ecbff}"
        "</style></head><body>"
        "<div class='top'><h1>Codebase Intelligence</h1>"
        "<p>Understand any codebase fast. Analyze a folder, a path, or a Git URL, then explore it page by page and ask it questions.</p></div>"
        "<div class='panels'>"
        "<div class='card'><h3>Analyze by path</h3>"
        "<form method='get' action='/analyze'><input type='text' name='path' placeholder='/path/to/repo' value='" + html.escape(value) + "'>"
        "<button type='submit'>Analyze</button></form>" + _examples() + "</div>"
        "<div class='card'><h3>Or drag a folder here</h3>"
        "<div id='drop'>Drop a project folder, or click to choose one</div>"
        "<input id='dir' type='file' webkitdirectory directory multiple style='display:none'></div>"
        "<div class='card'><h3>Or analyze a Git repo URL</h3>"
        "<form method='get' action='/analyze'><input type='text' name='giturl' placeholder='https://github.com/user/repo'>"
        "<button type='submit'>Clone &amp; Analyze</button></form>"
        "<div class='examples'>Public repos. Shallow clone; large repos take a moment.</div></div>"
        "</div><div id='busy'>Analyzing... this can take a few seconds.</div>" + body
        + "<script>"
        "var drop=document.getElementById('drop'),dir=document.getElementById('dir');"
        "drop.onclick=function(){dir.click()};"
        "drop.ondragover=function(e){e.preventDefault();drop.classList.add('over')};"
        "drop.ondragleave=function(){drop.classList.remove('over')};"
        "drop.ondrop=function(e){e.preventDefault();drop.classList.remove('over');if(e.dataTransfer.items)collect(e.dataTransfer.items)};"
        "dir.onchange=function(){send([].slice.call(dir.files))};"
        "function collect(items){var ent=[];for(var i=0;i<items.length;i++){var it=items[i].webkitGetAsEntry&&items[i].webkitGetAsEntry();if(it)ent.push(it)}"
        "var files=[],pending=0;function walk(en,p){if(en.isFile){pending++;en.file(function(f){f._rel=p+f.name;files.push(f);if(--pending===0)send(files)})}"
        "else if(en.isDirectory){var rd=en.createReader();rd.readEntries(function(es){for(var j=0;j<es.length;j++)walk(es[j],p+en.name+'/')})}}"
        "for(var k=0;k<ent.length;k++)walk(ent[k],'');setTimeout(function(){if(files.length&&pending===0)send(files)},900)}"
        "function send(files){if(!files.length)return;document.getElementById('busy').style.display='block';"
        "var fd=new FormData(),n=0;files.forEach(function(f){var rel=f.webkitRelativePath||f._rel||f.name;"
        "if(/\\.(py|js|jsx|ts|tsx|go|rs|java|rb|php|c|cpp|cs)$/.test(rel)){fd.append('files',f,rel);n++}});"
        "if(!n){document.getElementById('busy').textContent='No supported source files found.';return}"
        "fetch('/upload',{method:'POST',body:fd}).then(function(r){if(r.redirected){location.href=r.url;return}return r.text()})"
        ".then(function(t){if(t){document.open();document.write(t);document.close()}});}"
        "</script></body></html>"
    )


def _examples():
    rows = []
    try:
        for name in sorted(os.listdir(ROOT)):
            full = os.path.join(ROOT, name)
            if os.path.isdir(full) and not name.startswith("."):
                rows.append("<code onclick=\"document.querySelector('[name=path]').value='"
                            + html.escape(full) + "'\">" + html.escape(name) + "</code>")
    except OSError:
        pass
    return ("<div class='examples'>Folders: " + " ".join(rows[:25]) + "</div>") if rows else ""


# ----------------------------- store + routing --------------------------

def _store(analysis, label):
    aid = hashlib.sha256((analysis.repo_path + str(time.time())).encode()).hexdigest()[:12]
    CACHE[aid] = (analysis, label)
    return aid


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    # -- GET --
    def do_GET(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        qs = parse_qs(u.query)

        if not parts or u.path == "/":
            self._html(landing()); return

        if parts[0] == "analyze":
            path = (qs.get("path") or [""])[0].strip()
            giturl = (qs.get("giturl") or [""])[0].strip()
            if giturl:
                self._analyze_git(giturl); return
            if path:
                self._analyze_path(path); return
            self._html(landing()); return

        if parts[0] == "view" and len(parts) >= 2:
            self._view(parts[1], parts[2:], qs); return

        self.send_response(404); self.end_headers()

    # -- POST (folder upload) --
    def do_POST(self):
        if urlparse(self.path).path != "/upload":
            self.send_response(404); self.end_headers(); return
        try:
            files = self._parse_multipart()
            if not files:
                self._html(landing("<div class='err'>No source files received.</div>")); return
            with tempfile.TemporaryDirectory() as tmp:
                for rel, data in files:
                    rel = rel.replace("\\", "/").lstrip("/")
                    if ".." in rel.split("/"):
                        continue
                    dest = os.path.join(tmp, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, "wb") as f:
                        f.write(data)
                a = analyze_repository(tmp, top_n=20, with_git=False)
                label = files[0][0].replace("\\", "/").split("/")[0] or "uploaded"
                self._redirect("/view/%s/overview" % _store(a, label))
        except Exception:
            self._html(landing("<div class='err'>Upload failed:\n" + html.escape(traceback.format_exc()) + "</div>"))

    # -- analysis helpers --
    def _analyze_path(self, path):
        target = path if os.path.isabs(path) else os.path.join(ROOT, path)
        if not os.path.isdir(target):
            self._html(landing("<div class='err'>Not a directory: " + html.escape(target) + "</div>", value=path)); return
        try:
            a = analyze_repository(target, top_n=20, with_git=True)
            self._redirect("/view/%s/overview" % _store(a, os.path.basename(target.rstrip("/\\")) or target))
        except Exception:
            self._html(landing("<div class='err'>Analysis failed:\n" + html.escape(traceback.format_exc()) + "</div>", value=path))

    def _analyze_git(self, url):
        if not re.match(r"^https?://[\w.@:/\-~]+$", url):
            self._html(landing("<div class='err'>Only http(s) Git URLs are allowed.</div>")); return
        try:
            tmp = tempfile.mkdtemp(prefix="cbi_")
            proc = subprocess.run(["git", "clone", "--depth", "1", url, tmp],
                                  capture_output=True, text=True, timeout=240)
            if proc.returncode != 0:
                self._html(landing("<div class='err'>git clone failed:\n" + html.escape(proc.stderr[-1500:]) + "</div>")); return
            a = analyze_repository(tmp, top_n=20, with_git=True)
            label = url.rstrip("/").split("/")[-1].replace(".git", "") or "repo"
            self._redirect("/view/%s/overview" % _store(a, label))
        except FileNotFoundError:
            self._html(landing("<div class='err'>git is not installed or not on PATH.</div>"))
        except subprocess.TimeoutExpired:
            self._html(landing("<div class='err'>git clone timed out.</div>"))
        except Exception:
            self._html(landing("<div class='err'>Git analysis failed:\n" + html.escape(traceback.format_exc()) + "</div>"))

    # -- view router --
    def _view(self, aid, rest, qs):
        item = CACHE.get(aid)
        if not item:
            self._html(landing("<div class='err'>That analysis expired (server restarted). Run it again.</div>")); return
        a, label = item
        base = "/view/" + aid
        page = rest[0] if rest else "overview"

        if page == "download.html":
            self._download(render_html(a), "text/html", label + "_report.html"); return
        if page == "download.json":
            self._download(json.dumps(a.to_dict(), indent=2), "application/json", label + "_report.json"); return
        if page == "function" and len(rest) >= 2:
            inner = webapp.function_detail_page(a, rest[1], base)
            self._html(webapp.page(a, base, "functions", inner, label)); return

        renderers = {
            "overview": lambda: webapp.overview_page(a),
            "graph": lambda: webapp.graph_page(a),
            "modules": lambda: webapp.modules_page(a, base),
            "functions": lambda: webapp.functions_page(a, base),
            "ask": lambda: webapp.ask_page(a, base, (qs.get("q") or [""])[0], use_llm=bool(qs.get("llm"))),
            "risks": lambda: webapp.risks_page(a),
            "dependencies": lambda: webapp.deps_page(a),
            "git": lambda: webapp.git_page(a),
            "hotspots": lambda: webapp.hotspots_page(a),
        }
        if page not in renderers:
            page = "overview"
        self._html(webapp.page(a, base, page, renderers[page](), label))

    # -- multipart --
    def _parse_multipart(self):
        ctype = self.headers.get("Content-Type", "")
        if "boundary=" not in ctype:
            return []
        boundary = ("--" + ctype.split("boundary=", 1)[1].strip()).encode()
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        out = []
        for part in body.split(boundary):
            if b"\r\n\r\n" not in part:
                continue
            head, data = part.split(b"\r\n\r\n", 1)
            data = data[:-2] if data.endswith(b"\r\n") else data
            hs = head.decode("utf-8", "replace")
            if 'name="files"' not in hs or "filename=" not in hs:
                continue
            fname = hs.split("filename=", 1)[1].split("\r\n", 1)[0].strip().strip('"')
            if not fname or os.path.splitext(fname)[1] not in LANGUAGE_MAP or len(data) > MAX_FILE_BYTES:
                continue
            out.append((fname, data))
            if len(out) >= MAX_UPLOAD_FILES:
                break
        return out

    # -- responders --
    def _html(self, content):
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def _download(self, content, ctype, filename):
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Disposition", "attachment; filename=\"%s\"" % filename)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def _redirect(self, loc):
        self.send_response(303); self.send_header("Location", loc)
        self.send_header("Content-Length", "0"); self.end_headers()


def _make_server(host, port):
    if host in ("127.0.0.1", "localhost", "::", "::1", ""):
        try:
            class Dual(ThreadingHTTPServer):
                address_family = socket.AF_INET6

                def server_bind(self):
                    try:
                        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    except (AttributeError, OSError):
                        pass
                    super().server_bind()
            return Dual(("::", port), Handler)
        except OSError:
            pass
    return ThreadingHTTPServer((host or "127.0.0.1", port), Handler)


def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8500)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    ROOT = os.path.abspath(args.root)
    server = _make_server(args.host, args.port)
    print("Codebase Intelligence UI is running.")
    print("  Open in your browser:  http://127.0.0.1:%d" % args.port)
    print("  Root:", ROOT)
    print("  Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
