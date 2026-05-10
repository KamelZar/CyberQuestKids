#!/usr/bin/env python3
"""
CyberQuest — Serveur local Flask
Usage :
    pip install flask
    sudo python3 server.py          # port 80 (nécessite sudo)
    python3 server.py               # port 8080 (sans sudo)

Le serveur écoute sur 0.0.0.0 pour être accessible depuis le réseau local.
"""

import base64
import json
import os
import re
import socket
import sys
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, Response, request, redirect

# ── Config ────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
HTML_DIR    = BASE_DIR / "html"
EVENTS_FILE = BASE_DIR / "events.json"
TEAMS_FILE  = BASE_DIR / "teams.json"      # équipes enregistrées pour la session
PHOTOS_DIR  = BASE_DIR / "photos"          # photos "Vous" uploadées

PORT = 80 if os.geteuid() == 0 else 8080   # 80 si root, 8080 sinon

# ── App ───────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(HTML_DIR))
app.config['JSON_SORT_KEYS'] = False

# ── Helpers — events ──────────────────────────────────────────────────
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

# ── Helpers — teams ───────────────────────────────────────────────────
def load_teams():
    """Retourne le dict { team_id: { uuid, team_num, lang, registered_at } }"""
    if TEAMS_FILE.exists():
        try:
            return json.loads(TEAMS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}

def save_teams(teams):
    TEAMS_FILE.write_text(
        json.dumps(teams, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

# ── Avatar map ───────────────────────────────────────────────────────
AVATARS_DIR = BASE_DIR / "images" / "Avatar"

# Mapping id métier → nom de fichier réel (source de vérité unique)
AVATAR_MAP = {
    'james':       'James_manga.png',
    'moussouris':  'Kate_moussouris_manga.png',
    'mckinnon':    'McKinnon_manga.png',
    'berners-lee': 'TimBerners-Lee_manga.png',
    'torvalds':    'Linus_manga.png',
    'snowden':     'snowden_manga.png',
    'hopper':      'Hopper_manga.png',
    'murati':      'Murati_manga.png',
    'anonymous':   'Anonymous_manga.png',
    'wannacry':    'WannaCry_manga.png',
}

# ── Helpers — IP locale ───────────────────────────────────────────────
def get_local_ip():
    """Détecte l'IP locale de la machine sur le réseau."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

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

# ── API teams ─────────────────────────────────────────────────────────
@app.route('/teams/available')
def teams_available():
    """
    Retourne la liste des team_id déjà pris.
    Appelé par team-select.html toutes les secondes (polling).
    Réponse : { "taken": ["snowden", "anonymous", ...] }
    """
    teams = load_teams()
    resp = jsonify({'taken': list(teams.keys())})
    resp.headers['Cache-Control'] = 'no-store'
    return resp

@app.route('/teams/register', methods=['POST'])
def teams_register():
    """
    Enregistre le choix d'équipe d'un participant.
    Corps JSON attendu : { "team_id": "snowden", "lang": "fr", "photo": "data:image/jpeg;base64,..." }
    Réponse succès : { "uuid": "...", "team_num": 3 }
    Réponse échec  : { "error": "taken" }  (l'équipe vient d'être prise par quelqu'un d'autre)
    """
    data    = request.get_json(silent=True) or {}
    team_id = data.get('team_id', '').strip()
    lang    = data.get('lang', 'fr')
    photo   = data.get('photo', '')        # base64 data-URL, seulement pour "vous"

    if not team_id:
        return jsonify({'error': 'missing team_id'}), 400

    teams = load_teams()

    # Vérification : l'équipe est-elle encore libre ?
    if team_id in teams:
        return jsonify({'error': 'taken'}), 409

    # Génération UUID + numéro d'équipe lisible
    team_uuid = str(uuid.uuid4())
    team_num  = len(teams) + 1

    # Sauvegarde de la photo "Vous" si présente
    photo_path = None
    if photo and photo.startswith('data:image'):
        try:
            PHOTOS_DIR.mkdir(exist_ok=True)
            # Extrait la partie base64 après la virgule
            b64_data   = re.sub(r'^data:image/\w+;base64,', '', photo)
            photo_file = PHOTOS_DIR / f"{team_uuid}.jpg"
            photo_file.write_bytes(base64.b64decode(b64_data))
            photo_path = f"photos/{team_uuid}.jpg"
        except Exception as e:
            print(f"[WARN] Photo upload failed: {e}")

    # Enregistrement de l'équipe
    teams[team_id] = {
        'uuid':          team_uuid,
        'team_num':      team_num,
        'lang':          lang,
        'photo':         photo_path,
        'ip':            request.remote_addr,
        'registered_at': datetime.now().isoformat(timespec='seconds'),
    }
    save_teams(teams)

    print(f"[TEAM]  #{team_num:<3} | {team_id:<20} | {lang} | {request.remote_addr}")

    return jsonify({'uuid': team_uuid, 'team_num': team_num})

# ── API dashboard ─────────────────────────────────────────────────────
@app.route('/dashboard/data')
def dashboard_data():
    """
    Retourne teams + events en JSON (polling toutes les 5 s).
    Réponse : { "teams": { team_id: {...} }, "events": [...] }
    """
    resp = jsonify({
        'teams':  load_teams(),
        'events': load_events(),
    })
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'no-store'
    return resp

@app.route('/dashboard/reset', methods=['POST'])
def dashboard_reset():
    """Efface tous les événements ET remet les équipes à zéro."""
    EVENTS_FILE.write_text('[]', encoding='utf-8')
    TEAMS_FILE.write_text('{}', encoding='utf-8')
    # Supprime les photos de la session
    if PHOTOS_DIR.exists():
        for f in PHOTOS_DIR.glob('*.jpg'):
            f.unlink(missing_ok=True)
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

@app.route('/avatar/<team_id>')
def serve_avatar(team_id):
    """Sert l'image d'un avatar à partir de son id métier."""
    filename = AVATAR_MAP.get(team_id)
    if not filename:
        return '', 404
    return send_from_directory(str(AVATARS_DIR), filename)

@app.route('/team-select')
def team_select_page():
    return send_from_directory(str(HTML_DIR), 'team-select.html')

@app.route('/photos/<filename>')
def serve_photo(filename):
    """Sert les photos 'Vous' uploadées pendant la session."""
    return send_from_directory(str(PHOTOS_DIR), filename)

@app.route('/<path:filename>')
def static_files(filename):
    """Sert tous les fichiers du dossier html/."""
    return send_from_directory(str(HTML_DIR), filename)

# ── Démarrage ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not EVENTS_FILE.exists():
        EVENTS_FILE.write_text('[]', encoding='utf-8')
    if not TEAMS_FILE.exists():
        TEAMS_FILE.write_text('{}', encoding='utf-8')
    PHOTOS_DIR.mkdir(exist_ok=True)

    local_ip = get_local_ip()

    print(f"""
╔══════════════════════════════════════════════╗
║         CyberQuest — Serveur local           ║
╠══════════════════════════════════════════════╣
║  Accessible sur le réseau :                  ║
║    http://{local_ip}:{PORT:<5}               ║
║                                              ║
║  Init participants :  /init                  ║
║  Choix d'équipe :     /team-select           ║
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
