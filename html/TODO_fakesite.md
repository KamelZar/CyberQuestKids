# 🎮 TODO - Gamification du Faux Site (page.html)

## 📋 Objectif
Transformer le faux site de vente en jeu éducatif interactif avec 3 niveaux de difficulté : Basic / Standard / Advanced

---

## 🎯 Points clés par niveau

### 🟢 BASIC (8 ans, débutants)
**Format :** QCM après exploration libre
**Durée :** ~3-5 minutes
**Mécanique :**
- Laisser l'utilisateur explorer le site librement
- Après 1 minute OU clic sur bouton "Quitter/Continuer"
- Pop-up avec question : "Que penses-tu de ce site ?"
- Choix multiples (sélection multiple activée)
- Score + feedback éducatif simple

**Choix du QCM :**
- [ ] "Ça a l'air génial" ❌ (piège)
- [x] "C'est ridicule" ✅
- [x] "Il n'utilise pas HTTPS" ✅
- [x] "Les prix sont suspects" ✅
- [x] "Cela ressemble à une arnaque" ✅
- [x] "Les avis ont l'air faux" ✅
- [x] "Le timer est louche" ✅

**Score :**
- Bonne réponse = +1 point
- Mauvaise réponse = -1 point
- Non sélectionné = 0 point

---

### 🟡 STANDARD (Intermédiaire)
**Format :** Chasse aux indices guidée
**Durée :** ~5-10 minutes
**Mécanique :**
- Sidebar/Header avec liste de missions
- L'utilisateur doit cliquer sur les éléments suspects
- Chaque clic validé → ✅ + explication
- Clic invalide → ❌ (pas de pénalité majeure)
- Boutons d'achat désactivés pendant le jeu
- Score final avec détails

**Liste des indices à trouver (7 missions) :**
1. 🔒 "Trouve le faux badge SSL"
2. 💰 "Repère un prix impossible (réduction > 80%)"
3. ⭐ "Identifie un faux avis client"
4. 📞 "Trouve l'info de contact suspecte"
5. ⏰ "Détecte l'urgence artificielle"
6. 🏢 "Repère les infos légales manquantes"
7. 📦 "Trouve l'expédition suspecte"

**Score :**
- 7/7 = Expert 🏆
- 5-6/7 = Bon détective 👍
- 3-4/7 = À améliorer 🤔
- 0-2/7 = Attention danger ⚠️

---

### 🔴 ADVANCED (Expert)
**Format :** Mode libre avec piège actif
**Durée :** ~10-15 minutes
**Mécanique :**
- AUCUN indice fourni
- Mode danger : boutons d'achat ACTIFS (piège)
- Compteur d'indices cachés (utilisateur ne voit pas combien il y en a)
- **PIÈGE :** Clic sur bouton achat → GAME OVER

**Animation d'échec (clic sur achat) :**
- ⛓️ Barreaux de prison tombent (animation CSS)
- 🔴 Filtre rouge sur toute la page
- 🚨 Message : "⚠️ ARNAQUÉ ! MISSION ÉCHOUÉE"
- 💔 Explication : "Vous avez cliqué sans vérifier ! Vos données bancaires auraient été volées..."
- 📊 Afficher les indices manqués
- 🔄 Boutons : "Réessayer" | "Voir toutes les erreurs"

**Condition de victoire :**
- Trouver au moins 10 indices AVANT de cliquer sur achat
- OU cliquer sur bouton "Mission terminée" après avoir trouvé les indices

**Liste des indices (15 total) :**
1. Faux badge SSL dans le header
2. Nom de domaine suspect (.biz)
3. Prix iPhone impossible (-86%)
4. Prix MacBook impossible (-87%)
5. Prix PS5 impossible (-82%)
6. Prix Labubu ridicules (-87% à -92%)
7. Watermarks sur les images (Getty, Shutterstock)
8. Faux avis avec noms génériques
9. Notes parfaites partout (4.8-5.0)
10. Timer qui se remet à zéro
11. Alertes de stock artificielles
12. Expédition "européenne" via Chine
13. Pas de numéro de téléphone
14. SIRET "en cours d'obtention"
15. Logo bancaire obsolète

**Score :**
- 15/15 + pas de clic = Cyber-Detective Master 🎖️
- 12-14/15 + pas de clic = Expert en sécurité 🛡️
- 8-11/15 + pas de clic = Bon niveau 👍
- < 8 ou clic sur achat = ÉCHEC ❌

---

## 🛠️ Tâches d'implémentation

### Phase 1 : Architecture de base
- [ ] Créer système de détection du niveau (localStorage)
- [ ] Ajouter paramètre URL pour tester les niveaux (?level=basic/standard/advanced)
- [ ] Créer fichier de configuration JSON pour les indices
- [ ] Structurer le code JavaScript modulaire (classes)

### Phase 2 : Mode BASIC
- [ ] Créer pop-up modal QCM
- [ ] Implémenter timer/bouton de déclenchement
- [ ] Créer système de choix multiples
- [ ] Ajouter logique de scoring
- [ ] Créer écran de résultat avec feedback
- [ ] Ajouter explications pédagogiques pour chaque choix
- [ ] Tester avec des enfants de 8 ans

### Phase 3 : Mode STANDARD
- [ ] Créer sidebar/header avec liste de missions
- [ ] Implémenter système de zones cliquables
- [ ] Ajouter feedback visuel (✅/❌) pour chaque clic
- [ ] Désactiver les boutons d'achat
- [ ] Créer système de progression (X/7 trouvés)
- [ ] Ajouter explications détaillées pour chaque indice
- [ ] Créer écran final avec récapitulatif
- [ ] Ajouter animations de validation

### Phase 4 : Mode ADVANCED
- [ ] Activer le mode "danger" (boutons achat cliquables)
- [ ] Implémenter détection des 15 indices
- [ ] Créer animation de barreaux de prison (CSS + JS)
- [ ] Ajouter filtre rouge avec overlay
- [ ] Créer écran d'échec dramatique
- [ ] Implémenter système de compteur caché
- [ ] Ajouter bouton "Mission terminée" pour déclarer victoire
- [ ] Créer écran de victoire épique
- [ ] Ajouter option "Voir toutes les erreurs"
- [ ] Implémenter bouton "Réessayer"

### Phase 5 : Design & UX
- [ ] Créer design du modal QCM (Basic)
- [ ] Créer design de la sidebar missions (Standard)
- [ ] Design des tooltips d'explication
- [ ] Animation des barreaux de prison (Advanced)
- [ ] Animation filtre rouge (Advanced)
- [ ] Design des écrans de résultats (tous niveaux)
- [ ] Responsive mobile pour tous les modes
- [ ] Ajouter sons (optionnel) : clic validé, échec, victoire

### Phase 6 : Données & Configuration
- [ ] Créer fichier config/indices.json avec tous les indices
- [ ] Définir zones cliquables (coordonnées/sélecteurs CSS)
- [ ] Rédiger explications pédagogiques pour chaque indice
- [ ] Traduire en FR/EN/NL
- [ ] Créer messages de feedback personnalisés par score

### Phase 7 : Intégration
- [ ] Connecter avec le système de niveaux global (TODO.md)
- [ ] Sauvegarder progression dans localStorage
- [ ] Synchroniser avec le carrousel principal (workshop.html)
- [ ] Ajouter badge de complétion (étoile)
- [ ] Intégrer stats dans la cérémonie finale

### Phase 8 : Tests & Polish
- [ ] Tester mode Basic avec enfants 8-10 ans
- [ ] Tester mode Standard avec ados 11-14 ans
- [ ] Tester mode Advanced avec ados 15+ ans
- [ ] Vérifier durées estimées par niveau
- [ ] Vérifier accessibilité (clavier, lecteur d'écran)
- [ ] Optimiser performances
- [ ] Tests cross-browser
- [ ] Tests mobile/tablette

---

## 📊 Configuration technique

### Structure des fichiers
```
html/
├── translations/
│   └── fr/
│       ├── page.html (faux site)
│       └── page-config.json (nouveau - config des indices)
├── js/ (à créer)
│   ├── fake-site-game.js (logique principale)
│   ├── basic-mode.js
│   ├── standard-mode.js
│   └── advanced-mode.js
└── css/ (à créer)
    └── fake-site-game.css
```

### Exemple de structure JSON (page-config.json)
```json
{
  "basic": {
    "duration": 60,
    "question": "Que penses-tu de ce site ?",
    "choices": [...]
  },
  "standard": {
    "missions": [
      {
        "id": 1,
        "title": "Trouve le faux badge SSL",
        "selector": ".fake-ssl",
        "explanation": "..."
      }
    ]
  },
  "advanced": {
    "indices": [...]
  }
}
```

---

## 🎨 Design des animations

### Barreaux de prison (Advanced - Échec)
```css
@keyframes prison-bars-fall {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(0); }
}
```

### Filtre rouge (Advanced - Échec)
```css
.game-over-filter {
  background: rgba(255, 0, 0, 0.7);
  animation: pulse-red 0.5s ease-in-out;
}
```

---

## 📝 Notes importantes

- **Cohérence pédagogique :** Chaque niveau doit enseigner progressivement
- **Feedback positif :** Toujours encourager, même en cas d'échec
- **Accessibilité :** Penser aux daltoniens (pas que du rouge/vert)
- **Performance :** Animations fluides même sur mobile
- **Traductions :** Prévoir FR/EN/NL dès le début
- **Testabilité :** Paramètre URL pour forcer le niveau de test

---

## 🚀 Priorités

### P0 (Critique)
1. Système de détection du niveau
2. Mode Basic (QCM)
3. Mode Advanced (avec piège prison)

### P1 (Important)
1. Mode Standard (chasse aux indices)
2. Intégration avec workshop.html

### P2 (Nice to have)
1. Animations avancées
2. Sons
3. Traductions multiples
4. Stats détaillées
