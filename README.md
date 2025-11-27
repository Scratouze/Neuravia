# 🧠 NEURAVIA-AUTONOME -- Situation actuelle

## 🚀 Mission

Agent IA **local**, **autonome**, **sandboxé**, piloté en CLI, conçu
pour : - **planifier** des objectifs en étapes (LLM local Ollama ou
fallback), - **exécuter** une boucle
`Run → Steps → Review → Masterplan`, - **générer** et tester des patchs
locaux avec **rollback automatique si tests échouent**, - **conserver
une mémoire symbolique persistante** (SQLite), - **rester sous contrôle
utilisateur** via des politiques de sécurité 100% paramétrables.

------------------------------------------------------------------------

## ✅ État actuel du développement

### 1) CLI stable

Entrée officielle :

    python -m neuravia.agent --goal "..." --max-steps N

Flags supportés : \| Flag \| Usage \| \|---\|---\| \|
`--config <path.yaml>` \| Charger config \| \|
`--profile [safe|balanced|danger]` \| Preset sécurité \| \| `--dry-run`
\| Simulation \|

### 2) Mémoire relationnelle

Base locale :

    data/memory.db

Tables : - `events` - `actions` - `artifacts` - `agent_masterplan`

### 3) Auto‑amélioration protégée par tests

-   Patchs format `diff`
-   Application locale sur dossiers allowlist
-   Tests immédiats + rollback si échec

Coverage actuel : **34 tests OK → noyau stable**

------------------------------------------------------------------------

## ⛔ Actions impossibles par architecture (garde‑fous)

-   Élévation de privilèges
-   Actions financières autonomes
-   Création d'identités / comptes en ligne
-   Contournement de protections (captcha, 2FA)
-   Propagation réseau hors sandbox
-   Chiffrement destructif ou suppression récursive non confirmée

------------------------------------------------------------------------

## 🧭 Roadmap validée des prochaines phases

### Phase 13 (prochaine) → Mémoire vectorielle + RAG interne

-   Ajout `Vector Store`
-   Retrieval sémantique des goals proches
-   Regroupement des runs par **projet**
-   Injection automatique du contexte dans planner (RAG)

### Phase 14 → Multi‑agents + Rules Engine

-   Séparation des rôles : Planner / Executor / Observer / Reviewer /
    Supervisor sécurité
-   Lois pondérables, **ordre et weights 100% configurables en YAML**
-   Logs auditables
-   Dry‑run global

------------------------------------------------------------------------

## 🏁 Conclusion

Neuravia est déjà un **agent autonome CLI robuste, local, configurable,
non‑expansif**, prêt pour les évolutions mémoire (Phase 13) et
multi‑agents/sécurité (Phase 14).

------------------------------------------------------------------------

👤 Auteur : JM 📌 Design : offline‑first • sandbox • 100% configurable
YAML • NO unsafe world ops • tests verts 📅 Version : 0.1‑alpha
