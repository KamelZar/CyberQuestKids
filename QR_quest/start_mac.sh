#!/bin/bash
# ─────────────────────────────────────────────
#  CyberQuest — Lancement Mac
#  Usage :
#    ./start_mac.sh           (= --start)
#    ./start_mac.sh --start
#    ./start_mac.sh --stop
#    ./start_mac.sh --restart
#
#  Détecte automatiquement .venv si présent (mode dev)
# ─────────────────────────────────────────────

PORT=8080
DASHBOARD="http://localhost:$PORT/dashboard"
POSTER="http://localhost:$PORT/init-poster"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/.cyberquest.pid"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

# ── Fonctions ─────────────────────────────────

header() {
  echo ""
  echo "╔══════════════════════════════════════════════╗"
  echo "║       CyberQuest — Démarrage Mac             ║"
  echo "╚══════════════════════════════════════════════╝"
  echo ""
}

activate_venv_if_exists() {
  if [ -d "$VENV_DIR" ]; then
    echo "🐍 .venv détecté — activation..."
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    echo "   ✅ Environnement virtuel activé"
  fi
}

check_deps() {
  if ! command -v python3 &>/dev/null; then
    echo "❌ python3 introuvable. Installe-le via https://python.org"
    exit 1
  fi

  # Active .venv si présent
  activate_venv_if_exists

  if ! python3 -c "import flask" &>/dev/null; then
    echo "⚙️  Flask non installé — installation en cours..."
    pip3 install flask
  fi
}

do_stop() {
  # 1. Essaie via le fichier PID
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID"
      echo "🛑 Serveur arrêté (PID $PID)"
    fi
    rm -f "$PID_FILE"
  fi

  # 2. Filet de sécurité : tue tout process qui occupe le port (démarré manuellement)
  PORT_PID=$(lsof -ti:$PORT 2>/dev/null)
  if [ -n "$PORT_PID" ]; then
    echo "🛑 Process résiduel sur le port $PORT tué (PID $PORT_PID)"
    kill -9 $PORT_PID 2>/dev/null
  fi

  echo "✅ Port $PORT libéré"
}

do_start() {
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
      echo "⚠️  Le serveur tourne déjà (PID $PID)"
      echo "   Utilise --restart pour le redémarrer"
      exit 1
    fi
  fi

  check_deps

  echo "🚀 Démarrage du serveur Flask sur le port $PORT..."
  cd "$SCRIPT_DIR"
  python3 server.py &
  SERVER_PID=$!
  echo $SERVER_PID > "$PID_FILE"

  echo "⏳ En attente du serveur..."
  for i in $(seq 1 10); do
    if curl -s "http://localhost:$PORT/dashboard" -o /dev/null; then
      break
    fi
    sleep 1
  done

  echo "🌐 Ouverture du dashboard et du poster..."
  open "$DASHBOARD"
  open "$POSTER"

  echo ""
  echo "✅ Serveur démarré (PID $SERVER_PID)"
  echo "   Dashboard : $DASHBOARD"
  echo "   Arrêt     : ./start_mac.sh --stop"
  echo ""

  wait $SERVER_PID
  rm -f "$PID_FILE"
}

# ── Main ──────────────────────────────────────

header

case "${1:---start}" in
  --start)
    do_start
    ;;
  --stop)
    do_stop
    ;;
  --restart)
    do_stop
    sleep 1
    do_start
    ;;
  *)
    echo "Usage : $0 [--start|--stop|--restart]"
    exit 1
    ;;
esac
