# =============================================================================
# CyberQuestKids — Configuration routeur GL.iNet + démarrage Flask
#
# Usage :
#   setup_router.bat                   → --setup   (défaut)
#   setup_router.bat --setup           → setup complet (dnsmasq + DNAT + FORWARD DROP + Flask)
#   setup_router.bat --forward         → active uniquement les règles FORWARD DROP
#   setup_router.bat --passthrough     → supprime le FORWARD DROP (internet rétabli, DNS log actif)
#
# Log : setup_router.log (même dossier, horodaté)
# =============================================================================

param(
    [string]$Mode      = "--setup",
    [string]$RouterIP  = "192.168.8.1",
    [int]   $FlaskPort = 8080
)

# ── Fichier de log + clé SSH ──────────────────────────────────────────────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile   = Join-Path $scriptDir "setup_router.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$SshDir    = Join-Path $scriptDir ".ssh"
$KeyFile   = Join-Path $SshDir "cyberquest_key"

function Write-Log ($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Add-Content -Path $LogFile -Value $line
}

# ── Couleurs + log ────────────────────────────────────────────────────────────
function Write-Step ($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan;    Write-Log "=== $msg" }
function Write-OK   ($msg) { Write-Host "    [OK] $msg" -ForegroundColor Green; Write-Log "    [OK] $msg" }
function Write-Warn ($msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow; Write-Log "    [!]  $msg" }
function Write-Fail ($msg) { Write-Host "    [ERREUR] $msg" -ForegroundColor Red; Write-Log "    [ERREUR] $msg" }
function Write-Out  ($msg) { Write-Host "    $msg" -ForegroundColor DarkGray;  Write-Log "    $msg" }

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
        [switch]$AllowFail
    )
    Write-Out "-> $Label"
    Write-Log "   CMD: $Cmd"

    # Utilise la clé SSH si disponible, sinon auth par mot de passe interactif
    $sshArgs = @(
        '-o', 'HostKeyAlgorithms=+ssh-rsa',
        '-o', 'PubkeyAcceptedKeyTypes=+ssh-rsa',
        '-o', 'StrictHostKeyChecking=no'
    )
    if (Test-Path $KeyFile) {
        $sshArgs += @('-i', $KeyFile, '-o', 'BatchMode=yes')
    }
    $sshArgs += @("root@$RouterIP", $Cmd)

    $output = & ssh @sshArgs 2>&1

    foreach ($line in $output) { Write-Out "   $line" }

    if ($LASTEXITCODE -ne 0 -and -not $AllowFail) {
        Write-Fail "Échec (code $LASTEXITCODE) : $Label"
        exit 1
    }
    if ($LASTEXITCODE -eq 0) { Write-OK $Label } else { Write-Warn "$Label (ignoré)" }
    return $output
}

# ── Générer la clé SSH et la déployer sur le routeur (une seule fois) ──────────
function Invoke-SshKeySetup {
    Write-Step "Clé SSH CyberQuest"

    # Créer le dossier .ssh s'il n'existe pas
    if (-not (Test-Path $SshDir)) {
        New-Item -ItemType Directory -Path $SshDir | Out-Null
    }

    # Générer la paire de clés si absente
    if (-not (Test-Path $KeyFile)) {
        Write-Out "-> Génération de la paire de clés RSA..."
        & ssh-keygen -t rsa -b 2048 -f $KeyFile -N '""' -q
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "ssh-keygen a échoué"
            exit 1
        }
        Write-OK "Clé générée : $KeyFile"
    } else {
        Write-OK "Clé existante réutilisée : $KeyFile"
    }

    # Vérifier si la clé est déjà sur le routeur
    $pubKey = Get-Content "$KeyFile.pub" -Raw
    $pubKey = $pubKey.Trim()

    $testResult = & ssh `
        -o HostKeyAlgorithms=+ssh-rsa `
        -o PubkeyAcceptedKeyTypes=+ssh-rsa `
        -o StrictHostKeyChecking=no `
        -o BatchMode=yes `
        -i $KeyFile `
        "root@$RouterIP" "echo OK" 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-OK "Clé déjà déployée sur le routeur — mot de passe non nécessaire"
        return
    }

    # Déployer la clé publique — SSH demande le mot de passe UNE SEULE FOIS
    Write-Out ""
    Write-Host "    ┌─────────────────────────────────────────────────────┐" -ForegroundColor Yellow
    Write-Host "    │  Entrez le mot de passe root du routeur GL.iNet     │" -ForegroundColor Yellow
    Write-Host "    │  (une seule fois — plus jamais demandé ensuite)     │" -ForegroundColor Yellow
    Write-Host "    └─────────────────────────────────────────────────────┘" -ForegroundColor Yellow
    Write-Out ""

    & ssh `
        -o HostKeyAlgorithms=+ssh-rsa `
        -o PubkeyAcceptedKeyTypes=+ssh-rsa `
        -o StrictHostKeyChecking=no `
        "root@$RouterIP" `
        "mkdir -p /root/.ssh && chmod 700 /root/.ssh && echo '$pubKey' >> /root/.ssh/authorized_keys && sort -u /root/.ssh/authorized_keys -o /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys && echo DEPLOYED"

    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Déploiement de la clé échoué"
        exit 1
    }
    Write-OK "Clé publique déployée sur le routeur — plus jamais de mot de passe"
}

# =============================================================================
# ÉTAPES COMMUNES — prérequis + détection IP + SSH
# =============================================================================
function Invoke-CommonInit {
    Write-Step "Vérification des prérequis"
    if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
        Write-Fail "ssh introuvable. Active OpenSSH dans Paramètres → Applications → Fonctionnalités facultatives."
        exit 1
    }
    if (-not (Get-Command ssh-keygen -ErrorAction SilentlyContinue)) {
        Write-Fail "ssh-keygen introuvable. Active OpenSSH dans Paramètres → Applications → Fonctionnalités facultatives."
        exit 1
    }
    Write-OK "OpenSSH client disponible"

    Write-Step "Détection de l'adresse IP de ce PC sur le réseau ($RouterIP)"
    $script:FlaskIP = Get-FlaskIP
    if (-not $script:FlaskIP) {
        Write-Warn "Impossible de détecter l'IP automatiquement."
        $script:FlaskIP = Read-Host "    Entrez l'IP de ce PC manuellement (ex: 192.168.8.100)"
    }
    Write-OK "IP Flask : $($script:FlaskIP)  (port $FlaskPort)"
    Write-Log "FlaskIP détectée : $($script:FlaskIP)"

    Invoke-SshKeySetup

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
}

# =============================================================================
# ÉTAPE dnsmasq
# =============================================================================
function Invoke-Dnsmasq {
    Write-Step "Configuration dnsmasq — tout le DNS → $($script:FlaskIP)"
    Write-Out "Effet : google.com, apple.com, etc. résoudront tous vers $($script:FlaskIP)"
    Write-Out "        (l'accès à $RouterIP par IP directe n'est PAS affecté)"

    Invoke-RouterCmd `
        "mkdir -p /etc/dnsmasq.d && printf 'address=/#/$($script:FlaskIP)\nlog-queries\nlog-facility=/tmp/dnsmasq.log\n' > /etc/dnsmasq.d/captive.conf && cat /etc/dnsmasq.d/captive.conf" `
        "Écriture /etc/dnsmasq.d/captive.conf (DNS wildcard + query logging)"

    Invoke-RouterCmd `
        "/etc/init.d/dnsmasq restart && echo 'dnsmasq redémarré'" `
        "Redémarrage dnsmasq"

    Invoke-RouterCmd `
        "nslookup google.com 127.0.0.1 2>/dev/null | grep -E 'Address|answer' || echo '(nslookup absent — règle active quand même)'" `
        "Vérification DNS (google.com doit pointer vers $($script:FlaskIP))" `
        -AllowFail
}

# =============================================================================
# ÉTAPE DNAT iptables
# =============================================================================
function Invoke-Dnat {
    Write-Step "iptables DNAT — port 80 → $($script:FlaskIP):${FlaskPort}"
    Write-Out "Les requêtes HTTP (port 80) sont redirigées vers Flask"

    $ruleDnat  = "iptables -t nat -A PREROUTING -i br-lan ! -s $($script:FlaskIP) -p tcp --dport 80 -j DNAT --to-destination $($script:FlaskIP):${FlaskPort}"
    $checkDnat = "iptables -t nat -C PREROUTING -i br-lan ! -s $($script:FlaskIP) -p tcp --dport 80 -j DNAT --to-destination $($script:FlaskIP):${FlaskPort} 2>/dev/null"

    Invoke-RouterCmd "$checkDnat || $ruleDnat" "Règle DNAT 80 → $FlaskPort (idempotente)"

    $persistDnat = "grep -qF '$($script:FlaskIP):${FlaskPort}' /etc/firewall.user 2>/dev/null || echo '$ruleDnat' >> /etc/firewall.user"
    Invoke-RouterCmd $persistDnat "Persistance DNAT dans /etc/firewall.user"
}

# =============================================================================
# ÉTAPE FORWARD DROP — active le captive portal (bloque internet)
# =============================================================================
function Invoke-ForwardDrop {
    Write-Step "iptables FORWARD DROP — captive portal activé"
    Write-Out "Les clients WiFi n'ont plus accès à internet."
    Write-Out "Flask ($($script:FlaskIP):$FlaskPort) reste joignable."
    Write-Out "$RouterIP (admin routeur) reste joignable par IP directe."

    $ruleAccept  = "iptables -I FORWARD -i br-lan -d $($script:FlaskIP) -j ACCEPT"
    $ruleDrop    = "iptables -A FORWARD -i br-lan -j DROP"
    $checkAccept = "iptables -C FORWARD -i br-lan -d $($script:FlaskIP) -j ACCEPT 2>/dev/null"
    $checkDrop   = "iptables -C FORWARD -i br-lan -j DROP 2>/dev/null"

    Invoke-RouterCmd "$checkAccept || $ruleAccept" "FORWARD ACCEPT br-lan → $($script:FlaskIP) (idempotente)"
    Invoke-RouterCmd "$checkDrop   || $ruleDrop"   "FORWARD DROP br-lan → internet (idempotente)"

    $persistFwd = "grep -qF 'FORWARD.*$($script:FlaskIP).*ACCEPT' /etc/firewall.user 2>/dev/null || echo '$ruleAccept' >> /etc/firewall.user ; grep -qF 'FORWARD.*br-lan.*DROP' /etc/firewall.user 2>/dev/null || echo '$ruleDrop' >> /etc/firewall.user"
    Invoke-RouterCmd $persistFwd "Persistance FORWARD dans /etc/firewall.user"
}

# =============================================================================
# ÉTAPE PASSTHROUGH — supprime le DROP, internet rétabli, DNS log reste actif
# =============================================================================
function Invoke-Passthrough {
    Write-Step "iptables FORWARD PASSTHROUGH — internet rétabli"
    Write-Out "Suppression du DROP FORWARD et du ACCEPT Flask."
    Write-Out "Le DNS log reste actif → les sites visités continuent d'être tracés."
    Write-Out "Le DNAT port 80 reste actif → Flask reçoit toujours les sondes OS."

    # Supprimer les règles FORWARD (on ignore les erreurs si elles n'existent pas)
    Invoke-RouterCmd `
        "iptables -D FORWARD -i br-lan -d $($script:FlaskIP) -j ACCEPT 2>/dev/null || true" `
        "Suppression FORWARD ACCEPT Flask" -AllowFail

    Invoke-RouterCmd `
        "iptables -D FORWARD -i br-lan -j DROP 2>/dev/null || true" `
        "Suppression FORWARD DROP internet" -AllowFail

    # Nettoyer firewall.user pour que le reboot ne les réactive pas
    Invoke-RouterCmd `
        "sed -i '/FORWARD.*br-lan/d' /etc/firewall.user && echo 'firewall.user nettoyé'" `
        "Nettoyage persistance FORWARD dans /etc/firewall.user"

    Write-Out ""
    Write-Out "✅ Internet rétabli pour tous les clients WiFi."
    Write-Out "📋 DNS log toujours actif sur le routeur (/tmp/dnsmasq.log)"
}

# =============================================================================
# ÉTAPE port proxy Windows
# =============================================================================
function Invoke-PortProxy {
    Write-Step "Configuration port proxy Windows (80 → $FlaskPort)"

    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Warn "Droits administrateur requis pour le port proxy."
        Write-Warn "Relance setup_router.bat en faisant clic droit → Exécuter en tant qu'administrateur."
        Write-Warn "La config routeur est OK — seul le proxy port 80 a été ignoré."
        return
    }

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

# =============================================================================
# ÉTAPE vérification finale
# =============================================================================
function Invoke-Verify {
    Write-Step "Vérification finale — état des règles sur le routeur"

    Write-Out "--- dnsmasq ---"
    Invoke-RouterCmd "cat /etc/dnsmasq.d/captive.conf" "Contenu captive.conf" -AllowFail

    Write-Out ""
    Write-Out "--- iptables NAT (DNAT) ---"
    Invoke-RouterCmd "iptables -t nat -L PREROUTING -n -v --line-numbers" "Règles PREROUTING" -AllowFail

    Write-Out ""
    Write-Out "--- iptables FORWARD ---"
    Invoke-RouterCmd "iptables -L FORWARD -n -v --line-numbers" "Règles FORWARD" -AllowFail

    Write-Out ""
    Write-Out "--- /etc/firewall.user ---"
    Invoke-RouterCmd "cat /etc/firewall.user" "Contenu firewall.user" -AllowFail
}

# =============================================================================
# MAIN — routing par mode
# =============================================================================
Write-Host ""
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host "     CyberQuestKids -- Setup routeur      " -ForegroundColor Magenta
Write-Host "  Mode : $Mode" -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Magenta

Add-Content -Path $LogFile -Value ""
Add-Content -Path $LogFile -Value "============================================"
Add-Content -Path $LogFile -Value "  $timestamp  Mode=$Mode"
Add-Content -Path $LogFile -Value "============================================"
Write-Host "    Log : $LogFile" -ForegroundColor DarkGray
Write-Log "RouterIP=$RouterIP  FlaskPort=$FlaskPort  Mode=$Mode"

switch ($Mode) {

    "--setup" {
        # Setup complet : tout configurer + démarrer Flask
        Invoke-CommonInit
        Invoke-Dnsmasq
        Invoke-Dnat
        Invoke-ForwardDrop
        Invoke-PortProxy

        Write-Step "Démarrage du serveur Flask"
        $batPath = Join-Path $scriptDir "start_windows.bat"
        if (Test-Path $batPath) {
            Write-OK "Lancement de start_windows.bat --start"
            Start-Process "cmd.exe" -ArgumentList "/k `"$batPath`" --start"
        } else {
            Write-Warn "start_windows.bat introuvable — lance le serveur manuellement"
        }

        Invoke-Verify

        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Green
        Write-Host "  ✅ Setup terminé — Captive portal ACTIF " -ForegroundColor Green
        Write-Host "------------------------------------------" -ForegroundColor Green
        Write-Host "  Flask     : http://$($script:FlaskIP)`:$FlaskPort" -ForegroundColor Green
        Write-Host "  Dashboard : http://$($script:FlaskIP)`:$FlaskPort/dashboard" -ForegroundColor Green
        Write-Host "  Routeur   : http://$RouterIP" -ForegroundColor Green
        Write-Host "------------------------------------------" -ForegroundColor Green
        Write-Host "  Passthrough : setup_router.bat --passthrough" -ForegroundColor DarkGray
        Write-Host "  Log         : $LogFile" -ForegroundColor DarkGray
        Write-Host "==========================================" -ForegroundColor Green
    }

    "--forward" {
        # Réactive uniquement les règles FORWARD DROP (ex: après reboot routeur)
        Invoke-CommonInit
        Invoke-ForwardDrop
        Invoke-Verify

        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Green
        Write-Host "  ✅ FORWARD DROP actif — internet coupé  " -ForegroundColor Green
        Write-Host "------------------------------------------" -ForegroundColor Green
        Write-Host "  Passthrough : setup_router.bat --passthrough" -ForegroundColor DarkGray
        Write-Host "==========================================" -ForegroundColor Green
    }

    "--passthrough" {
        # Rétablit internet — DNS log toujours actif
        Invoke-CommonInit
        Invoke-Passthrough
        Invoke-Verify

        Write-Host ""
        Write-Host "==========================================" -ForegroundColor Green
        Write-Host "  ✅ PASSTHROUGH — internet rétabli       " -ForegroundColor Green
        Write-Host "  📋 DNS log toujours actif               " -ForegroundColor Green
        Write-Host "------------------------------------------" -ForegroundColor Green
        Write-Host "  Re-activer : setup_router.bat --forward" -ForegroundColor DarkGray
        Write-Host "==========================================" -ForegroundColor Green
    }

    default {
        Write-Host ""
        Write-Host "Usage :" -ForegroundColor Yellow
        Write-Host "  setup_router.bat                → setup complet" -ForegroundColor Yellow
        Write-Host "  setup_router.bat --setup        → setup complet" -ForegroundColor Yellow
        Write-Host "  setup_router.bat --forward      → active FORWARD DROP (captive portal)" -ForegroundColor Yellow
        Write-Host "  setup_router.bat --passthrough  → coupe FORWARD DROP (internet rétabli)" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Log "=== Terminé — Mode=$Mode FlaskIP=$($script:FlaskIP) ==="
