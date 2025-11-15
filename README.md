# Neuravia — Agent Autonome (Phase 1 → Phase 9)

Neuravia est une base de développement pour créer un **agent autonome local**, sécurisé, extensible, capable de s’auto-améliorer et d’utiliser des modèles LLM en local (Ollama). Le projet progresse par "phases" successives jusqu’à un agent réellement autonome et intelligent.

---

# 🚀 Fonctionnalités Actuelles

## ✔️ Architecture Modulaire
- `neuravia/autoimprove` : moteur complet d’auto-amélioration
- `neuravia/agent` : boucle d’exécution d’un agent autonome
- `neuravia/llm` : abstractions LLM + support Ollama
- `neuravia/core` : settings, sandbox, sécurité
- `config/` : profils, règles et paramètres

## ✔️ 34 tests unitaires — tous validés
Le projet inclut une suite de tests complète garantissant la stabilité du système.

## ✔️ Self-improvement sécurisé
- Application de patchs `.patch`
- Vérification du format et de la sécurité
- Backups automatiques
- Rollback si les tests échouent
- Validation obligatoire en mode *safe*

## ✔️ Intégration LLM locale (Ollama)
- Support natif de `ollama run <model>`
- Gestion Unicode Windows
- Gestion d’erreur robuste

## ✔️ Agent autonome Phase 9
- Reçoit un objectif (`--goal`)
- Génère un plan étape par étape
- S’exécute pendant un nombre limité de steps
- Utilise un modèle local (ex : Llama3.1)

---

# 📦 Installation (mode développement)

```bash
python -m pip install -e '.[dev,web]'
```

Assurez-vous également que **Ollama** est installé :

```bash
winget install -e --id Ollama.Ollama
ollama serve
ollama list
```

---

# 🎯 Utilisation de la CLI principale

## 1. Mode standard
```bash
python -m neuravia --goal "Mon objectif" --config config --profile safe
```

## 2. Exécuter la demo LLM
```bash
python -m neuravia.llm.demo --goal "Organiser mon bureau en 3 étapes" --model llama3.1:8b-instruct
```

## 3. Agent autonome (Phase 9)
```bash
python -m neuravia.agent --goal "Organiser mon bureau" \
                         --model llama3.1:8b \
                         --max-steps 3
```

---

# 🔧 Self-Improvement (patch automatique)

## Vérifier un patch sans l’appliquer
```bash
python -m neuravia --config config --profile safe \
                   --self-improve-patch mypatch.patch
```

## Appliquer un patch avec approbation
```bash
python -m neuravia --config config --profile safe \
                   --self-improve-patch mypatch.patch --approve
```

Sortie typique :
```json
{
  "status": "applied_ok",
  "backups_dir": ".patch_backups/2025...",
  "changed": ["neuravia/..."],
  "pytest_ok": true
}
```

---

# 🧭 Roadmap des prochaines phases

## 🔮 Phase 10 — Mémoire avancée
- Scratchpad interne
- Mémoire longue durée (SQLite déjà prête)
- Résumés automatiques
- Persistance des observations

## 🛠️ Phase 11 — Outils de l’agent
- Accès contrôlé au système (fs, exec)
- Recherche locale
- Python sandboxé
- Extensions modulaires

## 🧠 Phase 12 — Agent autonome complet
- Planification hiérarchique
- ReAct / Chain-of-Thought interne
- Gestion de sous-objectifs
- Sécurité adaptative

---

# 🤝 Contribution
Les contributions (patchs `.patch`) sont encouragées. Le système d’auto-amélioration garantit que toute modification passe par :
1. vérification de sécurité
2. tests
3. rollback si nécessaire

---

# 📄 Licence
Projet expérimental — usage personnel, éducatif et R&D. À ne pas utiliser en production sans audit complet.

---

# 📌 Statut actuel
**Neuravia atteint la Phase 9 : un agent autonome minimal, utilisant un LLM local, sécurisé, auto-améliorable et testé.**

Les phases 10–12 transformeront Neuravia en véritable IA autonome locale.
