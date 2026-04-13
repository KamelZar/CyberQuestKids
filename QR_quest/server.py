#!/usr/bin/env python3
"""
CyberQuest — Serveur local Flask
Usage :
    pip install flask
    sudo python3 server.py          # port 80 (nécessite sudo)
    python3 server.py               # port 8080 (sans sudo)

Le serveur écoute sur 0.0.0.0 pour être accessible depuis le réseau local.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, Response, request, redirect

# ── Config ────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
HTML_DIR    = BASE_DIR / "html"
EVENTS_FILE = BASE_DIR / "events.json"

PORT = 80 if os.geteuid() == 0 else 8080   # 80 si root, 8080 sinon

# ── App ───────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(HTML_DIR))
app.config['JSON_SORT_KEYS'] = False

# ── Helpers ───────────────────────────────────────────────────────────
def load_events():
    if EVENTS_FILE.exists():
        try:
            return json.loads(EVENTS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []

def append_event(event):
    events = load_events()
    events.append(event)
    EVENTS_FILE.write_text(
        json.dumps(events, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

# 1×1 pixel GIF transparent (tracking pixel)
GIF_1x1 = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
    b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00'
    b'\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
)

# ── Routes de tracking ────────────────────────────────────────────────
@app.route('/cyberquest/<team_id>/<exo>/<status>')
def track(team_id, exo, status):
    """
    Appelé par _track.js via Image().src
    Exemples :
        /cyberquest/4271/mirror/gotcha
        /cyberquest/4271/phishing/gotcha
        /cyberquest/4271/lockpicking/view
        /cyberquest/4271/init/start
    """
    event = {
        'id':        team_id,
        'exo':       exo,
        'status':    status,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'ip':        request.remote_addr,
        'ua':        request.headers.get('User-Agent', '')[:120],
    }
    append_event(event)
    print(f"[TRACK] {team_id:>8} | {exo:<16} | {status}")

    resp = Response(GIF_1x1, mimetype='image/gif')
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'no-store'
    return resp

# ── API dashboard ─────────────────────────────────────────────────────
@app.route('/dashboard/data')
def dashboard_data():
    """Retourne tous les événements en JSON (polling toutes les 5 s)."""
    events = load_events()
    resp = jsonify(events)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'no-store'
    return resp

@app.route('/dashboard/reset', methods=['POST'])
def dashboard_reset():
    """Efface tous les événements (bouton reset animateur)."""
    EVENTS_FILE.write_text('[]', encoding='utf-8')
    return jsonify({'ok': True})

# ── Pages HTML ────────────────────────────────────────────────────────
@app.route('/')
def root():
    return redirect('/init')

@app.route('/init')
def init_page():
    return send_from_directory(str(HTML_DIR), 'init.html')

@app.route('/dashboard')
def dashboard_page():
    return send_from_directory(str(HTML_DIR), 'dashboard.html')

@app.route('/<path:filename>')
def static_files(filename):
    """Sert tous les fichiers du dossier html/."""
    return send_from_directory(str(HTML_DIR), filename)

# ── Démarrage ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not EVENTS_FILE.exists():
        EVENTS_FILE.write_text('[]', encoding='utf-8')

    print(f"""
╔══════════════════════════════════════════════╗
║         CyberQuest — Serveur local           ║
╠══════════════════════════════════════════════╣
║  Accessible sur le réseau :                  ║
║    http://192.168.0.45:{PORT:<5}             ║
║                                              ║
║  Init participants :  /init                  ║
║  Dashboard animateur: /dashboard             ║
║  Données brutes :     /dashboard/data        ║
╚══════════════════════════════════════════════╝
""")

    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=(len(sys.argv) > 1 and sys.argv[1] == '--debug'),
        use_reloader=False,
    )
