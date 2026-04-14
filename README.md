# LinkedIn AI Agent 🤖

Projet personnel de portfolio — agent IA qui automatise la création et la publication de posts LinkedIn, avec dashboard d'analytics.

## Fonctionnalités

- **Génération automatique de posts** via l'API Claude (Anthropic)
- **Publication automatisée** sur LinkedIn via Playwright
- **Calendrier éditorial intelligent** — l'agent choisit le bon sujet selon le jour
- **Scheduler** — pipeline quotidien automatique
- **Dashboard Streamlit** — interface pour générer, publier et analyser les posts
- **Analytics** — scraping automatique des stats d'engagement (likes, commentaires, vues)

## Stack technique

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
│   ├── publisher.py        # Publication LinkedIn via Playwright
│   ├── content_planner.py  # Sélection automatique du sujet
│   └── scheduler.py        # Pipeline quotidien automatisé
├── agent_prospector/
│   ├── cv_parser.py        # Parsing CV PDF
│   ├── searcher.py         # Recherche profils LinkedIn
│   └── messenger.py        # Messages personnalisés
├── core/
│   ├── claude_client.py    # Client API Anthropic
│   ├── linkedin_client.py  # Client LinkedIn
│   └── logger.py           # Logging centralisé
├── data/
│   └── content_calendar.yaml  # Stratégie éditoriale
├── app.py                  # Dashboard Streamlit
└── main.py                 # Point d'entrée
## Installation

```bash
# Cloner le repo
git clone https://github.com/Vinception00/linkedin-ai-agents.git
cd linkedin-ai-agents

# Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Crée un fichier `.env` à la racine :
ANTHROPIC_API_KEY=ta_clé_anthropic
LINKEDIN_EMAIL=ton@email.com
LINKEDIN_PASSWORD=ton_mot_de_passe

## Utilisation

**Lancer le dashboard :**
```bash
streamlit run app.py
```

**Lancer le pipeline manuellement :**
```bash
python main.py
```

**Lancer le scheduler automatique :**
```python
from agent_poster.scheduler import PostScheduler
scheduler = PostScheduler(hour=9, minute=0)
scheduler.start()
```

## Roadmap

- [x] Agent poster — génération et publication automatique
- [x] Content planner — sélection intelligente des sujets
- [x] Dashboard Streamlit
- [x] Analytics scraping
- [ ] Agent prospecteur — lecture CV + recherche LinkedIn
- [ ] Notifications email avant publication
- [ ] Support multi-langues

## Auteur

**Vince** — Data Scientist junior | [LinkedIn](www.linkedin.com/in/vince-vindex-compper-030496294)