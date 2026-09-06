import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, request, Response
from flask import render_template_string

app = Flask(__name__)

DB_PATH = os.getenv("ANALYTICS_DB", "analytics.db")
DASHBOARD_USER = os.getenv("ANALYTICS_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("ANALYTICS_PASSWORD", "change-me-now")
HASH_SECRET = os.getenv("ANALYTICS_HASH_SECRET", secrets.token_hex(32))

# Optional allow-list. Empty means any project slug is accepted.
PROJECTS = {
    p.strip() for p in os.getenv("ANALYTICS_PROJECTS", "").split(",") if p.strip()
}

DASHBOARD_HTML = r'''
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Analytics</title>
<style>
:root{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#111827;background:#f4f6f8}
*{box-sizing:border-box} body{margin:0}.wrap{max-width:1150px;margin:auto;padding:28px 18px 50px}
h1{margin:0 0 6px}.muted{color:#6b7280}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.value{font-size:30px;font-weight:800;margin-top:7px}.label{font-size:13px;color:#6b7280;text-transform:uppercase;letter-spacing:.04em}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden}th,td{padding:14px;border-bottom:1px solid #eee;text-align:left}th{font-size:12px;color:#6b7280;text-transform:uppercase}tr:last-child td{border-bottom:0}
.controls{display:flex;gap:10px;align-items:center;margin:22px 0;flex-wrap:wrap}select,button{padding:9px 12px;border:1px solid #d1d5db;border-radius:9px;background:#fff}button{cursor:pointer}.chart{display:grid;grid-template-columns:repeat(30,1fr);gap:5px;align-items:end;height:230px;padding:16px 12px 8px;background:#fff;border:1px solid #e5e7eb;border-radius:14px}.bar{position:relative;min-width:0}.bar i{display:block;height:var(--h);background:#111827;border-radius:4px 4px 0 0}.bar span{display:block;font-size:9px;color:#6b7280;text-align:center;margin-top:5px;white-space:nowrap;overflow:hidden}.empty{padding:35px;text-align:center;color:#6b7280}
@media(max-width:800px){.grid{grid-template-columns:repeat(2,1fr)}.chart{grid-template-columns:repeat(15,1fr);height:210px}}@media(max-width:520px){.grid{grid-template-columns:1fr}.chart{grid-template-columns:repeat(10,1fr)}}
</style>
</head>
<body>
<div class="wrap">
  <h1>Project Analytics</h1>
  <div class="muted">Your websites in one dashboard</div>
  <div class="controls"><label>Project <select id="project"><option value="">All projects</option></select></label><label>Days <select id="days"><option>7</option><option selected>30</option><option>90</option></select></label><button onclick="load()">Refresh</button></div>
  <div class="grid">
    <div class="card"><div class="label">Page views</div><div class="value" id="views">—</div></div>
    <div class="card"><div class="label">Unique visitors</div><div class="value" id="visitors">—</div></div>
    <div class="card"><div class="label">Today</div><div class="value" id="today">—</div></div>
    <div class="card"><div class="label">Projects</div><div class="value" id="projects">—</div></div>
  </div>
  <div class="card" style="margin-bottom:22px"><div style="font-weight:700;margin-bottom:12px">Views by day</div><div class="chart" id="chart"></div></div>
  <table><thead><tr><th>Project</th><th>Views</th><th>Unique visitors</th><th>Last visit</th></tr></thead><tbody id="table"></tbody></table>
</div>
<script>
async function get(url){const r=await fetch(url);if(!r.ok)throw new Error('Request failed');return r.json()}
function fmt(n){return Number(n||0).toLocaleString()}
async function load(){
  try{
    const project=document.getElementById('project').value; const days=document.getElementById('days').value;
    const q=project?`?project=${encodeURIComponent(project)}&days=${days}`:`?days=${days}`;
    const data=await get('/api/stats'+q);
    document.getElementById('views').textContent=fmt(data.summary.views);
    document.getElementById('visitors').textContent=fmt(data.summary.unique_visitors);
    document.getElementById('today').textContent=fmt(data.summary.today);
    document.getElementById('projects').textContent=fmt(data.summary.projects);
    document.getElementById('table').innerHTML=data.projects.length?data.projects.map(x=>`<tr><td><b>${esc(x.project)}</b></td><td>${fmt(x.views)}</td><td>${fmt(x.unique_visitors)}</td><td>${esc(x.last_visit||'—')}</td></tr>`).join(''):`<tr><td colspan="4" class="empty">No data yet</td></tr>`;
    const values=data.daily.map(x=>x.views); const max=Math.max(1,...values);
    document.getElementById('chart').innerHTML=data.daily.map(x=>`<div class="bar" title="${x.date}: ${x.views}"><i style="--h:${Math.max(3,Math.round((x.views/max)*175))}px"></i><span>${x.date.slice(5)}</span></div>`).join('');
  }catch(e){alert(e.message)}
}
function esc(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
async function init(){const d=await get('/api/projects'); const s=document.getElementById('project'); d.projects.forEach(p=>{const o=document.createElement('option');o.value=p;o.textContent=p;s.appendChild(o)});s.addEventListener('change',load);load()}
init();
</script>
</body>
</html>
'''


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project TEXT NOT NULL,
            client_id TEXT NOT NULL,
            path TEXT,
            referrer TEXT,
            user_agent TEXT,
            ip_hash TEXT,
            country TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_project ON visits(project)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_created ON visits(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_client ON visits(project, client_id)")
    conn.commit()
    conn.close()


def hash_ip(ip: str) -> str:
    return hashlib.sha256(f"{HASH_SECRET}:{ip}".encode()).hexdigest()


def valid_project(project: str) -> bool:
    return bool(project) and len(project) <= 80 and all(c.isalnum() or c in "-_" for c in project) and (not PROJECTS or project in PROJECTS)


def cors_response(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.after_request
def after_request(response):
    return cors_response(response)


@app.route("/health")
def health():
    return jsonify(ok=True)


@app.route("/log", methods=["POST", "GET", "OPTIONS"])
def log_visit():
    if request.method == "OPTIONS":
        return ("", 204)

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
    else:
        data = request.args

    project = (data.get("project") or "").strip()
    client_id = (data.get("client_id") or "").strip()
    path = (data.get("path") or "")[:500]
    referrer = (data.get("referrer") or "")[:500]

    if not valid_project(project):
        return jsonify(error="Invalid project"), 400
    if not client_id or len(client_id) > 120:
        return jsonify(error="Invalid client_id"), 400

    now = datetime.now(timezone.utc).isoformat()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    ip_hash = hash_ip(ip) if ip else None
    ua = request.headers.get("User-Agent", "")[:500]
    country = request.headers.get("CF-IPCountry", "")[:10]

    conn = db()
    conn.execute("""
        INSERT INTO visits(project, client_id, path, referrer, user_agent, ip_hash, country, created_at)
        VALUES(?,?,?,?,?,?,?,?)
    """, (project, client_id, path, referrer, ua, ip_hash, country, now))
    conn.commit()
    conn.close()

    return jsonify(ok=True)


def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not secrets.compare_digest(auth.username or "", DASHBOARD_USER) or not secrets.compare_digest(auth.password or "", DASHBOARD_PASSWORD):
            return Response("Authentication required", 401, {"WWW-Authenticate": 'Basic realm="Analytics"'})
        return fn(*args, **kwargs)
    return wrapper


@app.route("/dashboard")
@auth_required
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/projects")
@auth_required
def projects():
    conn = db()
    rows = conn.execute("SELECT DISTINCT project FROM visits ORDER BY project").fetchall()
    conn.close()
    return jsonify(projects=[r["project"] for r in rows])


@app.route("/api/stats")
@auth_required
def stats():
    project = (request.args.get("project") or "").strip()
    try:
        days = max(1, min(365, int(request.args.get("days", "30"))))
    except ValueError:
        days = 30

    conn = db()
    where = "WHERE created_at >= datetime('now', ?)"
    params = [f"-{days} days"]
    if project:
        where += " AND project = ?"
        params.append(project)

    row = conn.execute(f"SELECT COUNT(*) views, COUNT(DISTINCT project || ':' || client_id) unique_visitors FROM visits {where}", params).fetchone()
    today_params = []
    today_where = "WHERE date(created_at) = date('now')"
    if project:
        today_where += " AND project = ?"
        today_params.append(project)
    today = conn.execute(f"SELECT COUNT(*) c FROM visits {today_where}", today_params).fetchone()["c"]
    project_count = conn.execute("SELECT COUNT(DISTINCT project) c FROM visits").fetchone()["c"]

    rows = conn.execute(f"""
        SELECT project, COUNT(*) views, COUNT(DISTINCT client_id) unique_visitors, MAX(created_at) last_visit
        FROM visits {where}
        GROUP BY project ORDER BY views DESC
    """, params).fetchall()

    daily_rows = conn.execute(f"""
        SELECT date(created_at) date, COUNT(*) views
        FROM visits {where}
        GROUP BY date(created_at) ORDER BY date(created_at)
    """, params).fetchall()
    conn.close()

    return jsonify(
        summary={
            "views": row["views"],
            "unique_visitors": row["unique_visitors"],
            "today": today,
            "projects": project_count,
        },
        projects=[dict(r) for r in rows],
        daily=[dict(r) for r in daily_rows],
    )


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
