## 🔮 Priorité 1 - Système de sélection de difficulté

**Objectif :** Ajouter une sélection au démarrage : Basic / Standard / Advanced

**Décisions :**
- **Niveaux :** Basic / Standard / Advanced (au lieu de Facile/Medium/Hard)
- **Approche :** Combinaison filtrage de carrousels + limitation du nombre de questions
- **Public cible :**
  - Basic : enfants de 8 ans ou sessions courtes (~10 min)
  - Standard : niveau intermédiaire (~20 min)
  - Advanced : complet et approfondi (~40 min)

---

## 📋 Répartition du contenu par niveau

### 🟢 BASIC (~10 min)

**Carrousels (4-5 activités) :**
- ✅ Anecdotes Tech
- ✅ Réseaux Sociaux
- ✅ Email Piège
- ✅ WiFi Piège
- ✅ Les Yeux du Lion (webcam)

**Questions pour un Champion (2-3 catégories) :**
- Anecdotes : 5 questions aléatoires
- Mobile : 4 questions
- **Total : ~9 questions**

---

### 🟡 STANDARD (~20 min)

**Carrousels (6-7 activités) :**
- Tous les carrousels Basic +
- ✅ Mot de passe Fortress
- ✅ Confidentialité

**Questions pour un Champion (3-4 catégories) :**
- Anecdotes : 7 questions
- Mobile : 6 questions
- Protection : 5 questions
- **Total : ~18 questions**

---

### 🔴 ADVANCED (complet, ~40 min)

**Carrousels :**
- ✅ TOUS les carrousels (pas de filtrage)

**Questions pour un Champion :**
- ✅ Toutes les catégories (AI, Protection, Mobile, Passwords, Anecdotes)
- **Total : 51 questions**

---

---

## 🎯 Écran de sélection

### Design (Option B - Un seul écran)

```
┌─────────────────────────────────────┐
│        🎮 CyberQuestKids            │
├─────────────────────────────────────┤
│                                     │
│        Bienvenue !                  │
│                                     │
│  Ton prénom :                       │
│  [________________]                 │
│                                     │
│  Ton âge :                          │
│  🎚️ 6────●────────20+               │
│         12 ans                      │
│                                     │
│                                     │
│         [Commencer →]               │
│                                     │
├─────────────────────────────────────┤
│      Langue : 🇫🇷 🇬🇧 🇳🇱           │
└─────────────────────────────────────┘
```

### Logique de sélection automatique (silencieuse)

**Mapping âge → niveau :**
- **6-9 ans** → BASIC
- **10-12 ans** → STANDARD
- **13-20+ ans** → ADVANCED

**Important :** Le niveau n'est PAS affiché à l'utilisateur pour éviter toute frustration.

### Comportement

**Drapeaux (footer) :**
- Changent la langue du formulaire uniquement
- **Ne démarrent PAS le site** (modification du comportement actuel)

**Bouton "Commencer" :**
- Seul déclencheur du démarrage du site
- Calcule et sauvegarde le niveau automatiquement

### Sauvegarde localStorage

```json
{
  "playerName": "Alex",
  "playerAge": 12,
  "selectedLevel": "standard",
  "language": "fr"
}
```

### Améliorations futures

- Permettre de modifier le niveau/profil en cours de route
- Bouton "Changer de profil" dans les paramètres
- Multi-profils (pour familles/classes)

---

## 🚀 TODO - Implémentation

### Écran de sélection
- [ ] Créer écran de bienvenue avec formulaire (prénom + âge)
- [ ] Implémenter slider d'âge (6 à 20+)
- [ ] Ajouter drapeaux en footer (modifier comportement : ne pas démarrer)
- [ ] Implémenter logique de mapping âge → niveau (silencieux)
- [ ] Sauvegarder dans localStorage (playerName, playerAge, selectedLevel, language)

### Filtrage du contenu
- [ ] Implémenter logique de filtrage des carrousels
- [ ] Adapter "Questions pour un Champion" selon le niveau
- [ ] **CRITIQUE** : Modifier `checkFantasyQuestUnlock()` pour vérifier UNIQUEMENT les carrousels visibles selon le niveau (actuellement hardcodé 0-8)
- [ ] **CRITIQUE** : S'assurer que la cérémonie (easter egg) se déclenche correctement avec les carrousels filtrés
- [ ] Tester les durées estimées pour chaque niveau