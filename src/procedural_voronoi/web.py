"""Loopback-only browser UI using the same library pipeline."""
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import json
from urllib.parse import urlparse
from .config import presets, resolve
from .pipeline import generate
HTML = '''<!doctype html><html><meta charset="utf-8"><title>Voronoi mesh studio</title>
<style>body{font:16px system-ui;background:#101b28;color:#e7eff5;max-width:1100px;margin:40px auto}main{display:grid;grid-template-columns:280px 1fr;gap:30px}label{display:block;margin:12px 0}input,select,button{padding:8px;width:95%;box-sizing:border-box}button{background:#64dcc8;border:0;font-weight:bold;cursor:pointer}img{width:100%}a{color:#64dcc8}#status{white-space:pre-wrap}</style>
<h1>Voronoi mesh studio</h1><p>Local deterministic geometry · David Cannan (Cdaprod)</p><main><form id="f">
<label>Preset<select name="preset" id="presets"></select></label>
<label>Seed<input name="seed" type="number" value="20261110"></label>
<label>Cells<input name="cells" type="number" min="2" max="1000" value="55"></label>
<label>Relief (mm)<input name="relief" type="number" step="0.1" value="1.8"></label>
<label>Surface mode<select name="mode"><option>raised</option><option>inverted</option><option>flat</option></select></label>
<label>Input geometry<select name="input"><option>plane</option><option>box</option></select></label>
<label>Output format<select name="format"><option>stl</option><option>obj</option><option>glb</option><option>3mf</option></select></label>
<label>Preview quality<select name="quality"><option>preview</option><option>high</option></select></label><button>Generate and export</button>
<p>Imported files: use the CLI with a local STL/OBJ/GLB path. This browser does not upload files.</p></form><section><img id="preview" alt="Generated geometry preview" hidden><p id="status">Choose parameters and generate.</p><a id="download" hidden>Download exported mesh</a></section></main>
<script>
const f=document.getElementById('f'), presets=document.getElementById('presets'), status=document.getElementById('status'), preview=document.getElementById('preview'), download=document.getElementById('download');
fetch('/api/presets').then(r=>r.json()).then(d=>{for(let n of Object.keys(d)){let o=document.createElement('option');o.value=o.textContent=n;presets.append(o)} const sync=()=>{const c=d[presets.value].config;for(const k of ['seed','cells','relief','mode','input','quality']){f.elements[k].value=c[k]}};presets.onchange=sync;sync()});
f.onsubmit=async e=>{e.preventDefault();status.textContent='Generating…';let d=Object.fromEntries(new FormData(f));d.seed=Number(d.seed);d.cells=Number(d.cells);d.relief=Number(d.relief);try{let r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});let j=await r.json();if(!r.ok)throw Error(j.error);preview.src=j.preview;preview.hidden=false;download.href=j.mesh;download.hidden=false;status.textContent='Validation: '+(j.pass?'passed':'failed — inspect validation JSON');}catch(e){status.textContent=e.message}};
</script></html>'''
def handler(output):
    root = Path(output).resolve(); root.mkdir(parents=True, exist_ok=True)
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, mime="application/json"):
            if isinstance(body, dict):
                body = json.dumps(body).encode()
            if isinstance(body, str):
                body = body.encode()
            self.send_response(status); self.send_header("Content-Type", mime); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                return self.reply(200, HTML, "text/html; charset=utf-8")
            if path == "/api/presets":
                return self.reply(200, {k: {"description": v["description"], "config": resolve(k)} for k, v in presets().items()})
            if path.startswith("/files/"):
                p = (root/path[len("/files/"):]).resolve()
                if root not in p.parents or not p.is_file():
                    return self.reply(404, {"error": "File not found"})
                mime = "image/png" if p.suffix == ".png" else "application/octet-stream"
                return self.reply(200, p.read_bytes(), mime)
            self.reply(404, {"error": "Not found"})
        def do_POST(self):
            if self.path != "/api/generate":
                return self.reply(404, {"error": "Not found"})
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size < 4096:
                    raise ValueError("Request must be smaller than 4096 bytes")
                a = json.loads(self.rfile.read(size))
                if a.get("input") not in ["plane", "box"]:
                    raise ValueError("Browser input must be plane or box; use CLI for imports")
                import hashlib
                name = hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest()[:16]
                fmt = a.pop("format")
                preset = a.pop("preset")
                result = generate(root/name, preset, overrides={**a, "formats": [fmt]})
                self.reply(200, {"preview": f"/files/{name}/preview.png", "mesh": f"/files/{name}/mesh.{fmt}", "pass": result["validation_pass"]})
            except (ValueError, OSError, KeyError, TypeError) as e:
                self.reply(400, {"error": str(e)})
    return Handler

def serve(port=8765, output="browser-output"):
    print(f"Open http://127.0.0.1:{port} (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", port), handler(output)).serve_forever()
