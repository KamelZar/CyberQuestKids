# 🎯 Guide de poche — Animateur CyberQuest
**Référence rapide pour le jour-J**

---

## 🚀 Démarrage rapide

### Sur site AVEC captive portal école/hôtel

```bash
# 1. Mode transparent (nettoie tout)
./setup_router.sh --transparent        # Mac
setup_router.bat --transparent         # Windows

# 2. Connexion captive portal école via http://192.168.8.1

# 3. Une fois internet OK sur le routeur
./setup_router.sh --setup              # Mac
setup_router.bat --setup               # Windows
```

### Sur site SANS captive portal (réseau simple)

```bash
# Windows
setup_router.bat                       # Première fois seulement
start_windows.bat

# Mac
./setup_router.sh                      # Première fois seulement
sudo ./start_mac.sh
```

---

## 📱 Dashboard

```
http://192.168.8.100:8080/dashboard
```

| Bouton | Action |
|--------|--------|
| **▶ START** | Démarre session 20 min + timer |
| **⏹ STOP** | Arrête session (scores bloqués) |
| **🌐 INTERNET** | Donne internet à tous (YouTube) |
| **🔒 CAPTIVE** | Réactive captive portal |
| **🧹 ÉQUIPES** | Reset équipes (garde événements) |
| **🏆 SCORES** | Reset scores Champions |
| **⚠️ RESET TOUT** | Efface tout |

---

## 🔧 Dépannage express

### ❌ Captive portal école ne s'ouvre pas

```bash
cd QR_quest/.ssh
./router_manual_clean.sh               # Nettoyage d'urgence
```

### ❌ Participants n'ont pas internet après INTERNET

```bash
cd QR_quest/.ssh
./router_status.sh                     # Diagnostic
```

Vérifier que le routeur a internet :
```bash
ssh -i .ssh/cyberquest_key root@192.168.8.1 "ping -c 2 8.8.8.8"
```

### ❌ Flask ne répond plus

```bash
# Mac
./start_mac.sh --restart

# Windows
start_windows.bat --restart
```

### ❌ Android : popup captive ne s'affiche pas

Afficher un QR code pointant vers :
```
http://192.168.8.100/
```

---

## 📋 Checklist session

- [ ] ✨ Mode transparent (si captive portal école)
- [ ] 🔌 Connexion captive portal école
- [ ] 🚀 `setup_router` + `start_windows` / `start_mac`
- [ ] 🌐 Dashboard ouvert (192.168.8.100:8080/dashboard)
- [ ] 📺 Poster init ouvert (192.168.8.100:8080/init-poster)
- [ ] ▶ **START** session sur dashboard
- [ ] 👥 Participants se connectent → NexaPlay → équipes
- [ ] 🎮 Activités en cours
- [ ] 🌐 **INTERNET** si besoin YouTube
- [ ] ⏹ **STOP** → Champions à la fin
- [ ] ⚠️ **RESET TOUT** entre deux groupes

---

## 🔑 Commandes SSH utiles

### Connexion

```bash
ssh -i QR_quest/.ssh/cyberquest_key root@192.168.8.1
```

### Diagnostic réseau

```bash
# Internet OK ?
ping -c 2 8.8.8.8

# Règles actives ?
iptables -L FORWARD -n --line-numbers

# DNS log temps réel
tail -f /tmp/dnsmasq.log
```

---

## 🎛️ Les 4 modes

| Mode | Commande | Usage |
|------|----------|-------|
| **✨ TRANSPARENT** | `--transparent` | Accès captive portal mère |
| **🔒 SETUP** | `--setup` | Captive portal CyberQuest |
| **🚫 FORWARD** | `--forward` | Réactive captive (après passthrough) |
| **🌐 PASSTHROUGH** | `--passthrough` | Internet libre + tracking |

---

## 📞 Contacts

- **Support technique** : [ton contact]
- **Doc complète** : `DEMARRAGE.md`
- **Modes routeur** : `MODES_ROUTEUR.md`
- **Routeur transparent** : `ROUTEUR_TRANSPARENT.md`

---

## 💾 Sauvegarde clé SSH

⚠️ Garde une copie de `QR_quest/.ssh/cyberquest_key` sur un drive sécurisé !

Si perdue → relance `./setup_router.sh` (redemande le mot de passe routeur 1×)

