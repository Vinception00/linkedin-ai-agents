import yaml
import random
from datetime import datetime
from pathlib import Path
from core.claude_client import ClaudeClient
from core.logger import get_logger

logger = get_logger("agent_poster.content_planner")

CALENDAR_FILE = Path("data/content_calendar.yaml")

DAY_MAP = {
    0: "monday",
    1: "tuesday", 
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday"
}


class ContentPlanner:
    """
    Décide automatiquement quel post générer selon le jour de la semaine.
    Utilise Claude pour choisir un sujet pertinent et original.
    """

    def __init__(self):
        self.claude = ClaudeClient()
        self.calendar = self._load_calendar()
        self.profile = self.calendar["profile"]
        logger.info("ContentPlanner initialisé")

    def _load_calendar(self) -> dict:
        """Charge le calendrier éditorial depuis le fichier YAML."""
        if not CALENDAR_FILE.exists():
            raise FileNotFoundError(f"Fichier calendrier introuvable : {CALENDAR_FILE}")
        with open(CALENDAR_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_todays_plan(self) -> dict:
        """
        Retourne le plan du jour selon le calendrier.
        Si aujourd'hui n'est pas dans le calendrier, retourne None.
        """
        today = DAY_MAP[datetime.now().weekday()]
        schedule = self.calendar.get("schedule", {})

        if today not in schedule:
            logger.info(f"Pas de post prévu aujourd'hui ({today})")
            return None

        plan = schedule[today]
        logger.info(f"Plan du jour ({today}) : type='{plan['type']}' theme='{plan['theme']}'")
        return plan

    def pick_topic(self, post_type: str) -> str:
        """
        Utilise Claude pour choisir un sujet frais et pertinent.
        Évite la répétition en demandant un angle original.
        """
        topics = self.calendar["topics_bank"].get(post_type, [])
        # Donne quelques suggestions à Claude mais le laisse être créatif
        suggestions = random.sample(topics, min(3, len(topics)))

        prompt = f"""Tu es un expert en personal branding pour data scientists.

Profil : {self.profile['name']}, {self.profile['role']}, {self.profile['experience']}
Stack : {', '.join(self.profile['stack'])}
Objectif : {self.profile['objectif']}

Type de post à créer : {post_type}
Suggestions de sujets : {', '.join(suggestions)}

Choisis UN sujet précis et original pour un post LinkedIn aujourd'hui.
Le sujet doit être concret, utile pour un data scientist junior, et engageant.
Tu peux t'inspirer des suggestions ou proposer quelque chose de différent.

Réponds UNIQUEMENT avec le sujet choisi en une phrase courte, sans explication."""

        topic = self.claude.generate(
            system_prompt="Tu es un stratège en contenu LinkedIn pour la data science.",
            user_prompt=prompt,
            max_tokens=100
        )
        logger.info(f"Sujet choisi par Claude : {topic}")
        return topic.strip()

    def get_daily_post_params(self) -> dict | None:
        """
        Retourne tous les paramètres nécessaires pour générer le post du jour.
        Retourne None si pas de post prévu aujourd'hui.
        """
        plan = self.get_todays_plan()
        if not plan:
            return None

        post_type = plan["type"]
        topic = self.pick_topic(post_type)

        return {
            "post_type": post_type,
            "sujet": topic,
            "contexte": f"Profil : {self.profile['role']} avec {self.profile['experience']}. Stack : {', '.join(self.profile['stack'])}"
        }