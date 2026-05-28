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
- `html/_phishing.js` : module partagé injecté sur Google — interception formulaire, overlay gotcha trilingue, bouton retour flottant, désactivation liens "créer un compte"
- Pages phishing : `phishing/google/login.html` (Roblox, Instagram, TikTok supprimés — pages non crédibles)
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
  ├── Soumet login     → gotcha (email + mdp) → countdown 6s → /gotcha
  ├── Clique CGU       → overlay "Bravo bon réflexe" → countdown 5s → /gotcha
  └── Clique "Créer"   → /phishing/signup?portal=1
        ├── Soumet signup → gotcha enrichi → countdown 6s → /gotcha
        └── Clique CGU    → overlay "Bravo bon réflexe" → countdown 5s → /gotcha
/gotcha → révèle infos navigateur → "Suivant" → /init
/init → leçon cookie → (vidéo) → /pret
/pret → théorie GDPR → "Je suis prêt(e)" → /attente
/attente → page d'attente (scan QR codes)
```

- `chemin.html` : hub de navigation LED 7×7 — 3 templates aléatoires (seedés par `team_id`), bifurcations avec questions `champions/{lang}.json`, pièges phishing (détectés via `events.json`), arche Champions, FR/NL/EN
- `server.py` : route `GET /chemin`

- `gotcha.html` + route `/gotcha` : page post-captive portal — révèle passivement IP (server), OS, navigateur, écran, timezone, langues, batterie, réseau, RAM, CPU, touch, dark mode, DNT, cookies, GPU — 20 cards animées + bouton "Suivant" → `/init`
- `server.py` : routes `/gotcha` + `/api/my-info` (retourne IP client)
- `phishing/login/index.html` + `phishing/signup/index.html` : redirects countdown → `/gotcha` au lieu de `/init`
- `pret.html` + route `/pret` : écran théorie GDPR — affiché après vidéo / sélection d'équipe — FR/NL/EN, animation téléphone, bouton "Je suis prêt(e)" → `/attente`
- `attente.html` + route `/attente` : page d'attente sans redirect — badge équipe, animation dots, FR/NL/EN — les participants patientent avant de scanner les QR codes
- `server.py` : session workshop in-memory (`_workshop_session`, `_session_lock`) — `POST /session/start`, `POST /session/stop` (arrêt manuel + flag `stopped`), `GET /session/state` ; timer 20 min, scoring bloqué après expiration ou arrêt manuel
- `dashboard.html` : bouton ⏹ STOP → CHAMPIONS (visible pendant session active) — appelle `/session/stop`, cache le STOP, passe START en "TERMINÉ"
- `missions.html` : overlay Champions (⚡ Direction Champions !) affiché quand session stoppée ou expirée — FR/NL/EN, lien direct `/champions`
- `server.py` : `POST /workshop/score` — point central de scoring, ajoute `workshop_score` dans `teams.json`, vérifie session active, log dans `events.json`
- `server.py` : routes activités — `GET /activity/videos` (`html/video.html`), `/activity/videos/list` (filtré par lang), `POST /activity/videos/watch` + `/score` (time-gate 90%), `GET /activity/cyberquest-match|defense|do-not-press`, `GET /activity/page` (translations/{cq_lang}/page.html)
- `html/video.html` : page activité vidéos — cards par topic, countdown visuel 90% durée, bouton scorer, anti-double-score, FR/NL/EN ; vidéo normale = 50 pts, bonus = 100 pts
- `cyberquest-match.html` : `_submitWorkshopScore()` injecté dans `showEnd()` — envoie le score du jeu (0–200 pts) vers `/workshop/score`
- `cyberquest-defense.html` : `_submitWorkshopScore()` injecté dans `showEndScreen()` — envoie `hp × 2` pts (max 200)
- `do-not-press.html` : `_submitWorkshopScore()` injecté dans `showVictory()` — 150 pts + bonus vitesse (max +50 si < 60s)
- `dashboard.html` : bouton ▶ START (`sessionStart()`), barre timer 20 min avec couleur (vert/orange/rouge), colonne 🏆 Score workshop dans la grille équipes

- `missions.html` + route `GET /missions` : carnet de missions — liste personnalisée Agent + nom équipe, barrage animé des missions complétées, timer session, score live, FR/NL/EN
- `server.py` : `GET /missions/status` — retourne `{done, workshop_score, session}` pour une équipe (polling 4s)

### À faire ❌
- Page de clôture (bilan projeté en fin de session)
- Page d'accueil activités pour les participants (liste des activités disponibles) (`/workshop`)
- Scoring `page.html` (fake website) — à définir
