"""Backend: a zero-dependency HTTP server (Python standard library only).
   python -m evalkit.server [--port 8000]   then open http://127.0.0.1:8000
API:  GET /api/summary   GET /api/questions   GET /api/verdicts.csv
      POST /api/check    {question, answer}  -> sentence-by-sentence policy check of one answer
      POST /api/evaluate  (CSV text body)    -> re-run the whole evaluation on an uploaded file"""
import argparse, csv, io, json, mimetypes, os, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .data import load, load_text
from .pipeline import evaluate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = threading.Lock()
STATE = {}

def build_state(rows, kb_path, cfg):
    S, R, kb = evaluate(rows, kb_path, cfg)
    qs = [{"id": r["id"], "topic": r["topic"], "question": r["question"], "better": r["verdict"][0], "reason": r["verdict"][1],
           "cur": {k: r["cur"][k] for k in ("sentences", "sev", "words", "missing")},
           "new": {k: r["newa"][k] for k in ("sentences", "sev", "words", "missing")}} for r in R]
    STATE.update(S=S, questions=qs, kb=kb)

def check_answer(question, answer):
    a = STATE["kb"].analyse(question, answer)
    return {"sentences": a["sentences"], "severity": a["sev"], "missing": a["missing"], "words": a["words"], "filler_words": a["filler_words"]}

def verdicts_csv():
    out = io.StringIO(); w = csv.writer(out, lineterminator="\n"); w.writerow(["id", "better"])
    for q in STATE["questions"]: w.writerow([q["id"], q["better"]])
    return out.getvalue()

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body, default=str)).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", ctype + "; charset=utf-8"); self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/summary": return self._send(200, STATE["S"])
        if path == "/api/questions": return self._send(200, STATE["questions"])
        if path == "/api/verdicts.csv": return self._send(200, verdicts_csv(), "text/csv")
        f = os.path.join(ROOT, "web", "index.html" if path == "/" else path.lstrip("/"))
        if os.path.commonpath([os.path.abspath(f), os.path.join(ROOT, "web")]) == os.path.join(ROOT, "web") and os.path.isfile(f):
            return self._send(200, open(f, "rb").read(), mimetypes.guess_type(f)[0] or "text/plain")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8", "replace")
        try:
            with LOCK:
                if self.path == "/api/check":
                    d = json.loads(raw); return self._send(200, check_answer(d.get("question", ""), d["answer"]))
                if self.path == "/api/evaluate":
                    build_state(load_text(raw), STATE["kb_path"], STATE["cfg"]); return self._send(200, STATE["S"])
            self._send(404, {"error": "not found"})
        except Exception as e:   # bad CSV, missing columns, bad JSON -> readable message for the UI
            self._send(400, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *a): pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000); ap.add_argument("--data", default=os.path.join(ROOT, "data", "questions.csv"))
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    STATE["kb_path"] = os.path.join(ROOT, "data", "policy_kb.json"); STATE["cfg"] = json.load(open(os.path.join(ROOT, "config.json")))
    build_state(load(a.data), STATE["kb_path"], STATE["cfg"])
    url = f"http://127.0.0.1:{a.port}"
    print(f"Prompt check running at {url}  (Ctrl+C to stop)")
    if not a.no_browser: threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()

if __name__ == "__main__":
    main()
