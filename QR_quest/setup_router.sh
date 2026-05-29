#!/bin/bash
# =============================================================================
# CyberQuestKids — Configuration routeur GL.iNet (Mac)
#
# Usage :
#   ./setup_router.sh                  → --setup       (défaut)
#   ./setup_router.sh --setup          → setup complet (dnsmasq + DNAT + FORWARD DROP)
#   ./setup_router.sh --forward        → active uniquement les règles FORWARD DROP
#   ./setup_router.sh --passthrough    → supprime le FORWARD DROP (internet rétabli, DNS log actif)
#   ./setup_router.sh --transparent    → nettoie TOUT (accès captive portal réseau mère)
#
# Log : setup_router.log (même dossier, horodaté)
# =============================================================================

set -euo pipefail

# ── Paramètres ────────────────────────────────────────────────────────────────
MODE="${1:---setup}"
ROUTER_IP="${ROUTER_IP:-192.168.8.1}"
FLASK_PORT=8080

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/setup_router.log"
SSH_DIR="$SCRIPT_DIR/.ssh"
KEY_FILE="$SSH_DIR/cyberquest_key"

# ── Couleurs ANSI ─────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
MAGENTA='\033[0;35m'
RESET='\033[0m'

# ── Logging ───────────────────────────────────────────────────────────────────
log()      { echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"; }
step()     { echo -e "\n${CYAN}>>> $*${RESET}";         log "=== $*"; }
ok()       { echo -e "    ${GREEN}[OK]${RESET} $*";     log "    [OK] $*"; }
warn()     { echo -e "    ${YELLOW}[!]  $*${RESET}";    log "    [!]  $*"; }
fail()     { echo -e "    ${RED}[ERREUR]${RESET} $*";   log "    [ERREUR] $*"; exit 1; }
out()      { echo -e "    ${GRAY}$*${RESET}";           log "    $*"; }

# ── Détection IP locale sur le réseau du routeur ──────────────────────────────
get_flask_ip() {
    # Utilise python3 pour trouver l'IP locale qui rejoint le routeur
    python3 -c "
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('$ROUTER_IP', 80))
    print(s.getsockname()[0])
    s.close()
except Exception:
    pass
" 2>/dev/null
}

# ── Exécuter une commande SSH + logger la sortie ──────────────────────────────
ssh_cmd() {
    local cmd="$1"
    local label="$2"
    local allow_fail="${3:-false}"

    out "-> $label"
    log "   CMD: $cmd"

    local ssh_args=(-o HostKeyAlgorithms=+ssh-rsa
                    -o PubkeyAcceptedAlgorithms=+ssh-rsa
                    -o StrictHostKeyChecking=no
                    -o ConnectTimeout=5)

    if [ -f "$KEY_FILE" ]; then
        ssh_args+=(-i "$KEY_FILE" -o BatchMode=yes)
    fi

    local output
    output=$(ssh "${ssh_args[@]}" "root@$ROUTER_IP" "$cmd" 2>&1) && local rc=0 || local rc=$?

    while IFS= read -r line; do
        out "   $line"
        log "   $line"
    done <<< "$output"

    if [ $rc -ne 0 ] && [ "$allow_fail" != "true" ]; then
        fail "Échec (code $rc) : $label"
    fi
    if [ $rc -eq 0 ]; then
        ok "$label"
    else
        warn "$label (ignoré)"
    fi
    return $rc
}

# ── Générer la clé SSH et la déployer sur le routeur (une seule fois) ──────────
setup_ssh_key() {
    step "Clé SSH CyberQuest"

    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"

    # Générer la paire de clés si absente
    if [ ! -f "$KEY_FILE" ]; then
        out "-> Génération de la paire de clés RSA 2048..."
        ssh-keygen -t rsa -b 2048 -m PEM -f "$KEY_FILE" -N "" -q
        chmod 600 "$KEY_FILE"
        ok "Clé générée : $KEY_FILE"
    else
        ok "Clé existante réutilisée : $KEY_FILE"
    fi

    # Vérifier si la clé est déjà sur le routeur
    local test_output
    test_output=$(ssh -o HostKeyAlgorithms=+ssh-rsa \
                      -o PubkeyAcceptedAlgorithms=+ssh-rsa \
                      -o StrictHostKeyChecking=no \
                      -o ConnectTimeout=5 \
                      -o BatchMode=yes \
                      -i "$KEY_FILE" \
                      "root@$ROUTER_IP" "echo OK" 2>&1) && local rc=0 || local rc=$?

    if [ $rc -eq 0 ] && echo "$test_output" | grep -q "OK"; then
        ok "Clé déjà déployée sur le routeur — mot de passe non nécessaire"
        return
    fi

    # Déployer la clé publique — SSH demande le mot de passe UNE SEULE FOIS
    local pub_key
    pub_key=$(cat "${KEY_FILE}.pub")

    echo ""
    echo -e "    ${YELLOW}┌─────────────────────────────────────────────────────┐${RESET}"
    echo -e "    ${YELLOW}│  Entrez le mot de passe root du routeur GL.iNet     │${RESET}"
    echo -e "    ${YELLOW}│  (une seule fois — plus jamais demandé ensuite)     │${RESET}"
    echo -e "    ${YELLOW}└─────────────────────────────────────────────────────┘${RESET}"
    echo ""

    ssh -o HostKeyAlgorithms=+ssh-rsa \
        -o PubkeyAcceptedAlgorithms=+ssh-rsa \
        -o StrictHostKeyChecking=no \
        "root@$ROUTER_IP" \
        "mkdir -p /root/.ssh && chmod 700 /root/.ssh && \
         echo '$pub_key' >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys && \
         mkdir -p /etc/dropbear && \
         echo '$pub_key' >> /etc/dropbear/authorized_keys && chmod 600 /etc/dropbear/authorized_keys && \
         echo DEPLOYED" || fail "Déploiement de la clé échoué"

    ok "Clé publique déployée sur le routeur — plus jamais de mot de passe"
}

# =============================================================================
# ÉTAPES COMMUNES — prérequis + détection IP + SSH
# =============================================================================
common_init() {
    step "Vérification des prérequis"
    command -v ssh      >/dev/null 2>&1 || fail "ssh introuvable (normalement présent sur macOS)"
    command -v ssh-keygen >/dev/null 2>&1 || fail "ssh-keygen introuvable"
    command -v python3  >/dev/null 2>&1 || fail "python3 requis pour la détection d'IP"
    ok "Outils disponibles (ssh, ssh-keygen, python3)"

    step "Détection de l'adresse IP de ce Mac sur le réseau ($ROUTER_IP)"
    FLASK_IP=$(get_flask_ip)
    if [ -z "$FLASK_IP" ]; then
        warn "Impossible de détecter l'IP automatiquement."
        read -rp "    Entrez l'IP de ce Mac manuellement (ex: 192.168.8.100) : " FLASK_IP
    fi
    ok "IP Flask : $FLASK_IP  (port $FLASK_PORT)"
    log "FlaskIP détectée : $FLASK_IP"

    setup_ssh_key

    step "Test de la connexion SSH vers le routeur ($ROUTER_IP)"
    local test_output
    test_output=$(ssh -o HostKeyAlgorithms=+ssh-rsa \
                      -o PubkeyAcceptedAlgorithms=+ssh-rsa \
                      -o StrictHostKeyChecking=no \
                      -o ConnectTimeout=5 \
                      -i "$KEY_FILE" \
                      -o BatchMode=yes \
                      "root@$ROUTER_IP" "echo SSH_OK" 2>&1) && local rc=0 || local rc=$?
    log "SSH test output: $test_output"
    if [ $rc -ne 0 ] || ! echo "$test_output" | grep -q "SSH_OK"; then
        fail "Impossible de se connecter en SSH au routeur. Vérifie : SSH activé dans l'interface GL.iNet (System > Advanced > SSH) ?"
    fi
    ok "Connexion SSH établie"
}

# =============================================================================
# ÉTAPE dnsmasq — UCI (méthode correcte pour OpenWrt GL.iNet)
# =============================================================================
setup_dnsmasq() {
    step "Configuration dnsmasq — tout le DNS → $FLASK_IP"
    out "Effet : google.com, apple.com, etc. résoudront tous vers $FLASK_IP"
    out "        (l'accès à $ROUTER_IP par IP directe n'est PAS affecté)"
    out "Méthode : UCI (OpenWrt ne charge pas /etc/dnsmasq.d/ par défaut)"

    # Supprime l'ancienne entrée si elle existe déjà (idempotent)
    ssh_cmd \
        "uci -q del_list dhcp.@dnsmasq[0].address='/#/$FLASK_IP' 2>/dev/null; \
         uci add_list dhcp.@dnsmasq[0].address='/#/$FLASK_IP' && \
         uci set dhcp.@dnsmasq[0].logqueries='1' && \
         uci set dhcp.@dnsmasq[0].logfacility='/tmp/dnsmasq.log' && \
         uci commit dhcp && \
         /etc/init.d/dnsmasq restart && echo 'dnsmasq UCI configuré'" \
        "UCI dnsmasq : wildcard DNS + log DNS → /tmp/dnsmasq.log"

    # Vérification
    ssh_cmd \
        "uci get dhcp.@dnsmasq[0].address 2>/dev/null || echo '(vérification uci)'" \
        "Vérification UCI address" \
        "true"
}

# =============================================================================
# ÉTAPE DNAT iptables — port 80 + 443 → Flask
# =============================================================================
setup_dnat() {
    step "iptables DNAT — port 80 + 443 → $FLASK_IP:$FLASK_PORT"
    out "Les requêtes HTTP/HTTPS (ports 80 et 443) sont redirigées vers Flask"
    out "Règles idempotentes (vérification avant insertion)"

    for port in 80 443; do
        local rule="iptables -t nat -A PREROUTING -i br-lan ! -s $FLASK_IP -p tcp --dport $port -j DNAT --to-destination $FLASK_IP:$FLASK_PORT"
        local check="iptables -t nat -C PREROUTING -i br-lan ! -s $FLASK_IP -p tcp --dport $port -j DNAT --to-destination $FLASK_IP:$FLASK_PORT 2>/dev/null"
        ssh_cmd "$check || $rule" "DNAT $port → $FLASK_PORT (idempotente)"

        local persist="grep -qF '$FLASK_IP:$FLASK_PORT' /etc/firewall.user 2>/dev/null && grep -qF 'dport $port' /etc/firewall.user 2>/dev/null || echo '$rule' >> /etc/firewall.user"
        ssh_cmd "$persist" "Persistance DNAT $port dans /etc/firewall.user"
    done
}

# =============================================================================
# ÉTAPE FORWARD DROP — active le captive portal (bloque internet)
# =============================================================================
setup_forward_drop() {
    step "iptables FORWARD DROP — captive portal activé"
    out "Les clients WiFi n'ont plus accès à internet."
    out "Flask ($FLASK_IP:$FLASK_PORT) reste joignable."
    out "$ROUTER_IP (admin routeur) reste joignable par IP directe."

    local rule_accept="iptables -I FORWARD 5 -i br-lan -d $FLASK_IP -j ACCEPT"
    local rule_drop="iptables -I FORWARD 6 -i br-lan -j DROP"
    local check_accept="iptables -C FORWARD -i br-lan -d $FLASK_IP -j ACCEPT 2>/dev/null"
    local check_drop="iptables -C FORWARD -i br-lan -j DROP 2>/dev/null"

    ssh_cmd "$check_accept || $rule_accept" "FORWARD ACCEPT br-lan → $FLASK_IP (idempotente)"
    ssh_cmd "$check_drop   || $rule_drop"   "FORWARD DROP br-lan → internet (idempotente)"

    # Persistance
    local persist="grep -qF 'ACCEPT.*$FLASK_IP' /etc/firewall.user 2>/dev/null || echo '$rule_accept' >> /etc/firewall.user ; \
                   grep -qF 'FORWARD.*br-lan.*DROP' /etc/firewall.user 2>/dev/null || echo '$rule_drop' >> /etc/firewall.user"
    ssh_cmd "$persist" "Persistance FORWARD dans /etc/firewall.user"
}

# =============================================================================
# ÉTAPE PASSTHROUGH — supprime le DROP, internet rétabli, DNS log reste actif
# =============================================================================
setup_passthrough() {
    step "iptables FORWARD PASSTHROUGH — internet rétabli"
    out "Suppression du DROP FORWARD et du ACCEPT Flask."
    out "Le DNS log reste actif → les sites visités continuent d'être tracés."
    out "Le DNAT port 80/443 reste actif → Flask reçoit toujours les sondes OS."

    ssh_cmd \
        "iptables -D FORWARD -i br-lan -d $FLASK_IP -j ACCEPT 2>/dev/null || true" \
        "Suppression FORWARD ACCEPT Flask" "true"

    ssh_cmd \
        "iptables -D FORWARD -i br-lan -j DROP 2>/dev/null || true" \
        "Suppression FORWARD DROP internet" "true"

    ssh_cmd \
        "sed -i '/FORWARD.*br-lan/d' /etc/firewall.user && echo 'firewall.user nettoyé'" \
        "Nettoyage persistance FORWARD dans /etc/firewall.user"

    out ""
    out "✅ Internet rétabli pour tous les clients WiFi."
    out "📋 DNS log toujours actif sur le routeur (/tmp/dnsmasq.log)"
}

# =============================================================================
# ÉTAPE TRANSPARENT — nettoie TOUT (accès captive portal réseau mère)
# =============================================================================
setup_transparent() {
    step "MODE TRANSPARENT — nettoyage complet des règles"
    out "Le routeur devient un simple bridge transparent."
    out "L'instructeur pourra accéder au captive portal du réseau mère."
    out ""
    out "⚠️  Toutes les règles CyberQuest seront supprimées :"
    out "   - FORWARD DROP/ACCEPT"
    out "   - DNAT 80/443"
    out "   - Wildcard DNS"
    out ""

    # 1. Supprimer toutes les règles FORWARD personnalisées
    ssh_cmd \
        "iptables -D FORWARD -i br-lan -d $FLASK_IP -j ACCEPT 2>/dev/null || true" \
        "Suppression FORWARD ACCEPT Flask" "true"

    ssh_cmd \
        "iptables -D FORWARD -i br-lan -j DROP 2>/dev/null || true" \
        "Suppression FORWARD DROP internet" "true"

    # 2. Flush toutes les règles DNAT (PREROUTING)
    ssh_cmd \
        "iptables -t nat -F PREROUTING && echo 'PREROUTING flushed'" \
        "Flush complet iptables PREROUTING (DNAT 80/443)" "true"

    # 3. Supprimer le wildcard DNS UCI
    ssh_cmd \
        "uci -q del_list dhcp.@dnsmasq[0].address='/#/$FLASK_IP' 2>/dev/null || true ; \
         uci -q del dhcp.@dnsmasq[0].logqueries 2>/dev/null || true ; \
         uci -q del dhcp.@dnsmasq[0].logfacility 2>/dev/null || true ; \
         uci commit dhcp && \
         /etc/init.d/dnsmasq restart && echo 'dnsmasq UCI nettoyé'" \
        "Suppression wildcard DNS + log"

    # 4. Nettoyer firewall.user (persistance)
    ssh_cmd \
        "> /etc/firewall.user && echo 'firewall.user vidé'" \
        "Nettoyage /etc/firewall.user"

    # 5. Redémarrer le firewall pour appliquer
    ssh_cmd \
        "/etc/init.d/firewall restart && echo 'firewall redémarré'" \
        "Redémarrage firewall OpenWrt"

    out ""
    out "✅ Routeur en mode TRANSPARENT — toutes les règles CyberQuest supprimées"
    out ""
    out "📋 Prochaines étapes :"
    out "   1. Connecte-toi au captive portal de l'école via l'interface web du routeur"
    out "   2. Une fois internet OK → lance : ./setup_router.sh --setup"
}

# =============================================================================
# ÉTAPE vérification finale — état des règles sur le routeur
# =============================================================================
verify() {
    step "Vérification finale — état des règles sur le routeur"

    out "--- dnsmasq UCI ---"
    ssh_cmd "uci get dhcp.@dnsmasq[0].address 2>/dev/null || echo '(absent)'" \
            "UCI address (wildcard DNS)" "true"

    out ""
    out "--- iptables NAT (DNAT) ---"
    ssh_cmd "iptables -t nat -L PREROUTING -n -v --line-numbers" \
            "Règles PREROUTING" "true"

    out ""
    out "--- iptables FORWARD ---"
    ssh_cmd "iptables -L FORWARD -n -v --line-numbers" \
            "Règles FORWARD" "true"

    out ""
    out "--- /etc/firewall.user ---"
    ssh_cmd "cat /etc/firewall.user 2>/dev/null || echo '(vide)'" \
            "Contenu firewall.user" "true"
}

# =============================================================================
# MAIN — routing par mode
# =============================================================================
echo ""
echo -e "${MAGENTA}==========================================${RESET}"
echo -e "${MAGENTA}     CyberQuestKids -- Setup routeur      ${RESET}"
echo -e "${MAGENTA}  Mode : $MODE${RESET}"
echo -e "${MAGENTA}==========================================${RESET}"

{
    echo ""
    echo "============================================"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')  Mode=$MODE"
    echo "============================================"
} >> "$LOG_FILE"

echo -e "    ${GRAY}Log : $LOG_FILE${RESET}"
log "RouterIP=$ROUTER_IP  FlaskPort=$FLASK_PORT  Mode=$MODE"

case "$MODE" in

    --setup)
        common_init
        setup_dnsmasq
        setup_dnat
        setup_forward_drop
        verify

        echo ""
        echo -e "${GREEN}==========================================${RESET}"
        echo -e "${GREEN}  ✅ Setup terminé — Captive portal ACTIF ${RESET}"
        echo -e "${GREEN}------------------------------------------${RESET}"
        echo -e "${GREEN}  Flask     : http://$FLASK_IP:$FLASK_PORT${RESET}"
        echo -e "${GREEN}  Dashboard : http://$FLASK_IP:$FLASK_PORT/dashboard${RESET}"
        echo -e "${GREEN}  Routeur   : http://$ROUTER_IP${RESET}"
        echo -e "${GREEN}------------------------------------------${RESET}"
        echo -e "${GRAY}  Démarrage Flask : sudo ./start_mac.sh${RESET}"
        echo -e "${GRAY}  Passthrough     : ./setup_router.sh --passthrough${RESET}"
        echo -e "${GRAY}  Log             : $LOG_FILE${RESET}"
        echo -e "${GREEN}==========================================${RESET}"
        ;;

    --forward)
        common_init
        setup_forward_drop
        verify

        echo ""
        echo -e "${GREEN}==========================================${RESET}"
        echo -e "${GREEN}  ✅ FORWARD DROP actif — internet coupé  ${RESET}"
        echo -e "${GREEN}------------------------------------------${RESET}"
        echo -e "${GRAY}  Passthrough : ./setup_router.sh --passthrough${RESET}"
        echo -e "${GREEN}==========================================${RESET}"
        ;;

    --passthrough)
        common_init
        setup_passthrough
        verify

        echo ""
        echo -e "${GREEN}==========================================${RESET}"
        echo -e "${GREEN}  ✅ PASSTHROUGH — internet rétabli       ${RESET}"
        echo -e "${GREEN}  📋 DNS log toujours actif               ${RESET}"
        echo -e "${GREEN}------------------------------------------${RESET}"
        echo -e "${GRAY}  Re-activer : ./setup_router.sh --forward${RESET}"
        echo -e "${GREEN}==========================================${RESET}"
        ;;

    --transparent)
        common_init
        setup_transparent
        verify

        echo ""
        echo -e "${GREEN}==========================================${RESET}"
        echo -e "${GREEN}  ✅ MODE TRANSPARENT — bridge pur         ${RESET}"
        echo -e "${GREEN}  🌐 Accès captive portal réseau mère     ${RESET}"
        echo -e "${GREEN}------------------------------------------${RESET}"
        echo -e "${GRAY}  Après connexion : ./setup_router.sh --setup${RESET}"
        echo -e "${GREEN}==========================================${RESET}"
        ;;

    *)
        echo ""
        echo -e "${YELLOW}Usage :${RESET}"
        echo -e "  ${YELLOW}./setup_router.sh                   → setup complet${RESET}"
        echo -e "  ${YELLOW}./setup_router.sh --setup           → setup complet${RESET}"
        echo -e "  ${YELLOW}./setup_router.sh --forward         → active FORWARD DROP (captive portal)${RESET}"
        echo -e "  ${YELLOW}./setup_router.sh --passthrough     → coupe FORWARD DROP (internet rétabli)${RESET}"
        echo -e "  ${YELLOW}./setup_router.sh --transparent     → nettoie TOUT (accès captive portal mère)${RESET}"
        exit 1
        ;;
esac

echo ""
log "=== Terminé — Mode=$MODE FlaskIP=${FLASK_IP:-?} ==="
