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

## 🚀 TODO - Implémentation

- [ ] Créer écran de sélection de niveau (Basic/Standard/Advanced)
- [ ] Implémenter logique de filtrage des carrousels
- [ ] Adapter "Questions pour un Champion" selon le niveau
- [ ] Tester les durées estimées pour chaque niveau
- [ ] Ajouter système de sauvegarde du niveau choisi