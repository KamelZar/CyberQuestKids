# CyberQuestKids — Mémoire projet

## Conventions de conversation
- Si un message commence par **`Q:`**, répondre uniquement — aucune modification de code, aucun fichier touché.
- **Après toute création ou modification de fichier dans `QR_quest/`** (page HTML, route Flask, feature), mettre à jour `QR_quest/CYBERQUEST_OVERVIEW.html` en conséquence : checklist (cocher les items faits), bloc routes, flow si impacté. Idem pour ce fichier `CLAUDE.md` (section "Fait ✅" / "À faire ❌").

## Profil développeur
- **Kamel** — développeur Java / Spring Boot + JavaScript / HTML
- Objectif pédagogique : comprendre ce qu'on fait, pas juste copier-coller
- Adapter les explications avec des analogies Spring Boot quand c'est utile

## Architecture du projet
Deux modules distincts :

### 1. Workshop interactif (`html/workshop.html`)
- Hébergé sur GitHub Pages (public)
- Carousel 3D pédagogique, activités cybersécurité
- Système de niveaux Basic / Standard / Advanced (mapping par âge, silencieux)
- Traductions FR / NL / EN via fichiers JSON dans `html/translations/`

### 2. QR Quest (`QR_quest/`)
- Expérience en présentiel, réseau WiFi local (hotspot animateur)
- Serveur Flask local (`server.py`) — sert les pages HTML + API REST légère
- Pas de base de données : `events.json` (tracking) + `teams.json` (équipes session)
- Public cible : 11–15 ans, sessions en journée

### 3. Tower Defense (`Tower.html`)
- Jeu pédagogique single-file HTML + CSS + JS
- Design documenté dans `GAME_DESIGN.md`

## État d'avancement QR Quest (mai 2026)
### Fait ✅
- `server.py` : tracking pixel, API dashboard, reset, routes teams (`/teams/available`, `/teams/register`), route `/avatar/<team_id>` (mapping id → fichier réel), IP dynamique via `get_local_ip()`
- `init.html` : WiFi → leçon cookie → redirect `/team-select` (screen-generate supprimé, détection cookie `cq_team`)
- `team-select.html` : carrousel avatars, polling live, POST register, cookies `cq_team` / `cq_uuid` / `cq_lang`
- `_track.js` : migré vers cookie `cq_team`, URL relative (plus d'IP codée en dur)
- `dashboard.html` : branché sur `teams.json` + `events.json`, équipes visibles dès inscription + section phishing victims (tableau source / email / mdp / banque / école / heure) + chip "🎣 Phishés"
- `start_mac.sh` / `start_windows.bat` : `--start` / `--stop` / `--restart`, ouvre dashboard + poster, tue les process résiduels par port
- Exercices : mirror, phishing, lockpicking (trackés)
- `html/_phishing.js` : module partagé injecté sur Roblox / Instagram / Google / TikTok — interception formulaire, overlay gotcha trilingue, bouton retour flottant, désactivation liens "créer un compte"
- Pages phishing : `phishing/roblox/login.html`, `phishing/instagram/login.html`, `phishing/google/login.html`, `phishing/tiktok/login.html`
- `phishing/login/index.html` : page NexaPlay captive portal — bannière WiFi trilingue, email + mdp, lien "Créer un compte" → signup, overlay gotcha login, overlay "Bravo bon réflexe" sur liens CGU
- `phishing/signup/index.html` : page NexaPlay signup — collecte étendue (prénom, nom, email, mdp, naissance, genre, téléphone, adresse, école, banque), overlay gotcha enrichi, overlay "Bravo bon réflexe" sur liens CGU
- Langue détectée via `navigator.languages` sur login (avant que `cq_lang` existe) → cookie posé pour tout le flow ; signup lit ce cookie en priorité
- `server.py` : `/phishing/catch` (anonymise + stocke victims), `/phishing/terms-click` (stocke "bon réflexe"), `/phishing/login`, `/phishing/signup`, `/captive` → `/phishing/login?portal=1`
- `server.py` : sondes OS captive portal interceptées (`/hotspot-detect.html`, `/generate_204`, `/connecttest.txt`, etc.) → redirect `/captive`
- **Routeur GL.iNet SFT1200 — configuration complète** :
  - dnsmasq wildcard via UCI (`uci add_list dhcp.@dnsmasq[0].address='/#/192.168.8.100'`) + log DNS (`logqueries` + `logfacility`)
  - iptables FORWARD DROP inséré à la position 5 (avant `zone_lan_forward` de fw3) → captive portal fonctionnel sur iOS
  - DNAT port 80 + 443 → 8080 (Android)
  - SSH key auth : `ssh-keygen -t rsa -b 2048`, déployé sur `/root/.ssh/authorized_keys` ET `/etc/dropbear/authorized_keys` — plus jamais de mot de passe
- `server.py` : whitelist IP par appareil — après gotcha, `whitelist_ip(client_ip)` pose 3 règles iptables via SSH : (1) `FORWARD ACCEPT -s <ip>`, (2) `PREROUTING RETURN -s <ip>` (bypass DNAT 80/443), (3) `PREROUTING DNS DNAT -s <ip> → 8.8.8.8:53` (bypass dnsmasq wildcard) ; sondes OS retournent `Success` → popup iOS se ferme
- `server.py` : `_ssh_router()` helper SSH partagé (subprocess + clé RSA, `HostKeyAlgorithms=+ssh-rsa`)
- `server.py` : `/admin/forward` (réactive FORWARD DROP + vide whitelist) et `/admin/passthrough` (supprime FORWARD DROP → internet global)
- `setup_router.ps1` : modes `--setup` / `--forward` / `--passthrough` ; déploiement clé SSH avec mot de passe une seule fois (Dropbear `/etc/dropbear/authorized_keys`) ; UCI dnsmasq ; iptables position 5 ; encodage UTF-8 BOM
- `setup_router.bat` : passe le mode (`%1`) à setup_router.ps1
- `setup_router.sh` : équivalent Mac bash — mêmes modes, même logique, UCI dnsmasq, DNAT 80+443, FORWARD DROP ; IP détectée via python3 socket ; chmod +x requis une seule fois
- `dashboard.html` : boutons 🌐 INTERNET (`passthrough()`) et 🔒 CAPTIVE (`forward()`)
- `DEMARRAGE.md` : guide opérationnel animateur — installation, démarrage session, dashboard, flow, fallback Mac, commandes SSH routeur

## Flow captive portal (mai 2026)
```
WiFi connect → OS probe interceptée → /captive → /phishing/login?portal=1
  ├── Soumet login     → gotcha (email + mdp) → countdown 6s → /init
  ├── Clique CGU       → overlay "Bravo bon réflexe" → countdown 5s → /init
  └── Clique "Créer"   → /phishing/signup?portal=1
        ├── Soumet signup → gotcha enrichi → countdown 6s → /init
        └── Clique CGU    → overlay "Bravo bon réflexe" → countdown 5s → /init
/init → leçon cookie → team-select (cookie cq_lang écrase la détection navigateur si changé)
```

- `chemin.html` : hub de navigation LED 7×7 — 3 templates aléatoires (seedés par `team_id`), bifurcations avec questions `champions/{lang}.json`, pièges phishing (détectés via `events.json`), arche Champions, FR/NL/EN
- `server.py` : route `GET /chemin`

### À faire ❌
- Page Gotcha (OS, navigateur, IP collectés passivement)
- Verrou d'activation workshop depuis le dashboard
- Page de clôture (bilan projeté en fin de session)
