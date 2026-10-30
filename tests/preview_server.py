"""本地预览服务：不装进 AstrBot 也能把两个视图跑起来看效果。

用法：
    python tests/preview_server.py --port 8765 \
        --state /path/state.json --covers /path/covers \
        --journal /path/entries.jsonl

然后浏览器打开 http://127.0.0.1:8765/watch/index.html
（脚本会把一个假的 window.AstrBotPluginView 注入到页面里，接口直接读本地文件。）
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.store import PanelData  # noqa: E402

BRIDGE_STUB = """
<script>
window.AstrBotPluginView = {
  ready: async () => ({ locale: 'zh-CN' }),
  getContext: () => ({ locale: 'zh-CN' }),
  getLocale: () => 'zh-CN',
  async apiGet(endpoint, params) {
    const q = new URLSearchParams(params || {});
    const r = await fetch('/__api/' + endpoint + (q.toString() ? '?' + q.toString() : ''));
    if (!r.ok) throw new Error(await r.text());
    return await r.json();
  },
  async apiPost(endpoint, body) {
    const r = await fetch('/__api/' + endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
    if (!r.ok) throw new Error(await r.text());
    return await r.json();
  },
};
</script>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--state", default="")
    ap.add_argument("--covers", default="")
    ap.add_argument("--journal", default="")
    args = ap.parse_args()

    conf = {
        "bili_state_file": args.state,
        "cover_dir": args.covers,
        "journal_file": args.journal,
        "page_size": 24,
    }
    data = PanelData(conf, "astrbot_plugin_dafeiyu_panel")

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            path = urllib.parse.unquote(u.path)
            q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
            if path.startswith("/__api/"):
                name = path[len("/__api/"):]
                if name == "items":
                    payload = data.page(
                        filter_=q.get("filter", "all"),
                        q=q.get("q", ""),
                        page=int(q.get("page", 1)),
                        size=int(q.get("size", 24)),
                    )
                    payload["allow_edit"] = True
                    payload["status"] = data.status()
                    return self._json(payload)
                if name == "cover":
                    return self._json({"bvid": q.get("bvid"), "data": data.cover_b64(q.get("bvid", ""))})
                if name == "journal":
                    entries = data.journal(limit=int(q.get("limit", 300)), q=q.get("q", ""))
                    days = {}
                    for e in entries:
                        days[e["day"]] = days.get(e["day"], 0) + 1
                    return self._json(
                        {
                            "total": len(entries),
                            "days": [{"day": d, "n": n} for d, n in sorted(days.items(), reverse=True)],
                            "entries": entries,
                            "status": data.status(),
                        }
                    )
                if name == "status":
                    return self._json({"summary": data.summary(), "sources": data.status()})
                return self._json({"message": "not found"}, 404)

            rel = path.lstrip("/") or "她看过什么/index.html"
            f = ROOT / "views" / rel
            if f.is_file():
                html = f.read_text(encoding="utf-8")
                html = html.replace("<script type=\"module\">", BRIDGE_STUB + "<script type=\"module\">", 1)
                return self._send(200, html.encode(), "text/html; charset=utf-8")
            return self._send(404, b"not found", "text/plain; charset=utf-8")

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            if self.path.startswith("/__api/rate"):
                return self._json(data.rate(body.get("bvid", ""), int(body.get("stars") or 0), str(body.get("note") or ""), body.get("fav")))
            return self._json({"message": "not found"}, 404)

    srv = ThreadingHTTPServer(("127.0.0.1", args.port), H)
    print(f"preview: http://127.0.0.1:{args.port}/%E5%A5%B9%E7%9C%8B%E8%BF%87%E4%BB%80%E4%B9%88/index.html")
    srv.serve_forever()


if __name__ == "__main__":
    main()
