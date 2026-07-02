#!/usr/bin/env python3
"""Another Beautiful Roof — lead capture server (a whosystems build).

Zero-dependency: Python stdlib only. Serves the static site, captures leads
into SQLite, and exposes an admin dashboard to work them.

Run:   python3 server/app.py
Visit: http://localhost:8000/          (public site)
       http://localhost:8000/admin     (dashboard — user: admin)

Admin password comes from env ABR_ADMIN_PW (default "roof"). Set a real one
before this ever faces the internet, and put it behind HTTPS.
"""
import os, json, sqlite3, base64, html, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.join(ROOT, "site")
DB   = os.path.join(HERE, "abr.db")
PORT = int(os.environ.get("PORT", "8000"))
ADMIN_USER = "admin"
ADMIN_PW = os.environ.get("ABR_ADMIN_PW", "roof")
STATUSES = ["new", "contacted", "quoted", "won", "lost"]
FIELDS = ["name", "phone", "email", "address", "roof_type", "message", "source"]

MIME = {".html":"text/html;charset=utf-8", ".css":"text/css", ".js":"text/javascript",
        ".svg":"image/svg+xml", ".png":"image/png", ".jpg":"image/jpeg", ".ico":"image/x-icon",
        ".xml":"application/xml", ".txt":"text/plain", ".webmanifest":"application/manifest+json"}


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS leads(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            name TEXT, phone TEXT, email TEXT, address TEXT,
            roof_type TEXT, message TEXT, source TEXT,
            status TEXT NOT NULL DEFAULT 'new')""")


class H(BaseHTTPRequestHandler):
    server_version = "ABR/1.0"

    def _send(self, code, body=b"", ctype="text/plain;charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json")

    # ---- auth ----
    def _authed(self):
        h = self.headers.get("Authorization", "")
        if h.startswith("Basic "):
            try:
                u, p = base64.b64decode(h[6:]).decode().split(":", 1)
                return u == ADMIN_USER and p == ADMIN_PW
            except Exception:
                return False
        return False

    def _auth_challenge(self):
        self._send(401, "Authentication required", extra={"WWW-Authenticate": 'Basic realm="ABR Admin"'})

    # ---- routing ----
    def do_GET(self):
        u = urlparse(self.path)
        path, qs = u.path, parse_qs(u.query)
        if path == "/admin":
            return self._admin()
        if path == "/admin/update":
            return self._admin_update(qs)
        if path == "/api/leads.json":
            if not self._authed():
                return self._auth_challenge()
            with db() as c:
                rows = [dict(r) for r in c.execute("SELECT * FROM leads ORDER BY id DESC")]
            return self._json(200, {"count": len(rows), "leads": rows})
        return self._static(path)

    def do_HEAD(self):
        self._static(urlparse(self.path).path)

    def do_POST(self):
        if urlparse(self.path).path == "/api/leads":
            return self._create_lead()
        self._send(404, "Not found")

    # ---- lead intake ----
    def _create_lead(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0 or n > 20000:
                return self._json(400, {"ok": False, "error": "bad size"})
            data = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return self._json(400, {"ok": False, "error": "bad json"})
        if data.get("company"):  # honeypot
            return self._json(200, {"ok": True})
        name = (data.get("name") or "").strip()
        phone = (data.get("phone") or "").strip()
        if not name or not phone:
            return self._json(422, {"ok": False, "error": "name and phone required"})
        vals = {k: (str(data.get(k, "") or "").strip()[:2000]) for k in FIELDS}
        vals["source"] = vals["source"] or "website"
        with db() as c:
            cur = c.execute(
                "INSERT INTO leads(created_at,name,phone,email,address,roof_type,message,source,status)"
                " VALUES(?,?,?,?,?,?,?,?, 'new')",
                (datetime.datetime.now().isoformat(timespec="seconds"),
                 vals["name"], vals["phone"], vals["email"], vals["address"],
                 vals["roof_type"], vals["message"], vals["source"]))
            lead_id = cur.lastrowid
        print(f"[lead] #{lead_id} {vals['name']} · {vals['phone']} · {vals['roof_type']}")
        return self._json(201, {"ok": True, "id": lead_id})

    # ---- admin dashboard ----
    def _admin_update(self, qs):
        if not self._authed():
            return self._auth_challenge()
        try:
            lid = int(qs.get("id", ["0"])[0]); st = qs.get("status", [""])[0]
        except Exception:
            return self._send(400, "bad request")
        if st in STATUSES:
            with db() as c:
                c.execute("UPDATE leads SET status=? WHERE id=?", (st, lid))
        self._send(303, "", extra={"Location": "/admin"})

    def _admin(self):
        if not self._authed():
            return self._auth_challenge()
        with db() as c:
            rows = [dict(r) for r in c.execute("SELECT * FROM leads ORDER BY id DESC")]
            counts = {s: c.execute("SELECT COUNT(*) FROM leads WHERE status=?", (s,)).fetchone()[0] for s in STATUSES}
        total = len(rows)
        badge = {"new":"#C8102E","contacted":"#d6a01e","quoted":"#2f7fe0","won":"#37c98a","lost":"#8B93A1"}
        cards = "".join(
            f'<div class="mc"><div class="mn">{counts[s]}</div><div class="ml">{s}</div></div>' for s in STATUSES)
        trs = []
        for r in rows:
            opts = "".join(
                f'<a class="st {"on" if r["status"]==s else ""}" style="--c:{badge[s]}"'
                f' href="/admin/update?id={r["id"]}&status={s}">{s}</a>' for s in STATUSES)
            msg = html.escape(r["message"] or "")
            trs.append(
                f'<tr><td class="mono">#{r["id"]}</td>'
                f'<td>{html.escape(r["created_at"])}</td>'
                f'<td><b>{html.escape(r["name"] or "")}</b>'
                f'{("<div class=sub>"+msg+"</div>") if msg else ""}</td>'
                f'<td><a href="tel:{html.escape(r["phone"] or "")}">{html.escape(r["phone"] or "")}</a>'
                f'<div class=sub>{html.escape(r["email"] or "")}</div></td>'
                f'<td>{html.escape(r["roof_type"] or "")}<div class=sub>{html.escape(r["address"] or "")}</div></td>'
                f'<td class="stcell">{opts}</td></tr>')
        empty = '<tr><td colspan="6" style="text-align:center;color:#8B93A1;padding:40px">No leads yet.</td></tr>'
        page = f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Leads · Another Beautiful Roof</title>
<style>
:root{{--ink:#0B0E14;--panel:#12161F;--line:rgba(139,147,161,.16);--steel:#8B93A1;--paper:#F4F5F7;--red:#C8102E}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--ink);color:var(--paper);font-family:'Archivo',system-ui,Arial,sans-serif;padding:28px}}
.head{{display:flex;align-items:center;gap:14px;margin-bottom:22px}}
.head svg{{width:34px;height:34px}}
.head h1{{font-size:18px;letter-spacing:.14em;font-weight:800}}
.head .t{{margin-left:auto;color:var(--steel);font-size:13px;font-family:monospace}}
.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:22px}}
.mc{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}}
.mn{{font-size:28px;font-weight:800}} .ml{{color:var(--steel);font-size:12px;text-transform:uppercase;letter-spacing:.1em;margin-top:4px}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
th{{text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--steel);padding:14px;border-bottom:1px solid var(--line);font-weight:600}}
td{{padding:14px;border-bottom:1px solid var(--line);font-size:14px;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
a{{color:var(--paper);text-decoration:none}}
.sub{{color:var(--steel);font-size:12px;margin-top:3px}}
.mono{{font-family:monospace;color:var(--steel)}}
.stcell{{white-space:nowrap}}
.st{{display:inline-block;font-size:11px;padding:4px 9px;border-radius:6px;margin:2px;border:1px solid var(--line);color:var(--steel);text-transform:uppercase;letter-spacing:.04em}}
.st.on{{background:var(--c);border-color:var(--c);color:#0B0E14;font-weight:600}}
</style></head><body>
<div class="head">
<svg viewBox="0 0 100 100"><path d="M8 92 L41 14 L27 60 L33 63 L48 16 L57 5 L92 92 L69 92 L51 48 L33 92 Z" fill="#F4F5F7"/></svg>
<h1>ANOTHER BEAUTIFUL ROOF — LEADS</h1><div class="t">{total} total · live</div></div>
<div class="cards">{cards}</div>
<table><thead><tr><th>ID</th><th>Received</th><th>Customer</th><th>Contact</th><th>Job / Location</th><th>Status</th></tr></thead>
<tbody>{''.join(trs) if trs else empty}</tbody></table>
</body></html>"""
        self._send(200, page, "text/html;charset=utf-8")

    # ---- static files ----
    def _static(self, path):
        if path == "/":
            path = "/index.html"
        rel = os.path.normpath(path).lstrip("/\\")
        full = os.path.join(SITE, rel)
        if not full.startswith(SITE) or not os.path.isfile(full):
            return self._send(404, "Not found")
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as f:
            self._send(200, f.read(), MIME.get(ext, "application/octet-stream"))

    def log_message(self, *a):
        pass  # quiet; lead inserts print their own line


if __name__ == "__main__":
    init_db()
    print(f"Another Beautiful Roof — serving site + lead DB on http://localhost:{PORT}")
    print(f"  site:  http://localhost:{PORT}/")
    print(f"  admin: http://localhost:{PORT}/admin  (user: {ADMIN_USER} / pw: {ADMIN_PW})")
    print(f"  db:    {DB}")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
