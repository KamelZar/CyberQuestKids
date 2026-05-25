# =============================================================================
# CyberQuestKids — Configuration routeur GL.iNet + démarrage Flask
# Usage : double-cliquer setup_router.bat  (ou : powershell -File setup_router.ps1)
# Log   : setup_router.log (même dossier, horodaté)
# =============================================================================

param(
    [string]$RouterIP  = "192.168.8.1",
    [int]   $FlaskPort = 8080
)

# ── Fichier de log ────────────────────────────────────────────────────────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile   = Join-Path $scriptDir "setup_router.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Write-Log ($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Add-Content -Path $LogFile -Value $line
}

# ── Couleurs + log ────────────────────────────────────────────────────────────
function Write-Step ($msg) {
    Write-Host "`n>>> $msg" -ForegroundColor Cyan
    Write-Log "=== $msg"
}
function Write-OK   ($msg) {
    Write-Host "    [OK] $msg" -ForegroundColor Green
    Write-Log "    [OK] $msg"
}
function Write-Warn ($msg) {
    Write-Host "    [!]  $msg" -ForegroundColor Yellow
    Write-Log "    [!]  $msg"
}
function Write-Fail ($msg) {
    Write-Host "    [ERREUR] $msg" -ForegroundColor Red
    Write-Log "    [ERREUR] $msg"
}
function Write-Out  ($msg) {
    Write-Host "    $msg" -ForegroundColor DarkGray
    Write-Log "    $msg"
}

# ── Détection IP locale sur le réseau du routeur ──────────────────────────────
function Get-FlaskIP {
    $subnet = $RouterIP -replace '\.\d+$', '.'
    $ip = Get-NetIPAddress -AddressFamily IPv4 |
          Where-Object { $_.IPAddress.StartsWith($subnet) -and $_.IPAddress -ne $RouterIP } |
          Select-Object -First 1 -ExpandProperty IPAddress
    return $ip
}

# ── Exécuter une commande SSH + logger la sortie ──────────────────────────────
function Invoke-RouterCmd {
    param(
        [string]$Cmd,
        [string]$Label,
        [switch]$AllowFail   # ne pas quitter en cas d'erreur (ex: vérifications)
    )
    Write-Out "-> $Label"
    Write-Log "   CMD: $Cmd"

    $output = & ssh -o HostKeyAlgorithms=+ssh-rsa `
                    -o PubkeyAcceptedKeyTypes=+ssh-rsa `
                    -o StrictHostKeyChecking=no `
                    "root@$RouterIP" $Cmd 2>&1

    foreach ($line in $output) {
        Write-Out "   $line"
    }

    if ($LASTEXITCODE -ne 0 -and -not $AllowFail) {
        Write-Fail "Échec (code $LASTEXITCODE) : $Label"
        exit 1
    }
    if ($LASTEXITCODE -eq 0) {
        Write-OK $Label
    } else {
        Write-Warn "$Label (ignoré)"
    }
    return $output
}

# =============================================================================
# MAIN
# =============================================================================
Write-Host ""
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host "     CyberQuestKids -- Setup routeur      " -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Magenta

Add-Content -Path $LogFile -Value ""
Add-Content -Path $LogFile -Value "============================================"
Add-Content -Path $LogFile -Value "  Setup routeur — $timestamp"
Add-Content -Path $LogFile -Value "============================================"

Write-Host "    Log : $LogFile" -ForegroundColor DarkGray
Write-Log "RouterIP=$RouterIP  FlaskPort=$FlaskPort"

# ── 0. Vérifier que SSH est dispo ─────────────────────────────────────────────
Write-Step "Vérification des prérequis"
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Fail "ssh introuvable. Active OpenSSH dans Paramètres → Applications → Fonctionnalités facultatives."
    exit 1
}
Write-OK "OpenSSH client disponible"

# ── 1. Détecter l'IP du PC Flask ──────────────────────────────────────────────
Write-Step "Détection de l'adresse IP de ce PC sur le réseau ($RouterIP)"
$FlaskIP = Get-FlaskIP
if (-not $FlaskIP) {
    Write-Warn "Impossible de détecter l'IP automatiquement."
    $FlaskIP = Read-Host "    Entrez l'IP de ce PC manuellement (ex: 192.168.8.100)"
}
Write-OK "IP Flask : $FlaskIP  (port $FlaskPort)"
Write-Log "FlaskIP détectée : $FlaskIP"

# ── 2. Tester la connexion SSH ────────────────────────────────────────────────
Write-Step "Test de la connexion SSH vers le routeur ($RouterIP)"
$sshTest = & ssh -o HostKeyAlgorithms=+ssh-rsa `
                 -o PubkeyAcceptedKeyTypes=+ssh-rsa `
                 -o StrictHostKeyChecking=no `
                 -o ConnectTimeout=5 `
                 "root@$RouterIP" "echo SSH_OK" 2>&1
Write-Log "SSH test output: $sshTest"
if ($LASTEXITCODE -ne 0 -or $sshTest -notmatch "SSH_OK") {
    Write-Fail "Impossible de se connecter en SSH au routeur."
    Write-Warn "Vérifie : SSH activé dans l'interface GL.iNet (System > Advanced > SSH) ?"
    exit 1
}
Write-OK "Connexion SSH établie"

# ── 3. dnsmasq : redirection DNS totale ──────────────────────────────────────
Write-Step "Configuration dnsmasq — tout le DNS → $FlaskIP"
Write-Out "Effet : google.com, apple.com, etc. résoudront tous vers $FlaskIP"
Write-Out "        (l'accès à $RouterIP par IP directe n'est PAS affecté)"

Invoke-RouterCmd `
    "mkdir -p /etc/dnsmasq.d && echo 'address=/#/$FlaskIP' > /etc/dnsmasq.d/captive.conf && cat /etc/dnsmasq.d/captive.conf" `
    "Écriture /etc/dnsmasq.d/captive.conf"

Invoke-RouterCmd `
    "/etc/init.d/dnsmasq restart && echo 'dnsmasq redémarré'" `
    "Redémarrage dnsmasq"

# Vérification : dig ou nslookup vers le routeur
Invoke-RouterCmd `
    "nslookup google.com 127.0.0.1 2>/dev/null | grep -E 'Address|answer' || echo '(nslookup absent — rule active quand même)'" `
    "Vérification DNS (google.com doit pointer vers $FlaskIP)" `
    -AllowFail

# ── 4. iptables : DNAT port 80 → FlaskPort ────────────────────────────────────
Write-Step "iptables DNAT — port 80 → ${FlaskIP}:${FlaskPort}"
Write-Out "Les requêtes HTTP (port 80) arrivant sur le routeur sont redirigées vers Flask"

$ruleDnat    = "iptables -t nat -A PREROUTING -i br-lan ! -s $FlaskIP -p tcp --dport 80 -j DNAT --to-destination ${FlaskIP}:${FlaskPort}"
$checkDnat   = "iptables -t nat -C PREROUTING -i br-lan ! -s $FlaskIP -p tcp --dport 80 -j DNAT --to-destination ${FlaskIP}:${FlaskPort} 2>/dev/null"

Invoke-RouterCmd `
    "$checkDnat || $ruleDnat" `
    "Règle DNAT 80 → $FlaskPort (idempotente)"

# Persistance
$persistDnat = "grep -qF '${FlaskIP}:${FlaskPort}' /etc/firewall.user 2>/dev/null || echo '$ruleDnat' >> /etc/firewall.user"
Invoke-RouterCmd `
    $persistDnat `
    "Persistance DNAT dans /etc/firewall.user"

# ── 5. iptables : FORWARD — bloquer internet pour les clients WiFi ────────────
Write-Step "iptables FORWARD — couper internet WiFi (captive portal)"
Write-Out "Sans cette étape, les téléphones détectent qu'ils ont internet"
Write-Out "et n'affichent pas la popup captive portal automatiquement."
Write-Out "IMPORTANT : $RouterIP (admin routeur) reste joignable par IP directe"
Write-Out "           (le trafic vers le routeur lui-même emprunte INPUT, pas FORWARD)"

$ruleAccept  = "iptables -I FORWARD -i br-lan -d $FlaskIP -j ACCEPT"
$ruleDrop    = "iptables -A FORWARD -i br-lan -j DROP"
$checkAccept = "iptables -C FORWARD -i br-lan -d $FlaskIP -j ACCEPT 2>/dev/null"
$checkDrop   = "iptables -C FORWARD -i br-lan -j DROP 2>/dev/null"

Invoke-RouterCmd `
    "$checkAccept || $ruleAccept" `
    "FORWARD ACCEPT br-lan → $FlaskIP (idempotente)"

Invoke-RouterCmd `
    "$checkDrop || $ruleDrop" `
    "FORWARD DROP br-lan → internet (idempotente)"

# Persistance des règles FORWARD
$persistFwd = @"
grep -qF 'FORWARD.*$FlaskIP.*ACCEPT' /etc/firewall.user 2>/dev/null || echo '$ruleAccept' >> /etc/firewall.user
grep -qF 'FORWARD.*br-lan.*DROP' /etc/firewall.user 2>/dev/null || echo '$ruleDrop' >> /etc/firewall.user
"@
Invoke-RouterCmd `
    $persistFwd `
    "Persistance FORWARD dans /etc/firewall.user"

# ── 6. Port proxy Windows : 80 → FlaskPort ───────────────────────────────────
Write-Step "Configuration port proxy Windows (80 → $FlaskPort)"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warn "Droits administrateur requis pour le port proxy."
    Write-Warn "Relance setup_router.bat en faisant clic droit → Exécuter en tant qu'administrateur."
    Write-Warn "La config routeur est OK — seul le proxy port 80 a été ignoré."
} else {
    netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0 2>$null | Out-Null
    netsh interface portproxy add v4tov4 `
        listenport=80 listenaddress=0.0.0.0 `
        connectport=$FlaskPort connectaddress=127.0.0.1
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Echec netsh portproxy"
        Write-Log "[ERREUR] netsh portproxy add a échoué"
    } else {
        Write-OK "Port proxy 80 → $FlaskPort actif"
    }

    netsh advfirewall firewall delete rule name="CyberQuest-port80" 2>$null | Out-Null
    netsh advfirewall firewall add rule `
        name="CyberQuest-port80" protocol=TCP dir=in localport=80 action=allow | Out-Null
    Write-OK "Règle firewall Windows port 80 ajoutée"
}

# ── 7. Démarrer le serveur Flask ──────────────────────────────────────────────
Write-Step "Démarrage du serveur Flask"
$batPath = Join-Path $scriptDir "start_windows.bat"

if (Test-Path $batPath) {
    Write-OK "Lancement de start_windows.bat --start"
    Start-Process "cmd.exe" -ArgumentList "/k `"$batPath`" --start"
} else {
    Write-Warn "start_windows.bat introuvable à : $batPath"
    Write-Warn "Lance le serveur manuellement : cd QR_quest && python server.py"
}

# ── 8. Vérification finale des règles actives sur le routeur ─────────────────
Write-Step "Vérification finale — état des règles sur le routeur"

Write-Out ""
Write-Out "--- dnsmasq ---"
Invoke-RouterCmd `
    "cat /etc/dnsmasq.d/captive.conf" `
    "Contenu captive.conf" `
    -AllowFail

Write-Out ""
Write-Out "--- iptables NAT (DNAT) ---"
Invoke-RouterCmd `
    "iptables -t nat -L PREROUTING -n -v --line-numbers" `
    "Règles PREROUTING" `
    -AllowFail

Write-Out ""
Write-Out "--- iptables FORWARD ---"
Invoke-RouterCmd `
    "iptables -L FORWARD -n -v --line-numbers" `
    "Règles FORWARD" `
    -AllowFail

Write-Out ""
Write-Out "--- /etc/firewall.user (persistance) ---"
Invoke-RouterCmd `
    "cat /etc/firewall.user" `
    "Contenu firewall.user" `
    -AllowFail

# ── Résumé ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "           Setup terminé !                " -ForegroundColor Green
Write-Host "------------------------------------------" -ForegroundColor Green
Write-Host "  Serveur Flask : http://$FlaskIP`:$FlaskPort" -ForegroundColor Green
Write-Host "  Routeur admin : http://$RouterIP" -ForegroundColor Green
Write-Host "  Dashboard     : http://$FlaskIP`:$FlaskPort/dashboard" -ForegroundColor Green
Write-Host "------------------------------------------" -ForegroundColor Green
Write-Host "  Log complet   : $LogFile" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

Write-Log "=== Setup terminé — FlaskIP=$FlaskIP FlaskPort=$FlaskPort ==="
