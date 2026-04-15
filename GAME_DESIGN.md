# CyberQuestKids — Tower Defense Game Design Document

## Vue d'ensemble
Jeu de tower defense pédagogique sur la cybersécurité.  
**Message central :** Aucun système n'est infaillible — l'objectif n'est pas de gagner, mais de tenir le plus longtemps possible.

---

## Specs techniques
- **Format :** Single HTML file (CSS + JS embarqués)
- **Plateforme cible :** Mobile-first (touch), compatible desktop
- **Style graphique :** Pixel art
- **Langues :** Français / Néerlandais / Anglais (sélecteur au démarrage)
- **Public :** 10–16 ans
- **Hébergement :** GitHub Pages (projet git existant)

---

## Carte & Disposition
- Grille carrée **13×13**
- **Maison / PC** au centre (bloc 3×3) = base à protéger
- Ennemis arrivent des **4 bords** de la grille
- Placement des défenses par **tap/clic** sur une case vide
- **Au départ** : grille vide — aucune défense, le joueur est exposé de tous côtés

---

## Défenses (plaçables sur la grille)

| Défense | Fonction | Coût | Upgradable |
|---|---|---|---|
| 🧱 **Firewall** | Mur qui bloque physiquement les ennemis | 40🔐 | Oui → niveaux 1→2→3 |
| 🔫 **Antivirus** | Tourelle auto-ciblante | 80🔐 | Oui → +cadence/portée |
| 💾 **Backup** | Passif — sauvegarde l'état actuel. Essentiel contre le ransomware | 120🔐 | Non |
| ⬆️ **Update** | Améliore une défense existante (firewall ou antivirus) | 30🔐 | — |

### 🧱 Progression du Firewall (3 niveaux)
Le firewall n'existe pas au départ — le joueur le construit case par case.
Chaque case de mur a son propre niveau, upgradable indépendamment.

| Niveau | Visuel | HP | Coût total |
|---|---|---|---|
| 1 | Mur fin, 1 rangée de briques, couleur pâle | Faible | 40🔐 |
| 2 | Mur moyen, 2 rangées, orange vif | Moyen | 70🔐 |
| 3 | Mur épais, plein, couleur intense | Élevé | 100🔐 |

**Dilemme stratégique clé :** couvrir plus de surface (murs niv.1 partout) ou renforcer moins de cases (murs niv.3 ciblés) ?
→ *Même tension que dans la vraie sécurité : budget limité, impossible de tout protéger à fond.*

---

## Ressources
- **Points de sécurité** = monnaie du jeu
- Gagnés en **répondant aux quiz** entre les vagues
- Dépensés pour construire, placer ou upgrader des défenses

---

## Système de Quiz (entre chaque vague)
- 1 à 3 questions apparaissent entre les vagues
- Mélange : culture générale + cybersécurité
- Bonne réponse = points bonus
- Mauvaise réponse = points réduits ou aucun bonus
- Les questions deviennent progressivement plus orientées cybersécurité

---

## Types d'ennemis

| Ennemi | Comportement |
|---|---|
| 🦠 **Virus** | Standard, suit le chemin le plus court |
| 💥 **DDoS** | Arrive en grand groupe, lent mais nombreux |
| 🍪 **Cookie** | Lent, se colle aux murs et les ronge progressivement (érosion de vie privée) |
| 🎣 **Phishing** | Se déguise en "Mise à jour" — si non détecté, passe les défenses |
| 👤 **Hacker** | Rapide, cible directement les antivirus |
| 💀 **Ransomware** | Ennemi spécial (voir section dédiée) |
| 🔓 **Zero-day** | Ignore les firewalls — passe à travers les murs |

### Vagues
- Aléatoires en taille et composition (pas uniquement DDoS)
- Intensité croissante avec le temps
- Mélange de types différents

---

## Mécanique Cookies (spéciale)
- Les cookies ne se détruisent pas au contact du mur
- Ils **s'accumulent** sur les murs et les **rongent lentement**
- Si trop de cookies accumulés → **fuite de données** (événement négatif)
- Se nettoient via le choix "Nettoyer les cookies" (voir Moments de choix)

---

## Événements aléatoires (perturbateurs)

| Événement | Effet |
|---|---|
| 📧 **Email corrompu** | Ouvre une brèche dans un firewall aléatoire |
| 🔑 **Mot de passe volé** | Désactive un antivirus temporairement |
| 🎣 **Phishing** | Un ennemi se déguise en mise à jour — inattention = il passe |
| 🦠 **Virus installé** | Une défense se retourne contre le joueur |
| ✅ **Mise à jour dispo** | Bonus : upgrade gratuite d'une défense aléatoire |

---

## Moments de Choix (dilemmes stratégiques)

Apparaissent à des moments clés. Le joueur doit choisir entre deux options avec des trade-offs réels.

### 🍪 Nettoyer les cookies vs Installer un VPN
- **Nettoyer cookies** → supprime l'accumulation actuelle, retire le risque de fuite (curatif)
- **VPN** → chiffre le trafic, ralentit les ennemis de type "interception" (préventif)
- *Leçon : deux protections différentes, aucune n'est universelle*

### 💀 Ransomware (événement majeur)
Toutes les défenses se figent. Les vagues continuent. Trois options :

| Option | Effet immédiat | Effet long terme |
|---|---|---|
| 💸 **Payer la rançon** | Perd 80% des points, défenses restaurées vite | 40% de chance de 2e attaque ransomware |
| 💾 **Restaurer le backup** | Perd les défenses depuis le dernier backup | Pas de surrisque. *Nécessite d'avoir un backup placé !* |
| ⏳ **Résister / Attendre** | Paralysé X secondes, ennemis envahissent librement | Ransomware se dissout, dégâts permanents |

*Message ransomware : "Tu as financé le cybercrime" / "Les backups t'ont sauvé" / "Aucun système n'est infaillible"*

### 🔒 2FA proposé
- **Activer** → ralentit légèrement le joueur pour placer des défenses, mais bloque les attaques "mot de passe volé"
- **Ignorer** → plus rapide maintenant, vulnérable plus tard

### ⚠️ Breach détectée
- **Couper le réseau** → perd des points mais stoppe l'attaque immédiatement
- **Isoler et continuer** → risqué, mais préserve les ressources

### 🔄 Fausse mise à jour
- **Installer maintenant** → peut être du malware (risque)
- **Vérifier la source** → coûte du temps, mais sécurisé

---

## Thème Visuel Dynamique (HP → ambiance)

L'apparence du jeu évolue **en temps réel** selon les HP de la base.
Le joueur ressent instinctivement l'état de son système, sans lire les chiffres.

| HP | Ambiance | Grille | Nature |
|---|---|---|---|
| 100–80% | ☀️ Prairie ensoleillée | Vert clair | Petites fleurs pixel qui se balancent |
| 80–60% | 🌤 Fin d'après-midi | Jaune-vert | Fleurs qui disparaissent, herbe dorée |
| 60–40% | ☁️ Nuages lourds | Gris-vert | Herbe maigre, brins seulement |
| 40–20% | 🌙 Nuit tombante | Bleu-noir | Plus de nature, cyber s'installe |
| 20–0% | 💀 Full cyber-dark | Noir/rouge | Vignette rouge, couleurs d'alerte |

- Les couleurs du HUD, des bordures et du fond s'interpolent progressivement
- La bannière "VAGUE EN APPROCHE" n'apparaît qu'en dessous de 40%
- Le numéro de vague affiché reflète aussi l'intensité (vague 1 → vague 6+)

---

## Fin de partie
- La maison est détruite = Game Over
- Affichage du **temps de survie** + récapitulatif des événements subis
- Message final : *"Aucun système n'est infaillible. La vraie sécurité, c'est être prêt à reconstruire."*
- Partage du score possible

---

## Structure des fichiers
```
index.html          ← jeu complet (HTML + CSS + JS)
mockup.html         ← prototype visuel / démo du thème dynamique
GAME_DESIGN.md      ← ce fichier (source de vérité du design)
```

---

## Notes pédagogiques
- La règle **3-2-1 des backups** est enseignée implicitement via la mécanique backup
- Les cookies : métaphore de l'**érosion lente et silencieuse** de la vie privée
- Le ransomware : reproduit fidèlement le dilemme réel des entreprises victimes
- L'absence de victoire possible = message fort sur la nature de la cybersécurité
- Le thème visuel (prairie → cyber-dark) rend **viscéral** l'état de santé du système
- La progression du firewall (inexistant → niv.3) enseigne que la sécurité se **construit activement**

---

## Historique des décisions de design
- *Session 1 :* Concept de base, mécaniques principales, types d'ennemis, quiz, langues
- *Session 1 :* Ajout mécanique cookies (érosion des murs), choix stratégiques (cookies vs VPN)
- *Session 1 :* Ransomware avec 3 options (payer / backup / résister), défense Backup ajoutée
- *Session 1 :* Firewall absent au départ, progression en 3 niveaux visuels
- *Session 1 :* Thème visuel dynamique HP → prairie ensoleillée (100%) / cyber-dark (0%)
