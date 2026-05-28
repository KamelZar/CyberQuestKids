# CyberQuest QR Quest — Guide de démarrage

> Guide opérationnel pour l'animateur. Architecture technique dans `PROJET.md`.

---

## Matériel requis

| Élément | Rôle |
|---|---|
| Routeur GL.iNet (Mango / SFT1200) | WiFi local + captive portal |
| PC Windows ou MacBook | Serveur Flask (192.168.8.100) |
| Câble USB-C → USB-A (ou WiFi) | Connexion PC → routeur |

---

## Première installation (une seule fois par routeur)

### Windows

```bat
setup_router.bat
```

### Mac

```bash
chmod +x setup_router.sh   # une seule fois
./setup_router.sh
```

Ce que ça fait (Windows + Mac) :
1. Génère la clé SSH dans `.ssh/cyberquest_key`
2. Demande le mot de passe root du routeur **une seule fois**
3. Configure dnsmasq via UCI (DNS wildcard → 192.168.8.100 + log DNS)
4. Configure iptables (DNAT port 80 + 443 → Flask + FORWARD DROP)

> Après ça, le routeur est configuré définitivement. Plus jamais de mot de passe.

---

## Démarrage d'une session (jour-J)

### Windows

```bat
start_windows.bat
```

### Mac

```bash
cd QR_quest
sudo ./start_mac.sh
```

---

## Pendant la session

### Dashboard animateur

```
http://192.168.8.100:8080/dashboard
```

| Bouton | Effet |
|---|---|
| `🌐 INTERNET` | Supprime le FORWARD DROP → internet rétabli pour tous. DNS log reste actif. |
| `🔒 CAPTIVE` | Réactive le FORWARD DROP + vide la whitelist → les participants repassent par NexaPlay |
| `🧹 ÉQUIPES` | Remet les équipes à zéro (événements conservés) |
| `🏆 SCORES` | Remet les scores Champions à zéro |
| `⚠️ RESET TOUT` | Efface tout (équipes + événements + scores) |

### Flow type d'une session

```
1. Démarrer start_windows.bat (ou start_mac.sh en sudo)
2. Participants connectent au WiFi → popup NexaPlay → phishing → gotcha
   └─ Internet débloqué automatiquement par appareil après le gotcha
3. Participants s'inscrivent en équipe → chemin.html → exercices
4. Si YouTube nécessaire → cliquer 🌐 INTERNET sur le dashboard
5. Fin de session → 🔒 CAPTIVE pour le groupe suivant
6. ⚠️ RESET TOUT entre deux groupes
```

### QR Code de secours (Android)

Sur Android, la popup captive ne s'affiche pas toujours automatiquement.
Afficher ce QR code pointant vers `http://192.168.8.100/` :

> *"Scanne ce QR code pour accéder aux activités"*

---

## Commandes routeur (SSH)

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa root@192.168.8.1
```

| Commande | Usage |
|---|---|
| `iptables -L FORWARD -n --line-numbers` | Vérifier les règles actives |
| `tail -f /tmp/dnsmasq.log` | Voir les sites visités en temps réel |
| `/etc/init.d/dnsmasq restart` | Redémarrer le DNS |
| `/etc/init.d/dropbear restart` | Redémarrer SSH |

---

## Fallback Mac (si Windows tombe en panne)

Si tu bascules du Windows au Mac **après** que le routeur est déjà configuré, tu n'as besoin que de la clé SSH :

```bash
# Option A — copier depuis Windows (USB ou réseau)
cp /chemin/vers/QR_quest/.ssh/cyberquest_key QR_quest/.ssh/

# Option B — re-déployer la clé depuis le Mac (setup_router.sh gère tout)
cd QR_quest
./setup_router.sh   # re-génère la clé + demande le mdp routeur 1 fois
```

Puis démarrer Flask :

```bash
sudo ./start_mac.sh
```

> Pas de portproxy nécessaire — Flask écoute sur le port 80 directement avec sudo.

---

## Variables d'environnement

| Variable | Défaut | Usage |
|---|---|---|
| `ROUTER_IP` | `192.168.8.1` | IP du routeur GL.iNet |

```bat
REM Windows
set ROUTER_IP=192.168.8.1 && setup_router.bat
```

```bash
# Mac
ROUTER_IP=192.168.8.1 ./setup_router.sh
```

---

## Fichiers importants

```
QR_quest/
├── server.py              Serveur Flask
├── start_windows.bat      Lancement Windows
├── start_mac.sh           Lancement Mac
├── setup_router.bat       Configuration routeur Windows (une seule fois)
├── setup_router.ps1       Script PowerShell appelé par setup_router.bat
├── setup_router.sh        Configuration routeur Mac (une seule fois)
├── .ssh/                  Clé SSH (gitignorée — ne pas perdre !)
│   ├── cyberquest_key     Clé privée
│   └── cyberquest_key.pub Clé publique
├── events.json            Tracking événements session
├── teams.json             Équipes session en cours
└── setup_router.log       Log du dernier setup
```

> ⚠️ Le dossier `.ssh/` est gitignorié. Garde une copie de `cyberquest_key` en lieu sûr.
