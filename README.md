# LinkedIn AI Agent

Un projet perso qui automatise ma présence LinkedIn : génération de posts, publication, analytics, et maintenant prospection. L'idée c'est de passer moins de temps à galérer devant une page blanche et plus de temps sur ce qui compte.

## Ce que ça fait

**Agent Poster** : génère des posts LinkedIn adaptés à mon profil data scientist, les planifie selon un calendrier éditorial, et les publie automatiquement via Playwright. Trois formats disponibles : conseil, storytelling, veille tech.

**Agent Prospecteur** : parse un CV en PDF, cherche des profils LinkedIn correspondant à des critères donnés, et génère des messages de connexion ou InMails personnalisés via Claude. Les messages évitent les formules génériques et s'adaptent à chaque profil cible.

**Dashboard** : interface Streamlit pour générer et publier des posts manuellement, suivre l'engagement (likes, commentaires, vues), et faire tourner le prospecteur.

## Stack

| Composant | Technologie |
|-----------|-------------|
| LLM | Claude API (Anthropic) |
| Automatisation navigateur | Playwright |
| Interface | Streamlit |
| Visualisation | Plotly |
| Base de données | SQLite |
| Scheduling | APScheduler |
| Parsing CV | pdfplumber |

## Architecture

    linkedin-ai-agents/
    ├── agent_poster/
    │   ├── generator.py        # Génération posts via Claude
    │   ├── publisher.py        # Publication via Playwright
    │   ├── publish_worker.py   # Worker subprocess Playwright
    │   ├── content_planner.py  # Sélection du sujet selon le jour
    │   └── scheduler.py        # Pipeline quotidien automatique
    ├── agent_prospector/
    │   ├── cv_parser.py        # Parsing CV PDF via pdfplumber + Claude
    │   ├── searcher.py         # Recherche profils LinkedIn
    │   ├── search_worker.py    # Worker subprocess Playwright
    │   └── messenger.py        # Génération messages personnalisés
    ├── core/
    │   ├── claude_client.py    # Client API Anthropic
    │   ├── analytics_scrapper.py  # Scraping stats engagement
    │   └── logger.py           # Logging centralisé
    ├── data/
    │   ├── content_calendar.yaml
    │   └── posts.db
    ├── app.py                  # Dashboard Streamlit
    └── main.py                 # Point d'entrée scheduler

## Installation

```bash
git clone https://github.com/Vinception00/linkedin-ai-agents.git
cd linkedin-ai-agents

python -m venv venv
venv\Scripts\activate  # Windows

pip install -r requirements.txt
playwright install chromium
```

## Configuration

Crée un fichier `.env` à la racine :

```
ANTHROPIC_API_KEY=ta_clé_anthropic
LINKEDIN_EMAIL=ton@email.com
LINKEDIN_PASSWORD=ton_mot_de_passe
```

## Utilisation

**Dashboard (recommandé pour commencer) :**
```bash
streamlit run app.py
```

Depuis le dashboard tu peux générer un post, le modifier et le publier. La page Prospecteur te guide en 3 étapes : importe ton CV, lance une recherche LinkedIn, génère les messages.

**Scheduler automatique :**
```bash
python main.py
```

Lance le pipeline quotidien en arrière-plan. Il génère et publie automatiquement chaque matin selon le calendrier éditorial défini dans `data/content_calendar.yaml`.

## Roadmap

- [x] Agent poster — génération et publication automatique
- [x] Content planner — sélection intelligente des sujets
- [x] Dashboard Streamlit
- [x] Analytics scraping (likes, commentaires, vues)
- [x] Agent prospecteur — parsing CV + recherche LinkedIn + messages personnalisés
- [ ] Notifications email avant publication
- [ ] Support multi-langues

## Auteur

**Vince** — Data Scientist junior | [LinkedIn](www.linkedin.com/in/vince-vindex-compper-030496294)
