# =============================================================================
# CyberQuestKids — Configuration routeur GL.iNet Opal + démarrage Flask
# Usage : double-cliquer setup_router.bat  (ou : powershell -File setup_router.ps1)
# =============================================================================

param(
    [string]$RouterIP  = "192.168.8.1",
    [int]   $FlaskPort = 8080
)

# ── Couleurs ──────────────────────────────────────────────────────────────────
function Write-Step  ($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK    ($msg) { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn  ($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }
function Write-Fail  ($msg) { Write-Host "    [ERREUR] $msg" -ForegroundColor Red }

# ── Détection IP locale sur le réseau du routeur ──────────────────────────────
function Get-FlaskIP {
    $subnet = $RouterIP -replace '\.\d+$', '.'          # "192.168.8."
    $ip = Get-NetIPAddress -AddressFamily IPv4 |
          Where-Object { $_.IPAddress.StartsWith($subnet) -and $_.IPAddress -ne $RouterIP } |
          Select-Object -First 1 -ExpandProperty IPAddress
    return $ip
}

# ── Exécuter une commande SSH sur le routeur ──────────────────────────────────
function Invoke-RouterCmd {
    param([string]$Cmd, [string]$Label)
    Write-Host "    -> $Label" -ForegroundColor DarkGray
    & ssh -o HostKeyAlgorithms=+ssh-rsa `
          -o PubkeyAcceptedKeyTypes=+ssh-rsa `
          -o StrictHostKeyChecking=no `
          "root@$RouterIP" $Cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Échec : $Label"
        Write-Host "    Commande : $Cmd" -ForegroundColor DarkGray
        exit 1
    }
    Write-OK $Label
}

# =============================================================================
# MAIN
# =============================================================================
Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║     CyberQuestKids — Setup routeur       ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Magenta

# ── 0. Vérifier que SSH est dispo ─────────────────────────────────────────────
Write-Step "Vérification des prérequis"
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Fail "ssh introuvable. Active OpenSSH dans Paramètres → Applications → Fonctionnalités facultatives."
    exit 1
}
Write-OK "OpenSSH client disponible"

# ── 1. Détecter l'IP du PC Flask ──────────────────────────────────────────────
Write-Step "Détection de l'adresse IP de ce PC sur le réseau Opal ($RouterIP)"
$FlaskIP = Get-FlaskIP
if (-not $FlaskIP) {
    Write-Warn "Impossible de détecter l'IP automatiquement."
    $FlaskIP = Read-Host "    Entrez l'IP de ce PC manuellement (ex: 192.168.8.100)"
}
Write-OK "IP Flask : $FlaskIP  (port $FlaskPort)"

# ── 2. Tester la connexion SSH ────────────────────────────────────────────────
Write-Step "Test de la connexion SSH vers le routeur ($RouterIP)"
& ssh -o HostKeyAlgorithms=+ssh-rsa `
      -o PubkeyAcceptedKeyTypes=+ssh-rsa `
      -o StrictHostKeyChecking=no `
      -o ConnectTimeout=5 `
      "root@$RouterIP" "echo OK" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Impossible de se connecter en SSH au routeur."
    Write-Warn "Vérifie : SSH activé dans l'interface GL.iNet (System > Advanced > SSH) ?"
    exit 1
}
Write-OK "Connexion SSH établie"

# ── 3. dnsmasq : redirection DNS totale ──────────────────────────────────────
Write-Step "Configuration dnsmasq (DNS → $FlaskIP)"
Invoke-RouterCmd `
    "mkdir -p /etc/dnsmasq.d && echo 'address=/#/$FlaskIP' > /etc/dnsmasq.d/captive.conf" `
    "Écriture /etc/dnsmasq.d/captive.conf"
Invoke-RouterCmd `
    "/etc/init.d/dnsmasq restart" `
    "Redémarrage dnsmasq"

# ── 4. iptables : port 80 → FlaskPort ────────────────────────────────────────
Write-Step "Configuration iptables (port 80 → $FlaskPort)"
$rule  = "iptables -t nat -A PREROUTING -i br-lan ! -s $FlaskIP -p tcp --dport 80 -j DNAT --to-destination ${FlaskIP}:${FlaskPort}"
$check = "iptables -t nat -C PREROUTING -i br-lan ! -s $FlaskIP -p tcp --dport 80 -j DNAT --to-destination ${FlaskIP}:${FlaskPort} 2>/dev/null"
Invoke-RouterCmd `
    "$check || $rule" `
    "Règle DNAT 80 → $FlaskPort (idempotente)"

# Persistance dans /etc/firewall.user
$persist = "grep -qF '${FlaskIP}:${FlaskPort}' /etc/firewall.user 2>/dev/null || echo '$rule' >> /etc/firewall.user"
Invoke-RouterCmd `
    $persist `
    "Persistance dans /etc/firewall.user"

# ── 5. Démarrer le serveur Flask ──────────────────────────────────────────────
Write-Step "Démarrage du serveur Flask"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$batPath   = Join-Path $scriptDir "start_windows.bat"

if (Test-Path $batPath) {
    Write-OK "Lancement de start_windows.bat --start"
    Start-Process "cmd.exe" -ArgumentList "/k `"$batPath`" --start"
} else {
    Write-Warn "start_windows.bat introuvable à : $batPath"
    Write-Warn "Lance le serveur manuellement : cd QR_quest && python server.py"
}

# ── Résumé ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           Setup terminé !                ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  Serveur Flask : http://$FlaskIP`:$FlaskPort" -ForegroundColor Green
Write-Host "║  Routeur admin : http://$RouterIP" -ForegroundColor Green
Write-Host "║  Dashboard     : http://$FlaskIP`:$FlaskPort/dashboard" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
