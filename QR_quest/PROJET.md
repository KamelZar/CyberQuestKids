# CyberQuest — Résumé du projet

## Contexte général
Workshop cybersécurité pédagogique pour enfants de **11 à 15 ans**.  
Sessions en journée, potentiellement plusieurs groupes par jour.  
Hébergé sur un réseau WiFi local généré par le PC animateur (MacBook ou Windows, pas encore déterminé).  
Tout doit fonctionner en **FR, NL et EN**.  
Projet Git, workshop HTML hébergé sur GitHub Pages (public).

---

## Architecture technique

### Serveur
- `server.py` — serveur Flask local, écoute sur `0.0.0.0`
- Port 80 si lancé en root/admin, 8080 sinon
- Dossier `html/` pour les pages servies
- `events.json` pour le tracking des équipes

### Réseau
- Le PC animateur crée un hotspot WiFi local
- **Windows** : hotspot natif, IP fixe `192.168.137.1`
- **Mac** : Partage Internet (nécessite adaptateur USB-C → Ethernet si pas de câble)
- IP actuellement codée en dur `192.168.0.45` → **à rendre dynamique**

### Scripts de lancement à créer
- `start_windows.bat` — démarre le hotspot + Flask, détecte l'IP automatiquement
- `start_mac.sh` — idem pour macOS

---

## Captive Portal (point d'entrée du parcours)

### Flux complet

**Étape 1 — Page captive portal** (déclenchée automatiquement à la connexion WiFi)
- Sélection de la langue (FR / NL / EN) → enregistrée pour toute la session
- Faux portail de connexion avec boutons : Google / Apple / Facebook / Instagram
- Peu importe le bouton cliqué → page Gotcha

**Étape 2 — Page Gotcha**
- Affiche ce qui a été collecté passivement (sans capturer de credentials) :
  - OS et version
  - Navigateur
  - Langue de l'appareil
  - Heure de connexion
  - IP locale
- Se termine par : *"Bonne nouvelle, tu es au bon endroit et ici, tu devrais apprendre une ou deux choses au moins :-)"*
- Redirige vers la sélection du nom d'équipe

**Étape 3 — Sélection du nom d'équipe**
- Carrousel avec photo + courte description de chaque figure (dans la langue choisie)
- Swipe gauche/droite pour naviguer (tactile pour mobile + flèches pour desktop)
- Noms déjà pris : **grisés avec cadenas** (visibles mais non sélectionnables)
- Polling toutes les **1 seconde** pour mettre à jour les noms disponibles en live
- Effet de pression : un nom peut disparaître pendant qu'on hésite 😄
- Premier arrivé, premier servi
- Clic pour confirmer

**Étape 4 — Confirmation**
- UUID généré côté serveur
- Cookie posé sur l'appareil
- Équipe enregistrée (UUID ↔ nom d'équipe ↔ langue)
- Redirection vers le parcours (ou page d'attente si workshop pas encore ouvert)

### Mécanique de détection OS (captive portal)
Le serveur doit répondre aux URLs de détection captive portal de chaque OS :
- Apple → `captive.apple.com`
- Android → `connectivitycheck.gstatic.com`
- Windows → `www.msftconnecttest.com`

Le DNS local (dnsmasq) redirige **toutes** les requêtes vers le serveur.

### Rôle pédagogique
- Remplace la page `/init` actuelle
- Sert de **pont entre théorie et pratique**
- Fonctionne avant ET après l'exposé théorique (les "malins" qui scannent avant deviennent des ambassadeurs involontaires)

---

## Noms d'équipes disponibles

| Nom | Type | Description courte |
|-----|------|-------------------|
| Kevin Mitnick | Hacker | Le hacker le plus recherché des années 90 |
| Jonathan James | Hacker | A piraté la NASA à 15 ans |
| Gary McKinnon | Hacker | A infiltré 97 systèmes militaires US depuis son salon |
| Tim Berners-Lee | Pionnier | Inventeur du Web |
| Linus Torvalds | Pionnier | Créateur de Linux |
| Edward Snowden | Militant | A révélé la surveillance de masse de la NSA |
| Grace Hopper | Pionnière | A inventé le premier compilateur, popularisé le terme "bug" |
| Mira Murati | Leader | Ex-CTO d'OpenAI, derrière ChatGPT, DALL-E et Sora |
| Anonymous | Collectif | Collectif hacktiviste, icône de la culture hacker |
| WannaCry | Malware | Ransomware le plus dévastateur de l'histoire |

Photos à fournir par l'animateur (format carré, même résolution).
Pour Anonymous → masque Guy Fawkes. Pour WannaCry → capture d'écran fenêtre rouge.

---

## Gestion des sessions et sécurité anti-triche

### Principe
- À la connexion via le captive portal, un **UUID** est généré pour l'appareil
- Cet UUID est mappé à un **numéro d'équipe** lisible (ex: "Équipe 7") — plus humain pour les enfants
- L'UUID est stocké dans un **cookie** sur l'appareil du participant
- Tout le tracking utilise cet UUID
- La table UUID ↔ équipe est stockée côté serveur (`teams.json` ou similaire)

### Anti-triche
- Toute requête avec un UUID **inconnu ou absent** → page neutre : *"Désolé, il faudra te reconnecter depuis le début et parler aux organisateurs"*
- Pas d'erreur technique révélatrice, pas d'accès partiel
- Le reset du dashboard efface les events **ET** la table UUID ↔ équipe → repart à zéro pour la session suivante

---

## Verrou d'activation des exercices

### Problème
Les exercices ne doivent pas être accessibles avant que la théorie ait été donnée.

### Solution à implémenter
- Bouton dans le **dashboard animateur** : "Ouvrir le workshop"
- Tant que non activé : les routes des exercices retournent une page d'attente
- Une fois activé : tout s'ouvre simultanément pour toutes les équipes
- Avantage : départ synchronisé, tout le monde part en même temps

---

## Dashboard animateur (`html/dashboard.html`) — existant

- Polling `/dashboard/data` toutes les 5 secondes
- Grille des équipes avec statut par exercice (gotcha ✅ / view 👁 / pas commencé ⬜)
- Carte équipe flashe en cyan à chaque nouvel événement
- Badge "COMPLET" quand les 3 exercices sont faits
- Journal live des événements (colonne droite)
- Barre de stats : équipes actives, total événements, gotchas, équipes complètes
- Reset avec confirmation modale
- Support FR / NL / EN
- Détection automatique de la langue du navigateur
- **À ajouter** : bouton "Ouvrir le workshop" + gestion des sessions

---

## Exercices existants

| Exercice     | Fichier              | Fragment | Tracking status |
|-------------|----------------------|----------|-----------------|
| Mirror       | `mirror.html`        | CYB-A3   | `gotcha`        |
| Phishing     | `phishing.html`      | CYB-B7   | `gotcha`        |
| Lockpicking  | (salle physique)     | CYB-C1   | `view`          |

Tracking via pixel GIF invisible (`_track.js`) → route `/cyberquest/<team_id>/<exo>/<status>`

---

## Pages existantes

| Fichier                  | Rôle                                              |
|--------------------------|---------------------------------------------------|
| `poster-init.html`       | Affiche imprimable avec QR codes (WiFi + Init)    |
| `html/dashboard.html`    | Dashboard animateur                               |
| `cyberquest-defense.html`| Mini-jeu défense                                  |
| `cyberquest-invaders.html`| Mini-jeu invaders                                |
| `cyberquest-match.html`  | Mini-jeu match                                    |
| `do-not-press.html`      | Exercice piège                                    |

---

## Sélection du nom d'équipe — détails

- Carrousel avec toutes les images disponibles
- Images stockées dans `QR_quest/images/avatar/`
- Pattern de nommage : `nom_manga.png` (ex: `mitnick_manga.png`)
- Images pas encore en manga : McKinnon, Hopper, Berners-Lee, Torvalds, WannaCry → à remplacer plus tard, même pattern
- Option **"Vous"** : prise de photo via caméra du téléphone (pas d'upload fichier)
  - Photo stockée temporairement côté serveur, liée à l'UUID
  - Supprimée au reset de session
  - Visible sur le dashboard animateur pour identifier les groupes physiquement
- Noms déjà pris : grisés avec cadenas, polling toutes les secondes
- Premier arrivé, premier servi

---

## Page de clôture (fin de session)

Page séparée du dashboard de suivi, conçue pour être **projetée devant tout le groupe** en fin de workshop.

### Inspiration
Black Hat London — affichage public de l'usage réseau des participants à la fin de la conférence. Prouve que personne n'est invisible sur un réseau.

### Contenu à afficher
- Nom/avatar de chaque équipe
- Temps total de connexion
- Pages visitées dans le workshop
- Nombre d'actions réalisées
- Exercices complétés

### Message pédagogique
*"Si on peut faire ça ici dans un cadre sécurisé, imagine ce qu'un vrai attaquant peut faire au Starbucks ou à l'aéroport."*
→ Tu as aussi un rôle à jouer dans la cybersécurité.

### Log réseau enrichi à implémenter dans server.py
- Temps de connexion par équipe (première et dernière requête)
- Pages visitées (routes appelées)
- Nombre d'actions totales par équipe

---

## Priorités de développement

1. **Captive portal** — sélection langue + faux portail (Google/Apple/Facebook/Instagram)
2. **Page Gotcha** — affichage données collectées passivement
3. **Carrousel sélection d'équipe** — avec photos, grisage live, option "Vous"
4. **Verrou d'activation** des exercices depuis le dashboard
5. **Gestion des sessions** — UUID + cookie + table équipes active
6. **Détection dynamique de l'IP** dans `server.py`
7. **Log réseau enrichi** dans `server.py`
8. **Page de clôture** — bilan visuel à projeter
9. **Scripts de lancement** `start_windows.bat` et `start_mac.sh`
10. **DNS local** (dnsmasq) pour redirection captive portal
