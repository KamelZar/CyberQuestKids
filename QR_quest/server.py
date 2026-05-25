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
import itertools
import json
import os
import queue as _queue
import re
import socket
import string
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, Response, request, redirect, stream_with_context

# ── Config ────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
HTML_DIR    = BASE_DIR / "html"
EVENTS_FILE    = BASE_DIR / "events.json"
TEAMS_FILE     = BASE_DIR / "teams.json"            # équipes enregistrées pour la session
CHAMPIONS_FILE = BASE_DIR / "champions_scores.json" # scores du jeu Champions
PHOTOS_DIR     = BASE_DIR / "photos"                # photos "Vous" uploadées

try:
    PORT = 80 if os.geteuid() == 0 else 8080   # Unix : 80 si root, 8080 sinon
except AttributeError:
    PORT = 8080  # Windows : http.sys réserve le port 80, on utilise 8080

# ── Config routeur (captive portal whitelist) ─────────────────────────
# ROUTER_IP surchargeable via variable d'environnement : set ROUTER_IP=192.168.8.1
ROUTER_IP = os.environ.get('ROUTER_IP', '192.168.8.1')
SSH_KEY   = BASE_DIR / '.ssh' / 'cyberquest_key'   # générée par setup_router.bat


def _get_local_ip() -> str:
    """Détecte l'IP locale sur le même réseau que le routeur (sans connexion réelle)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((ROUTER_IP, 80))
            return s.getsockname()[0]
    except Exception:
        return '192.168.8.100'

# IPs ayant complété le captive portal (session en cours, remis à zéro au redémarrage)
_whitelisted_ips: set = set()
_whitelist_lock = threading.Lock()


def whitelist_ip(client_ip: str) -> None:
    """
    Débloque internet pour une IP après le gotcha (phishing réussi ou bon réflexe CGU).

    1. Mémorise l'IP → captive_probe() retournera Success → OS ferme le captive browser
    2. SSH sur le routeur via clé RSA → iptables ACCEPT avant le DROP → internet rétabli

    Le SSH tourne en thread daemon pour ne pas bloquer la réponse Flask.
    """
    with _whitelist_lock:
        if client_ip in _whitelisted_ips:
            return  # déjà whitelisté, rien à faire
        _whitelisted_ips.add(client_ip)

    def _do_ssh():
        key = str(SSH_KEY)
        if not SSH_KEY.exists():
            print(f"[WHITELIST] ⚠️  Clé SSH introuvable : {key}")
            print(f"[WHITELIST]    Lance setup_router.bat pour la générer")
            return
        try:
            # Idempotent : ajoute ACCEPT seulement si absent, en tête de chaîne
            check = f"iptables -C FORWARD -s {client_ip} -j ACCEPT 2>/dev/null"
            rule  = f"iptables -I FORWARD -s {client_ip} -j ACCEPT"
            result = subprocess.run(
                [
                    'ssh',
                    '-i', key,
                    '-o', 'HostKeyAlgorithms=+ssh-rsa',
                    '-o', 'PubkeyAcceptedKeyTypes=+ssh-rsa',
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'ConnectTimeout=5',
                    '-o', 'BatchMode=yes',   # jamais de prompt mot de passe
                    f'root@{ROUTER_IP}',
                    f'{check} || {rule}'
                ],
                capture_output=True, timeout=10, text=True
            )
            if result.returncode == 0:
                print(f"[WHITELIST] ✅  {client_ip} → internet débloqué")
            else:
                print(f"[WHITELIST] ⚠️  SSH code {result.returncode}: {result.stderr.strip()}")
        except Exception as e:
            print(f"[WHITELIST] ⚠️  SSH échoué pour {client_ip}: {e}")

    threading.Thread(target=_do_ssh, daemon=True).start()

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

def check_uuid(team_id: str):
    """
    Vérifie que le cookie cq_uuid correspond à l'équipe enregistrée.

    Retourne None si tout est OK.
    Retourne une Response 412 (Precondition Failed) si :
      - le cookie cq_uuid est absent
      - l'équipe est inconnue (session nettoyée entre-temps)
      - l'UUID ne correspond pas (vieille session)

    Usage dans une route :
        err = check_uuid(team_id)
        if err: return err
    """
    uuid_cookie = request.cookies.get('cq_uuid', '').strip()
    if not uuid_cookie:
        return jsonify({'error': 'missing_uuid'}), 412
    teams = load_teams()
    team  = teams.get(team_id)
    if not team:
        return jsonify({'error': 'unknown_team'}), 412
    if team.get('uuid') != uuid_cookie:
        return jsonify({'error': 'session_expired'}), 412
    return None

# ── Helpers — champions ───────────────────────────────────────────────
def load_champions():
    if CHAMPIONS_FILE.exists():
        try:
            return json.loads(CHAMPIONS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return []
    return []

def save_champions(scores):
    CHAMPIONS_FILE.write_text(
        json.dumps(scores, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

# ── Lobby Champions (in-memory, session locale) ───────────────────────
# State machine : 'waiting' → 'countdown' → 'playing' → 'waiting'
_champ_lobby: dict = {
    'teams':         {},    # team_id → {team_id, last_seen, status, score}
    'state':         'waiting',
    'countdown_end': None,  # timestamp Unix (float)
    'playing_teams': [],    # équipes présentes au moment du START
}
_champ_lock = threading.Lock()
_LOBBY_TTL  = 12   # secondes avant de considérer une équipe déconnectée
_COUNTDOWN  = 4    # secondes de compte à rebours avant le départ


def _prune_lobby():
    """Retire les équipes silencieuses depuis > _LOBBY_TTL s. !! Appeler sous lock !!"""
    import time as _time
    now   = _time.time()
    stale = [tid for tid, t in _champ_lobby['teams'].items()
             if now - t['last_seen'] > _LOBBY_TTL]
    for tid in stale:
        del _champ_lobby['teams'][tid]


def _check_countdown():
    """Passe de countdown → playing si le délai est écoulé. !! Appeler sous lock !!"""
    import time as _time
    if (_champ_lobby['state'] == 'countdown'
            and _champ_lobby['countdown_end']
            and _time.time() >= _champ_lobby['countdown_end']):
        _champ_lobby['state'] = 'playing'


def _check_all_done():
    """Si toutes les équipes playing ont fini → repasse en waiting. !! Appeler sous lock !!"""
    playing = set(_champ_lobby['playing_teams'])
    if not playing:
        return
    done_statuses = {'eliminated', 'victory'}
    all_done = all(
        _champ_lobby['teams'].get(tid, {}).get('status') in done_statuses
        for tid in playing
    )
    if all_done:
        _champ_lobby['state']         = 'waiting'
        _champ_lobby['countdown_end'] = None
        _champ_lobby['playing_teams'] = []
        # Remettre les équipes encore présentes en 'waiting'
        for t in _champ_lobby['teams'].values():
            if t['status'] in done_statuses:
                t['status'] = 'waiting'
                t['score']  = None

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
    """Efface tous les événements ET remet les équipes + scores Champions à zéro."""
    EVENTS_FILE.write_text('[]', encoding='utf-8')
    TEAMS_FILE.write_text('{}', encoding='utf-8')
    CHAMPIONS_FILE.write_text('[]', encoding='utf-8')
    # Remet le lobby Champions à zéro
    with _champ_lock:
        _champ_lobby['teams']         = {}
        _champ_lobby['state']         = 'waiting'
        _champ_lobby['countdown_end'] = None
        _champ_lobby['playing_teams'] = []
    # Supprime les photos de la session
    if PHOTOS_DIR.exists():
        for f in PHOTOS_DIR.glob('*.jpg'):
            f.unlink(missing_ok=True)
    return jsonify({'ok': True})

def _ssh_router(cmd: str):
    """Helper SSH vers le routeur — retourne (ok, stderr)."""
    key = str(SSH_KEY)
    if not SSH_KEY.exists():
        return False, f'Clé SSH introuvable : {key}. Lance setup_router.bat.'
    try:
        result = subprocess.run(
            [
                'ssh',
                '-i', key,
                '-o', 'HostKeyAlgorithms=+ssh-rsa',
                '-o', 'PubkeyAcceptedKeyTypes=+ssh-rsa',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'ConnectTimeout=5',
                '-o', 'BatchMode=yes',
                f'root@{ROUTER_IP}',
                cmd
            ],
            capture_output=True, timeout=10, text=True
        )
        return result.returncode == 0, result.stderr.strip()
    except Exception as e:
        return False, str(e)


@app.route('/admin/forward', methods=['POST'])
def admin_forward():
    """Réactive le FORWARD DROP — captive portal remis en place."""
    flask_ip = _get_local_ip()
    check_accept = f"iptables -C FORWARD -i br-lan -d {flask_ip} -j ACCEPT 2>/dev/null"
    check_drop   = f"iptables -C FORWARD -i br-lan -j DROP 2>/dev/null"
    rule_accept  = f"iptables -I FORWARD 5 -i br-lan -d {flask_ip} -j ACCEPT"
    rule_drop    = f"iptables -A FORWARD -i br-lan -j DROP"
    cmd = f"{check_accept} || {rule_accept} ; {check_drop} || {rule_drop}"
    ok, err = _ssh_router(cmd)
    if ok:
        # Vider la whitelist locale — les appareils devront repasser par le captive portal
        with _whitelist_lock:
            _whitelisted_ips.clear()
        print("[FORWARD] Captive portal réactivé — whitelist vidée")
        return jsonify({'ok': True})
    print(f"[FORWARD] SSH échoué : {err}")
    return jsonify({'ok': False, 'error': err})


@app.route('/admin/passthrough', methods=['POST'])
def admin_passthrough():
    """
    Supprime le FORWARD DROP → internet rétabli pour tous les participants.
    Le DNS log (dnsmasq) reste actif → les sites visités continuent d'être tracés.
    """
    ok, err = _ssh_router('iptables -D FORWARD -i br-lan -j DROP 2>/dev/null || true')
    if ok:
        print("[PASSTHROUGH] Internet débloqué pour tous les participants")
        return jsonify({'ok': True})
    print(f"[PASSTHROUGH] SSH échoué : {err}")
    return jsonify({'ok': False, 'error': err})

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

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Sert les images statiques depuis QR_quest/images/."""
    return send_from_directory(str(BASE_DIR / 'images'), filename)

@app.route('/team-select')
def team_select_page():
    return send_from_directory(str(HTML_DIR), 'team-select.html')

@app.route('/chemin')
def chemin_page():
    """Hub de navigation — sol LED style Indiana Jones."""
    return send_from_directory(str(HTML_DIR), 'chemin.html')

@app.route('/photos/<filename>')
def serve_photo(filename):
    """Sert les photos 'Vous' uploadées pendant la session."""
    return send_from_directory(str(PHOTOS_DIR), filename)

VIDEO_DIR = BASE_DIR / "video"

@app.route('/video/<filename>')
def serve_video(filename):
    """Sert les trailers d'intro (TRAILER_FR.mp4, TRAILER_NL.mp4, TRAILER_EN.mp4)."""
    return send_from_directory(str(VIDEO_DIR), filename)

@app.route('/champions')
def champions_page():
    return send_from_directory(str(HTML_DIR), 'champions.html')

@app.route('/champions/score', methods=['POST'])
def champions_score_post():
    """
    Enregistre le score d'une équipe après une partie Champions.
    Corps JSON : { team_id, score, questions_answered, lives_remaining, status, retry }
    status : 'eliminated' | 'victory'
    """
    data               = request.get_json(silent=True) or {}
    team_id            = data.get('team_id', '').strip()
    score              = int(data.get('score', 0))
    questions_answered = int(data.get('questions_answered', 0))
    lives_remaining    = int(data.get('lives_remaining', 0))
    status             = data.get('status', 'eliminated')
    retry              = int(data.get('retry', 0))

    if not team_id:
        return jsonify({'error': 'missing team_id'}), 400

    err = check_uuid(team_id)
    if err: return err

    scores = load_champions()
    scores.append({
        'team_id':            team_id,
        'score':              score,
        'questions_answered': questions_answered,
        'lives_remaining':    lives_remaining,
        'status':             status,
        'retry':              retry,
        'timestamp':          datetime.now().isoformat(timespec='seconds'),
    })
    save_champions(scores)
    print(f"[CHAMP] {team_id:<20} | score={score:>5} | {status} | retry={retry}")

    resp = jsonify({'ok': True})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/teams/reset', methods=['POST'])
def teams_reset():
    """Nettoie les équipes (teams.json) sans toucher aux events ni aux scores Champions."""
    TEAMS_FILE.write_text('{}', encoding='utf-8')
    # Supprime aussi les photos liées aux équipes
    if PHOTOS_DIR.exists():
        for f in PHOTOS_DIR.glob('*.jpg'):
            f.unlink(missing_ok=True)
    # Vide le lobby Champions (les équipes ne sont plus valides)
    with _champ_lock:
        _champ_lobby['teams']         = {}
        _champ_lobby['state']         = 'waiting'
        _champ_lobby['countdown_end'] = None
        _champ_lobby['playing_teams'] = []
    print('[RESET] Équipes nettoyées (events et scores conservés)')
    return jsonify({'ok': True})


@app.route('/champions/scores/reset', methods=['POST'])
def champions_scores_reset():
    """Efface uniquement les scores Champions (events et équipes conservés)."""
    CHAMPIONS_FILE.write_text('[]', encoding='utf-8')
    print('[RESET] Scores Champions effacés')
    return jsonify({'ok': True})


@app.route('/champions/scores')
def champions_scores_get():
    """Retourne l'historique complet des scores Champions (pour le leaderboard)."""
    resp = jsonify(load_champions())
    resp.headers['Cache-Control'] = 'no-store'
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

# ── Lobby Champions ───────────────────────────────────────────────────

@app.route('/champions/lobby/state')
def champ_lobby_state():
    """
    Polling des clients (~toutes les 2 s).
    Retourne : { state, countdown_end, teams: [{team_id, status, score}] }
    """
    import time as _time
    with _champ_lock:
        _prune_lobby()
        _check_countdown()

        resp = jsonify({
            'state':         _champ_lobby['state'],
            'countdown_end': _champ_lobby['countdown_end'],
            'teams': [
                {k: v for k, v in t.items() if k != 'last_seen'}
                for t in _champ_lobby['teams'].values()
            ],
        })
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/champions/lobby/heartbeat', methods=['POST'])
def champ_lobby_heartbeat():
    """
    L'équipe signale sa présence (envoyé toutes les 3 s).
    Corps JSON : { team_id, status, score? }
    """
    import time as _time
    data    = request.get_json(silent=True) or {}
    team_id = data.get('team_id', '').strip()
    status  = data.get('status', 'waiting')   # waiting|playing|eliminated|victory
    score   = data.get('score', None)

    if not team_id:
        return jsonify({'error': 'missing team_id'}), 400

    err = check_uuid(team_id)
    if err: return err

    with _champ_lock:
        now = _time.time()
        if team_id not in _champ_lobby['teams']:
            _champ_lobby['teams'][team_id] = {
                'team_id':   team_id,
                'last_seen': now,
                'status':    status,
                'score':     score,
            }
        else:
            t = _champ_lobby['teams'][team_id]
            t['last_seen'] = now
            # Ne jamais rétrograder 'playing' → 'waiting' via heartbeat :
            # le statut 'playing' est posé par /start et doit rester jusqu'à
            # ce que la partie se termine (eliminated / victory).
            if not (t.get('status') == 'playing' and status == 'waiting'):
                t['status'] = status
            if score is not None:
                t['score'] = score

        _check_countdown()
        state = _champ_lobby['state']

    return jsonify({'ok': True, 'state': state})


@app.route('/champions/lobby/start', methods=['POST'])
def champ_lobby_start():
    """
    Lance le compte à rebours si >= 2 équipes présentes.
    Corps JSON : { team_id }
    """
    import time as _time
    data    = request.get_json(silent=True) or {}
    team_id = data.get('team_id', '').strip()

    if not team_id:
        return jsonify({'error': 'missing team_id'}), 400

    err = check_uuid(team_id)
    if err: return err

    with _champ_lock:
        _prune_lobby()
        active = list(_champ_lobby['teams'].keys())

        if len(active) < 2:
            return jsonify({'error': 'not_enough_teams'}), 400
        if _champ_lobby['state'] != 'waiting':
            return jsonify({'error': 'already_started'}), 409

        _champ_lobby['state']         = 'countdown'
        _champ_lobby['countdown_end'] = _time.time() + _COUNTDOWN
        _champ_lobby['playing_teams'] = active[:]
        for tid in active:
            _champ_lobby['teams'][tid]['status'] = 'playing'

    print(f"[CHAMP] Countdown started by {team_id} — {len(active)} équipes")
    return jsonify({'ok': True, 'countdown_end': _champ_lobby['countdown_end']})


@app.route('/champions/lobby/done', methods=['POST'])
def champ_lobby_done():
    """
    L'équipe signale la fin de sa partie (éliminée ou victoire).
    Corps JSON : { team_id, status, score }
    """
    data    = request.get_json(silent=True) or {}
    team_id = data.get('team_id', '').strip()
    status  = data.get('status', 'eliminated')
    score   = int(data.get('score', 0))

    if not team_id:
        return jsonify({'error': 'missing team_id'}), 400

    err = check_uuid(team_id)
    if err: return err

    with _champ_lock:
        if team_id in _champ_lobby['teams']:
            _champ_lobby['teams'][team_id]['status'] = status
            _champ_lobby['teams'][team_id]['score']  = score
        _check_all_done()

    return jsonify({'ok': True})

@app.route('/<path:filename>')
def static_files(filename):
    """Sert tous les fichiers du dossier html/."""
    return send_from_directory(str(HTML_DIR), filename)

# ── Password Check — outil pédagogique ────────────────────────────────
# Architecture : le hash SHA-256 est calculé côté navigateur (Web Crypto API).
# Le serveur ne reçoit jamais le mot de passe en clair, seulement son hash.

_jobs: dict       = {}
_jobs_lock        = threading.Lock()
_DICT_BASE        = BASE_DIR.parent / 'Html'
_DICTS            = [
    ('rockyou-75', _DICT_BASE / 'rockyou-75.txt'),
    ('10-million', _DICT_BASE / '10-million.txt'),
]
_MAX_BF_LEN = 12  # brute force jusqu'à N chars ; au-delà → résistant
_FREQ_DIR    = HTML_DIR / 'frequencyWords'   # fr.txt / nl.txt / en.txt
_FREQ_CACHE: dict = {}  # lang -> {longueur: [mots]} -- charge une fois au demarrage


def _load_freq_by_len(lang: str) -> dict:
    """
    Charge TOUS les mots d un fichier de frequence OpenSubtitles.
    Retourne {longueur: [mots...]} pour lookup O(1) par longueur.
    """
    import unicodedata as _ud

    path = _FREQ_DIR / f'{lang}.txt'
    if not path.exists():
        print(f'[FREQ] {lang}.txt introuvable dans {_FREQ_DIR}')
        return {}

    by_len: dict = {}
    seen: set = set()
    total = 0
    try:
        with open(str(path), encoding='utf-8', errors='replace') as fh:
            for line in fh:
                parts = line.strip().split(' ')
                if not parts:
                    continue
                word = parts[0].lower()
                if len(word) < 3:
                    continue

                # Mots composes avec tiret (loup-garou -> loupgarou)
                if '-' in word:
                    merged = word.replace('-', '')
                    if (len(merged) >= 3
                            and not any(c in merged for c in ("'", "’", ' '))
                            and all(_ud.category(c).startswith('L') for c in merged)):
                        if merged not in seen:
                            by_len.setdefault(len(merged), []).append(merged)
                            seen.add(merged)
                            total += 1
                    continue

                if any(c in word for c in ("‘", "’", ' ',
                       '0','1','2','3','4','5','6','7','8','9')):
                    continue
                if not all(_ud.category(c).startswith('L') for c in word):
                    continue

                if word not in seen:
                    by_len.setdefault(len(word), []).append(word)
                    seen.add(word)
                    total += 1

                # Variante sans accents (ete -> ete, prenom -> prenom)
                flat = _ud.normalize('NFD', word)
                flat = ''.join(c for c in flat if _ud.category(c) != 'Mn')
                if flat != word and flat not in seen:
                    by_len.setdefault(len(flat), []).append(flat)
                    seen.add(flat)
                    total += 1

    except OSError as exc:
        print(f'[FREQ] Erreur lecture {path}: {exc}')

    print(f'[FREQ] {lang} : {total} mots charges ({len(by_len)} longueurs differentes)')
    return by_len


def _get_freq_by_len(lang: str) -> dict:
    """Retourne le cache {longueur: [mots]} pour la langue (charge une fois)."""
    if lang not in _FREQ_CACHE:
        _FREQ_CACHE[lang] = _load_freq_by_len(lang)
    return _FREQ_CACHE[lang]


# ── Mots de base personnalisés (contexte FR/NL/BE) ────────────────────
# Ces mots ne sont pas forcément dans le top du rockyou, mais sont
# typiques du public cible (11-15 ans, Belgique francophone/néerlandophone).
_CUSTOM_BASES = [
    # Famille / proches
    'maman','papa','mamie','papi','frere','soeur','famille','bebe',
    # Animaux
    'chien','chat','lapin','oiseau','poisson','cheval','hamster',
    # Nature / quotidien
    'soleil','lune','etoile','fleur','jardin','maison','ecole',
    # Mots FR courants mal perçus comme "forts"
    'amour','coeur','secret','motdepasse','bonjour','salut','coucou',
    'football','basket','tennis','gaming','minecraft','fortnite','roblox',
    # Géographie BE/FR
    'belgique','bruxelles','liege','gand','anvers','paris','france',
    # Mots NL courants
    'mama','papa','hond','kat','school','wachtwoord','geheim','belgie',
    'brussel','antwerpen','gent','voetbal','hallo','dag',
    # Prénoms populaires Belgique
    'sarah','emma','lea','alice','marie','camille','manon','chloe','lena',
    'lucas','thomas','hugo','noah','paul','nicolas','pierre','axel','rayan',
    # Termes "cyber" que les jeunes pensent forts
    'hacker','cyber','admin','ninja','dragon','phoenix','shadow','master',
    'hunter','killer','legend','gamer','player','warrior','cobra','titan',
    # Patterns classiques
    'azerty','qwerty','iloveyou','jetaime','superman','batman','spiderman',
    'pokemon','naruto','onepiece','letsgo','welcome','password','passw0rd',
]

# ── Suppléments culturels par langue (public 11-15 ans, Belgique 2026) ──
_EXTRA_FR = [
    # ⚽ Football belge & français
    'anderlecht','standard','brugge','genk','charleroi','gent','cercle',
    'psg','marseille','lyon','monaco','lens','rennes','nantes','lorient',
    # 🌟 Joueurs / figures
    'mbappe','ronaldo','messi','benzema','neymar','lukaku','hazard','courtois',
    # 🎵 Musique FR/BE (populaire 2024-2026)
    'angele','stromae','orelsan','nekfeu','ninho','damso','hamza','sch',
    'aya','louane','vitaa','slimane','jul','leto','lacrim','rohff',
    # 🎤 K-pop (énorme chez les ados francophones)
    'bts','blackpink','twice','aespa','newjeans','ive','seventeen',
    'stray','txt','enhypen','le sserafim','nmixx','itzy',
    'jungkook','taehyung','jimin','suga','rm','jin','jhope',
    'lisa','jennie','rose','jisoo','winter','karina','giselle','ningning',
    # 🎮 Gaming / personnages
    'valorant','apex','warzone','fivem','minecraft','roblox','fortnite',
    'mario','luigi','zelda','link','pikachu','sonic','kirby','crewmate',
    'creeper','herobrine','steve','goku','vegeta',
    # 📺 Séries / manga / animé
    'squidgame','lupin','miraculous','asterix','tintin','spirou',
    'naruto','sasuke','luffy','zoro','ichigo','eren','levi',
    'gojo','itadori','tanjiro','nezuko','zenitsu',
    'demonslayer','jujutsu','attacktitan','onepiece',
    # 🗺️ Villes belges FR
    'namur','mons','liege','tournai','verviers','bastogne',
    'dinant','spa','ardennes','charleroi',
    # 💬 Slang ados FR 2026
    'wesh','ouf','stylee','swag','slay','drip','vibe','chill','ratio',
    # 🍫 Références belges
    'chocolat','gaufre','nutella','kebab','speculoos',
]

_EXTRA_NL = [
    # ⚽ Football belge & néerlandais
    'clubbrugge','anderlecht','gent','genk','mechelen','cercle',
    'beerschot','antwerp','lommel','stvv',
    'ajax','psv','feyenoord','twente',
    # 🌟 Joueurs belges
    'lukaku','courtois','hazard','tielemans','doku','theate','onana',
    # 🎵 Musique NL/BE
    'angele','k3','nachtwacht','goldband','josylvio','die antwoord',
    'niels','metejoor','bazart','novastar',
    # 🎤 K-pop (même engouement côté flamand)
    'bts','blackpink','twice','aespa','newjeans','ive','seventeen',
    'stray','jungkook','taehyung','jimin','lisa','jennie','rose',
    # 🎮 Gaming
    'valorant','apex','warzone','minecraft','roblox','fortnite','fivem',
    'mario','pikachu','zelda','creeper','herobrine',
    # 📺 Émissions / séries NL/BE
    'nachtwacht','ketnet','kampioenen','bumba','plop','piraat',
    'samson','gert','piet','jolien',
    # 🗺️ Villes belges NL
    'oostende','kortrijk','roeselare','hasselt','turnhout',
    'mechelen','leuven','aalst','dendermonde','sint-niklaas',
    # 💬 Slang ados NL 2026
    'vet','gaaf','sick','tof','lekker','chill','lit','fire','snappen',
    # 🍟 Références flamandes
    'frieten','wafel','speculoos','chocomel','stroopwafel',
]

_EXTRA_EN = [
    # ⚽ Premier League / international
    'arsenal','chelsea','liverpool','manchester','city','united','tottenham',
    'barcelona','realmadrid','juventus','intermilan','bayern',
    # 🌟 Joueurs international
    'haaland','salah','kane','bellingham','rashford','saka','vinicius',
    # 🎵 Musique EN (teen 2024-2026)
    'taylor','swift','billie','eilish','olivia','rodrigo','ariana','grande',
    'weeknd','drake','travis','kanye','sabrina','carpenter','chappell','roan',
    'dua','lipa','halsey','shawn','mendes','harry','styles',
    # 🎤 K-pop (EN crossover)
    'bts','blackpink','twice','aespa','newjeans','ive','suga','jungkook',
    'lisa','jennie','winter','karina',
    # 🎮 Gaming / FPS / RPG
    'valorant','warzone','pubg','overwatch','league','apex','gta','fivem',
    'eldenring','elden','baldur','minecraft','roblox','fortnite',
    'masterchief','kratos','geralt','alyx','lara','ezio','joel','ellie',
    'creeper','herobrine','steve','mario','pikachu','sonic',
    # 🧙 Harry Potter
    'harry','hermione','ron','dumbledore','voldemort','hogwarts',
    'gryffindor','slytherin','hufflepuff','ravenclaw','snape','malfoy',
    # 🚀 Star Wars / Marvel
    'vader','yoda','jedi','skywalker','mandalorian','grogu',
    'ironman','thanos','thor','spiderman','deadpool','wolverine','loki',
    # 💬 Slang EN ados 2026
    'rizz','slay','bussin','sigma','ohio','goat','ngl','nocap',
    'drip','vibe','banger','ratio','lowkey',
    # 🎬 Shows / fandoms
    'stranger','things','wednesday','squidgame','arcane','edgerunners',
    'mandalorian','andor','peaky','blinders',
]

# Index rapide : lang → liste supplémentaire (culture / pop)
_LANG_EXTRAS: dict = {'fr': _EXTRA_FR, 'nl': _EXTRA_NL, 'en': _EXTRA_EN}


# ── Moteur de mutations ────────────────────────────────────────────────
def _apply_rules(word: str) -> set:
    """
    Génère ~1 000 variantes d'un mot de base par règles de mutation.
    Couvre : leet speak (léger + complet), capitalize, UPPER,
             suffixes numériques, années, symboles et leurs combinaisons.
    """
    w = word.strip()
    if not w or len(w) > 20:
        return set()

    wl = w.lower()
    wc = wl.capitalize()
    wu = wl.upper()

    def _lm(s):   # leet minimal  : juste a→@  (sans s, e, o)
        return s.replace('a','@').replace('A','@')

    def _lo(s):   # leet doux    : a→@  e→3  o→0  (sans s→$)
        return (s.replace('a','@').replace('A','@')
                 .replace('e','3').replace('E','3')
                 .replace('o','0').replace('O','0'))

    def _ls(s):   # leet léger   : a→@  e→3  o→0  s→$
        return (_lo(s).replace('s','$').replace('S','$'))

    def _lh(s):   # leet complet : + i→1  t→7  l→1  b→8  g→9
        return (_ls(s).replace('i','1').replace('I','1')
                       .replace('t','7').replace('T','7')
                       .replace('l','1').replace('L','1')
                       .replace('b','8').replace('B','8')
                       .replace('g','9').replace('G','9'))

    def _l4(s):   # leet alt     : a→4  e→3  o→0  s→$  i→!  (style "hacker")
        return (s.replace('a','4').replace('A','4')
                 .replace('e','3').replace('E','3')
                 .replace('o','0').replace('O','0')
                 .replace('s','$').replace('S','$')
                 .replace('i','!').replace('I','!'))

    def _l5(s):   # leet doux v2 : a→4  e→3  o→0  i→!  (sans s→$)
        return (s.replace('a','4').replace('A','4')
                 .replace('e','3').replace('E','3')
                 .replace('o','0').replace('O','0')
                 .replace('i','!').replace('I','!'))

    bases = [
        wl,           # password
        wc,           # Password
        wu,           # PASSWORD
        _lm(wl),      # p@ssword         ← juste a→@
        _lm(wc),      # P@ssword         ← très courant
        _lo(wl),      # p@ssw0rd         ← sans s→$
        _lo(wc),      # P@ssw0rd
        _ls(wl),      # p@$$word
        _lh(wl),      # p@$$w0rd
        _ls(wc),      # P@$$word
        _lh(wc),      # P@$$w0rd
        _lh(wu),      # P@$$W0RD         ← le "classique"
        _l4(wl),      # p4$$w0rd
        _l4(wc),      # P4$$w0rd
        _l4(wu),      # P4$$W0RD
        _l5(wl),      # s0l3!l           ← sans s→$ (couvre soleil, etc.)
        _l5(wc),      # S0l3!l
        wl[::-1],     # drowssap         (reverse)
    ]

    # Suffixes issus des analyses réelles de fuites de données
    _NUM = ['1','2','3','11','12','21','23','42','69','00','01','99',
            '007','100','123','321','456','789','666','999','000',
            '1234','4321','1111','2222','9999','12345']
    _SYM = ['!','!!','!!!','?','@','#','$','.','*','&','_']
    _YRS = [str(y) for y in range(1970, 2027)]
    _CMB = ['123!','1234!','12345!','123@','123#','1!','2!',
            '1234@','2024!','2025!','2026!','!123','@2024']

    suffixes = [''] + _NUM + _SYM + _YRS + _CMB \
             + [y+'!' for y in _YRS[20:]]   # années récentes + !

    result = set()
    for base in bases:
        if base:
            for suf in suffixes:
                result.add(base + suf)
    result.add(wl + wl)   # passwordpassword

    # ── Préfixes : années + nombres AVANT la base ──────────────────
    # Couvre : "2024Maman", "123Password", "01Soleil", "99Dragon!"
    # Appliqués uniquement sur les 3 formes sans leet (évite l'explosion)
    _PFX_YRS = [str(y) for y in range(1990, 2027)]
    _PFX_NUM = ['1','2','3','00','01','07','12','21','23','42','69','99','123','007']
    for base in (wl, wc, wu):
        for pfx in _PFX_YRS + _PFX_NUM:
            result.add(pfx + base)          # 2024maman / 2024Maman / 2024MAMAN
            result.add(pfx + base + '!')    # 2024Maman!  ← pattern très répandu

    return result


def _run_pw_check(target_hash: str, q: '_queue.Queue',
                  lang: str = 'fr', max_len: int = 0):
    """
    Tourne dans un thread daemon. Envoie des events JSON dans la queue.

    max_len > 0 : longueur exacte du mot de passe connue côté client.
                  Chaque phase ne teste QUE les candidats de cette longueur →
                  gains massifs (brute force = 1 longueur au lieu de 1..8).
    max_len = 0 : longueur inconnue, comportement classique (aucun filtre).
    """
    import hashlib, time

    TIMEOUT  = 60
    start    = time.time()
    deadline = start + TIMEOUT
    total    = 0
    found    = False

    def _h(s):
        return hashlib.sha256(s.encode('utf-8', errors='replace')).hexdigest()

    # ── Phase 1 : dictionnaire ─────────────────────────────────────
    q.put({'phase': 'start', 'max_len': max_len})

    for dict_name, path in _DICTS:
        if not path.exists():
            q.put({'phase': 'dict_missing', 'dict': dict_name})
            continue
        q.put({'phase': 'dict', 'dict': dict_name, 'attempts': total, 'elapsed': 0})
        try:
            with open(str(path), 'r', encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    if time.time() >= deadline:
                        break
                    candidate = line.rstrip('\n')
                    # Optimisation : sauter les mots de mauvaise longueur
                    if max_len > 0 and len(candidate) != max_len:
                        continue
                    total += 1
                    if total % 20_000 == 0:
                        q.put({'phase': 'dict', 'dict': dict_name,
                               'attempts': total,
                               'elapsed': round(time.time() - start, 1)})
                    if _h(candidate) == target_hash:
                        found = True
                        break
        except OSError as exc:
            q.put({'phase': 'error', 'msg': str(exc)})

        if found or time.time() >= deadline:
            break

    elapsed = round(time.time() - start, 1)
    if found:
        q.put({'done': True, 'found': True, 'method': 'dictionary',
               'attempts': total, 'elapsed': elapsed})
        return
    if time.time() >= deadline:
        q.put({'done': True, 'found': False, 'attempts': total, 'elapsed': TIMEOUT})
        return

    # -- Phase 1.5 : mutations -------------------------------------------------
    # ── Phase 1.5 : mutations (approche stratifiée) ───────────────────
    # Principe : chercher par ordre décroissant de longueur de mot de base,
    # de max_len (overhead 0) jusqu'à max_len-4 (overhead 4 max).
    # → les patterns les plus probables (mot long, peu de suffixe) passent en premier.
    # → early exit dès qu'on trouve, les rounds suivants ne s'exécutent pas.
    _MAX_RULES_OVERHEAD = 4  # suffixe/préfixe max testé

    lang_extras = _LANG_EXTRAS.get(lang, _EXTRA_FR)
    other_langs  = [l for l in ('fr', 'nl', 'en') if l != lang]

    # Pré-bucketer rockyou (top 15K) par longueur de mot
    rk_by_len: dict = {}
    rk_path = _DICT_BASE / 'rockyou-75.txt'
    if rk_path.exists():
        try:
            with open(str(rk_path), 'r', encoding='utf-8', errors='replace') as fh:
                for i, line in enumerate(fh):
                    if i >= 15_000:
                        break
                    w = line.rstrip('\n').strip()
                    if w:
                        bl = len(w.lower())
                        rk_by_len.setdefault(bl, []).append(w)
        except OSError:
            pass

    # Pré-bucketer extras culturels + bases universelles par longueur
    extra_by_len: dict = {}
    for w in list(lang_extras) + list(_CUSTOM_BASES):
        extra_by_len.setdefault(len(w.lower()), []).append(w)

    def _add_exact(sources, seen_round, iterable, target_len):
        """Ajoute les mots de longueur exacte target_len, dédupliqués."""
        for w in iterable:
            wl = w.lower()
            if len(wl) == target_len and wl not in seen_round:
                sources.append(w)
                seen_round.add(wl)

    # Bornes de la boucle stratifiée
    if max_len > 0:
        bl_min = max(1, max_len - _MAX_RULES_OVERHEAD)
        bl_max = max_len
    else:
        bl_min = bl_max = None   # sans filtre : boucle plate ci-dessous

    q.put({'phase': 'rules', 'stage': 'start', 'attempts': total})

    if max_len > 0:
        # ── Boucle stratifiée ──────────────────────────────────────────
        for base_len in range(bl_max, bl_min - 1, -1):
            if time.time() >= deadline:
                break

            sources: list = []
            seen_round: set = set()
            for l_lang in [lang] + other_langs:
                _add_exact(sources, seen_round,
                           _get_freq_by_len(l_lang).get(base_len, []), base_len)
            _add_exact(sources, seen_round, extra_by_len.get(base_len, []), base_len)
            _add_exact(sources, seen_round, rk_by_len.get(base_len, []), base_len)

            q.put({'phase': 'rules', 'stage': 'round',
                   'base_len': base_len, 'overhead': max_len - base_len,
                   'sources': len(sources), 'attempts': total})

            for idx, word in enumerate(sources):
                if time.time() >= deadline:
                    break
                if idx % 500 == 0 and idx > 0:
                    q.put({'phase': 'rules', 'stage': 'progress',
                           'word': word, 'attempts': total,
                           'elapsed': round(time.time() - start, 1)})
                for variant in _apply_rules(word):
                    if len(variant) != max_len:
                        continue
                    total += 1
                    if _h(variant) == target_hash:
                        q.put({'done': True, 'found': True, 'method': 'rules',
                               'base_word': word,
                               'attempts': total,
                               'elapsed': round(time.time() - start, 1)})
                        return
    else:
        # ── Sans max_len : boucle plate sur tous les mots ─────────────
        rule_sources: list = []
        seen_set: set = set()

        def _add_words(iterable):
            for w in iterable:
                wl = w.lower()
                if wl not in seen_set:
                    rule_sources.append(w)
                    seen_set.add(wl)

        for l_lang in [lang] + other_langs:
            _add_words([w for bucket in _get_freq_by_len(l_lang).values() for w in bucket])
        _add_words(lang_extras)
        _add_words(_CUSTOM_BASES)
        _add_words([w for bucket in rk_by_len.values() for w in bucket])

        for idx, word in enumerate(rule_sources):
            if time.time() >= deadline:
                break
            if idx % 500 == 0 and idx > 0:
                q.put({'phase': 'rules', 'stage': 'progress',
                       'word': word, 'attempts': total,
                       'elapsed': round(time.time() - start, 1),
                       'pct': round(idx / len(rule_sources) * 100)})
            for variant in _apply_rules(word):
                total += 1
                if _h(variant) == target_hash:
                    q.put({'done': True, 'found': True, 'method': 'rules',
                           'base_word': word,
                           'attempts': total,
                           'elapsed': round(time.time() - start, 1)})
                    return

    elapsed = round(time.time() - start, 1)
    if time.time() >= deadline:
        q.put({'done': True, 'found': False, 'attempts': total, 'elapsed': elapsed})
        return

    # ── Phase 2 : brute force ──────────────────────────────────────
    # Si la longueur est connue et dépasse _MAX_BF_LEN, inutile d'essayer
    if max_len > _MAX_BF_LEN:
        q.put({'done': True, 'found': False, 'attempts': total, 'elapsed': elapsed})
        return

    charsets = [
        ('a-z',      string.ascii_lowercase),
        ('a-z0-9',   string.ascii_lowercase + string.digits),
        ('alphanum', string.ascii_letters   + string.digits),
        ('full',     string.ascii_letters   + string.digits + string.punctuation),
    ]

    # Si longueur connue → tester uniquement cette longueur (gain énorme)
    bf_start = max_len if max_len > 0 else 1
    bf_end   = max_len if max_len > 0 else _MAX_BF_LEN

    stop = False
    for length in range(bf_start, bf_end + 1):
        if stop:
            break
        for cs_name, charset in charsets:
            if time.time() >= deadline:
                stop = True
                break
            q.put({'phase': 'brute', 'length': length, 'charset': cs_name,
                   'attempts': total, 'elapsed': round(time.time() - start, 1)})
            for combo in itertools.product(charset, repeat=length):
                if time.time() >= deadline:
                    stop = True
                    break
                total += 1
                if total % 100_000 == 0:
                    q.put({'phase': 'brute', 'length': length, 'charset': cs_name,
                           'attempts': total, 'elapsed': round(time.time() - start, 1)})
                if _h(''.join(combo)) == target_hash:
                    found = True
                    stop  = True
                    break
            if stop:
                break

    elapsed = round(time.time() - start, 1)
    if found:
        q.put({'done': True, 'found': True, 'method': 'brute-force',
               'attempts': total, 'elapsed': elapsed})
    else:
        q.put({'done': True, 'found': False, 'attempts': total, 'elapsed': elapsed})


@app.route('/poster')
def poster_page():
    """Sert le poster interactif depuis la racine du projet."""
    return send_from_directory(str(BASE_DIR.parent), 'password-poster.html')

@app.route('/phishing/catch', methods=['POST'])
def phishing_catch():
    """Reçoit les credentials anonymisés depuis les pages de phishing pédagogique."""
    data   = request.get_json(silent=True) or {}
    email  = data.get('email', '').strip()[:120]
    pw_len = max(0, int(data.get('pw_length', 0)))
    source = data.get('source', 'unknown')[:20]
    lang   = data.get('lang', 'fr')[:2]

    def anon_email(e):
        at = e.find('@')
        if not e:        return '***'
        if at < 0:       return e[:1] + '***'
        return e[:1] + '***' + e[at:]

    event = {
        'type':      'phishing_victim',
        'source':    source,
        'email':     anon_email(email),
        'pw_length': pw_len,
        'lang':      lang,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'ip':        request.remote_addr,
    }
    # Champs supplémentaires signup (déjà anonymisés côté client)
    for field in ('initials', 'phone_end', 'zipcode', 'bank', 'school', 'gender'):
        val = data.get(field, '')
        if val:
            event[field] = str(val)[:40]

    append_event(event)
    print(f"[PHISH] {source:<12} | {anon_email(email):<25} | pw_len={pw_len}")

    # Gotcha affiché → débloquer internet pour cet appareil
    whitelist_ip(request.remote_addr)

    resp = jsonify({'ok': True})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'no-store'
    return resp

@app.route('/phishing/terms-click', methods=['POST'])
def phishing_terms_click():
    """Enregistre qu'un participant a cliqué sur les CGU / Politique avant de soumettre."""
    data   = request.get_json(silent=True) or {}
    lang   = data.get('lang', 'fr')[:2]
    source = data.get('source', 'signup')[:20]

    event = {
        'type':      'terms_click',
        'source':    source,
        'lang':      lang,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'ip':        request.remote_addr,
    }
    append_event(event)
    print(f"[TERMS] ✅ bon réflexe — {request.remote_addr} ({lang})")

    # Gotcha affiché (bon réflexe) → débloquer internet pour cet appareil
    whitelist_ip(request.remote_addr)

    resp = jsonify({'ok': True})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Cache-Control'] = 'no-store'
    return resp

@app.route('/captive')
def captive_portal():
    """Point d'entrée du captive portal — redirige vers NexaPlay login en mode portal."""
    return redirect('/phishing/login?portal=1')

# ── Sondes OS captive portal ──────────────────────────────────────────
# iOS / macOS détectent un captive portal si ces URLs ne retournent pas
# le contenu attendu → on redirige vers /captive.

@app.route('/hotspot-detect.html')          # iOS / macOS
@app.route('/library/test/success.html')    # iOS ancien
@app.route('/generate_204')                 # Android Chrome
@app.route('/gen_204')                      # Android fallback
@app.route('/connecttest.txt')              # Windows 10/11
@app.route('/ncsi.txt')                     # Windows NCSI
@app.route('/redirect')                     # Android générique
def captive_probe():
    """
    Intercepte les sondes de détection captive portal des différents OS.
    - IP non whitelistée → redirect /captive (portal pas encore fait)
    - IP whitelistée     → réponse Success  (OS ferme le captive browser)
    """
    if request.remote_addr in _whitelisted_ips:
        # Signale à l'OS que le captive portal est satisfait
        return '<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>', 200
    return redirect('/captive', code=302)

@app.route('/phishing/roblox')
def phishing_roblox():
    return send_from_directory(str(HTML_DIR / 'phishing' / 'roblox'), 'login.html')

@app.route('/phishing/instagram')
def phishing_instagram():
    return send_from_directory(str(HTML_DIR / 'phishing' / 'instagram'), 'login.html')

@app.route('/phishing/google')
def phishing_google():
    return send_from_directory(str(HTML_DIR / 'phishing' / 'google'), 'login.html')

@app.route('/phishing/tiktok')
def phishing_tiktok():
    return send_from_directory(str(HTML_DIR / 'phishing' / 'tiktok'), 'login.html')

@app.route('/phishing/login')
def phishing_login():
    return send_from_directory(str(HTML_DIR / 'phishing' / 'login'), 'index.html')

@app.route('/phishing/signup')
def phishing_signup():
    return send_from_directory(str(HTML_DIR / 'phishing' / 'signup'), 'index.html')

@app.route('/init-poster')
def init_poster_page():
    """Sert l'affiche d'initialisation (avec QR codes) via Flask."""
    return send_from_directory(str(BASE_DIR), 'poster-init.html')

@app.route('/api/server-url')
def api_server_url():
    """Retourne l'URL LAN du serveur pour que poster-init.html la pré-remplisse."""
    ip   = get_local_ip()
    resp = jsonify({'url': f'http://{ip}:{PORT}/init'})
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/password-check')
def password_check_page():
    return send_from_directory(str(HTML_DIR), 'password-check.html')


@app.route('/password-check/start', methods=['POST'])
def password_check_start():
    data        = request.get_json(silent=True) or {}
    target_hash = data.get('hash', '').lower().strip()
    lang        = data.get('lang', 'fr').lower().strip()
    if lang not in _LANG_EXTRAS:
        lang = 'fr'

    # Longueur du mot de passe (capturée côté client avant effacement)
    # 0 = inconnue → comportement classique (aucun filtre de longueur)
    try:
        max_len = max(0, int(data.get('len', 0)))
    except (TypeError, ValueError):
        max_len = 0

    if not re.match(r'^[a-f0-9]{64}$', target_hash):
        return jsonify({'error': 'invalid_hash'}), 400

    with _jobs_lock:
        if len(_jobs) >= 5:           # max 5 analyses simultanées (serveur local)
            return jsonify({'error': 'server_busy'}), 503
        job_id = str(uuid.uuid4())[:12]
        q: '_queue.Queue' = _queue.Queue()
        _jobs[job_id] = q

    threading.Thread(target=_run_pw_check, args=(target_hash, q, lang, max_len),
                     daemon=True).start()
    return jsonify({'job_id': job_id})


@app.route('/password-check/<job_id>/stream')
def password_check_stream(job_id):
    with _jobs_lock:
        q = _jobs.get(job_id)
    if q is None:
        return jsonify({'error': 'unknown_job'}), 404

    def _generate():
        try:
            while True:
                try:
                    msg = q.get(timeout=70)
                    yield f"data: {json.dumps(msg)}\n\n"
                    if msg.get('done'):
                        break
                except _queue.Empty:
                    yield f"data: {json.dumps({'done': True, 'found': False, 'timeout': True, 'attempts': 0, 'elapsed': 60})}\n\n"
                    break
        finally:
            with _jobs_lock:
                _jobs.pop(job_id, None)

    return Response(
        stream_with_context(_generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control':      'no-cache',
            'X-Accel-Buffering':  'no',
            'Access-Control-Allow-Origin': '*',
        },
    )


# ── Démarrage ─────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not EVENTS_FILE.exists():
        EVENTS_FILE.write_text('[]', encoding='utf-8')
    if not TEAMS_FILE.exists():
        TEAMS_FILE.write_text('{}', encoding='utf-8')
    if not CHAMPIONS_FILE.exists():
        CHAMPIONS_FILE.write_text('[]', encoding='utf-8')
    PHOTOS_DIR.mkdir(exist_ok=True)

    # Precharge les 3 listes de frequence au demarrage (evite latence premier eleve)
    print('[FREQ] Prechargement des listes de frequence...')
    for _lang in ('fr', 'nl', 'en'):
        _get_freq_by_len(_lang)
    print('[FREQ] Pret.')

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
        threaded=True,        # nécessaire pour SSE + brute force en parallèle
    )
