import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import datetime
DB_PATH = 'backend/health.db'
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        for ddl in (
            'CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT, age INTEGER, height_cm REAL, weight_kg REAL, updated_at TEXT)',
            'CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, steps INTEGER, water_ml INTEGER, sleep_hours REAL, notes TEXT, created_at TEXT)',
            'CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY CHECK (id = 1), steps_goal INTEGER, water_goal INTEGER, sleep_goal REAL, updated_at TEXT)',
            'CREATE TABLE IF NOT EXISTS weights (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, weight_kg REAL, created_at TEXT)',
            'CREATE TABLE IF NOT EXISTS moods (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, mood INTEGER, stress INTEGER, energy INTEGER, notes TEXT, created_at TEXT)'
        ):
            cur.execute(ddl)
class HealthTrackerHandler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, code, obj):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _payload(self):
        n = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(n) if n > 0 else b''
        try:
            return json.loads(raw.decode('utf-8') or '{}')
        except Exception:
            return None

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)
        if p.path == '/api/health':
            return self._json(200, {'ok': True, 'time': datetime.utcnow().isoformat()})
        if p.path == '/api/profile':
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute('SELECT * FROM profile WHERE id=1').fetchone()
                return self._json(200, dict(row) if row else {})
        if p.path == '/api/entries':
            qs = parse_qs(p.query); d = (qs.get('date') or [None])[0]; f = (qs.get('from') or [None])[0]; t = (qs.get('to') or [None])[0]
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('SELECT * FROM entries WHERE date=? ORDER BY date DESC, id DESC' if d else ('SELECT * FROM entries WHERE date BETWEEN ? AND ? ORDER BY date DESC, id DESC' if f and t else 'SELECT * FROM entries ORDER BY date DESC, id DESC LIMIT 200'), (d,) if d else ((f, t) if f and t else ()))
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if p.path == '/api/goals':
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute('SELECT * FROM goals WHERE id=1').fetchone()
                return self._json(200, dict(row) if row else {})
        if p.path == '/api/weights':
            qs = parse_qs(p.query); f = (qs.get('from') or [None])[0]; t = (qs.get('to') or [None])[0]
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('SELECT * FROM weights WHERE date BETWEEN ? AND ? ORDER BY date DESC, id DESC' if f and t else 'SELECT * FROM weights ORDER BY date DESC, id DESC LIMIT 200', (f, t) if f and t else ())
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if p.path == '/api/moods':
            qs = parse_qs(p.query); f = (qs.get('from') or [None])[0]; t = (qs.get('to') or [None])[0]
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('SELECT * FROM moods WHERE date BETWEEN ? AND ? ORDER BY date DESC, id DESC' if f and t else 'SELECT * FROM moods ORDER BY date DESC, id DESC LIMIT 200', (f, t) if f and t else ())
                return self._json(200, [dict(r) for r in cur.fetchall()])
        if p.path == '/api/summary':
            return self._summary()
        if p.path == '/api/export':
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute('SELECT * FROM entries ORDER BY date DESC, id DESC').fetchall()
                return self._json(200, {'entries': [dict(r) for r in rows]})
        return self._json(404, {'error': 'Not found'})

    def do_POST(self):
        p = urlparse(self.path); data = self._payload()
        if data is None: return self._json(400, {'error': 'Invalid JSON'})
        if p.path == '/api/profile':
            ts = datetime.utcnow().isoformat()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('INSERT INTO profile (id, name, age, height_cm, weight_kg, updated_at) VALUES (1, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, age=excluded.age, height_cm=excluded.height_cm, weight_kg=excluded.weight_kg, updated_at=excluded.updated_at', (data.get('name'), data.get('age'), data.get('height_cm'), data.get('weight_kg'), ts))
            return self._json(200, {'ok': True})
        if p.path == '/api/today':
            ts = datetime.utcnow().isoformat(); d = data.get('date') or datetime.utcnow().date().isoformat()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('INSERT INTO entries (date, steps, water_ml, sleep_hours, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)', (d, data.get('steps'), data.get('water_ml'), data.get('sleep_hours'), data.get('notes'), ts))
            return self._json(201, {'ok': True})
        if p.path == '/api/goals':
            ts = datetime.utcnow().isoformat()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('INSERT INTO goals (id, steps_goal, water_goal, sleep_goal, updated_at) VALUES (1, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET steps_goal=excluded.steps_goal, water_goal=excluded.water_goal, sleep_goal=excluded.sleep_goal, updated_at=excluded.updated_at', (data.get('steps_goal'), data.get('water_goal'), data.get('sleep_goal'), ts))
            return self._json(200, {'ok': True})
        if p.path == '/api/weights':
            ts = datetime.utcnow().isoformat(); d = data.get('date') or datetime.utcnow().date().isoformat()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('INSERT INTO weights (date, weight_kg, created_at) VALUES (?, ?, ?)', (d, data.get('weight_kg'), ts))
            return self._json(201, {'ok': True})
        if p.path == '/api/moods':
            ts = datetime.utcnow().isoformat(); d = data.get('date') or datetime.utcnow().date().isoformat()
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('INSERT INTO moods (date, mood, stress, energy, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)', (d, data.get('mood'), data.get('stress'), data.get('energy'), data.get('notes'), ts))
            return self._json(201, {'ok': True})
        return self._json(404, {'error': 'Not found'})

    def do_PUT(self):
        p = urlparse(self.path); data = self._payload()
        if data is None: return self._json(400, {'error': 'Invalid JSON'})
        if p.path == '/api/entries':
            eid = data.get('id');
            if not eid: return self._json(400, {'error': 'Missing id'})
            fields = ['date','steps','water_ml','sleep_hours','notes']
            ups = [f"{f}=?" for f in fields if f in data]
            if not ups: return self._json(400, {'error': 'No fields to update'})
            vals = [data.get(f) for f in fields if f in data] + [eid]
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(f"UPDATE entries SET {', '.join(ups)} WHERE id=?", tuple(vals))
            return self._json(200, {'ok': True})
        if p.path == '/api/weights':
            wid = data.get('id');
            if not wid: return self._json(400, {'error': 'Missing id'})
            fields = ['date','weight_kg']
            ups = [f"{f}=?" for f in fields if f in data]
            if not ups: return self._json(400, {'error': 'No fields to update'})
            vals = [data.get(f) for f in fields if f in data] + [wid]
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(f"UPDATE weights SET {', '.join(ups)} WHERE id=?", tuple(vals))
            return self._json(200, {'ok': True})
        if p.path == '/api/moods':
            mid = data.get('id');
            if not mid: return self._json(400, {'error': 'Missing id'})
            fields = ['date','mood','stress','energy','notes']
            ups = [f"{f}=?" for f in fields if f in data]
            if not ups: return self._json(400, {'error': 'No fields to update'})
            vals = [data.get(f) for f in fields if f in data] + [mid]
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(f"UPDATE moods SET {', '.join(ups)} WHERE id=?", tuple(vals))
            return self._json(200, {'ok': True})
        return self._json(404, {'error': 'Not found'})

    def do_DELETE(self):
        p = urlparse(self.path)
        if p.path in ('/api/entries','/api/weights','/api/moods'):
            qs = parse_qs(p.query); i = (qs.get('id') or [None])[0]
            if not i: return self._json(400, {'error': 'Missing id'})
            table = 'entries' if p.path.endswith('entries') else ('weights' if p.path.endswith('weights') else 'moods')
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(f'DELETE FROM {table} WHERE id=?', (i,))
            return self._json(200, {'ok': True})
        return self._json(404, {'error': 'Not found'})

    def _summary(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            goals_row = cur.execute('SELECT * FROM goals WHERE id=1').fetchone()
            goals = dict(goals_row) if goals_row else {}
            profile_row = cur.execute('SELECT * FROM profile WHERE id=1').fetchone()
            profile = dict(profile_row) if profile_row else {}
            entries = [dict(r) for r in cur.execute('SELECT * FROM entries ORDER BY date DESC LIMIT 30').fetchall()]
            weights = [dict(r) for r in cur.execute('SELECT * FROM weights ORDER BY date DESC LIMIT 30').fetchall()]
            moods = [dict(r) for r in cur.execute('SELECT * FROM moods ORDER BY date DESC LIMIT 30').fetchall()]
        def avg(lst, key):
            vals = [float(x.get(key) or 0) for x in lst if x.get(key) is not None]
            return round(sum(vals)/len(vals), 2) if vals else 0
        sg, wg, slg = goals.get('steps_goal') or 0, goals.get('water_goal') or 0, goals.get('sleep_goal') or 0
        streak = 0
        for e in sorted(entries, key=lambda x: x['date'], reverse=True):
            ok = True
            if sg: ok = ok and (int(e.get('steps') or 0) >= sg)
            if wg: ok = ok and (int(e.get('water_ml') or 0) >= wg)
            if slg: ok = ok and (float(e.get('sleep_hours') or 0) >= slg)
            if ok: streak += 1
            else: break
        bmi = None
        if profile.get('height_cm') and (profile.get('weight_kg') or (weights and weights[0].get('weight_kg'))):
            h_m = float(profile['height_cm'])/100.0
            w = float(profile.get('weight_kg') or weights[0].get('weight_kg'))
            bmi = round(w/(h_m*h_m), 2)
        return self._json(200, {
            'goals': goals,
            'profile': profile,
            'averages': {'steps': avg(entries,'steps'), 'water_ml': avg(entries,'water_ml'), 'sleep_hours': avg(entries,'sleep_hours')},
            'streak': streak,
            'weights': weights,
            'moods': moods,
            'bmi': bmi
        })

def run_server():
    init_db()
    httpd = HTTPServer(('127.0.0.1', 5000), HealthTrackerHandler)
    print('Backend running on http://127.0.0.1:5000')
    httpd.serve_forever()
if __name__ == '__main__':
    run_server()
