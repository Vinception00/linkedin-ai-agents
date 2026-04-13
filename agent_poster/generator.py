from core.claude_client import ClaudeClient
from core.logger import get_logger

logger = get_logger("agent_poster.generator")

SYSTEM_PROMPT = """Tu es un expert en personal branding LinkedIn pour les profils data science juniors.
Tu rédiges des posts authentiques, concrets et engageants.
Tes posts font entre 150 et 250 mots, utilisent des sauts de ligne pour la lisibilité,
et se terminent par maximum 3 hashtags pertinents.
Tu évites le jargon corporate et tu parles comme un humain."""

TEMPLATES = {
    "conseil": """Rédige un post LinkedIn de type conseil/tips sur le sujet suivant : {sujet}
Contexte additionnel : {contexte}
Structure : accroche forte, 3-5 tips numérotés courts, conclusion avec call-to-action.""",

    "story": """Rédige un post LinkedIn de type storytelling sur cette expérience : {sujet}
Leçon à transmettre : {contexte}
Structure : hook narratif, déroulé en 2-3 paragraphes courts, leçon tirée, question ouverte.""",

    "veille": """Rédige un post LinkedIn de veille/actualité sur ce sujet : {sujet}
Mon point de vue : {contexte}
Structure : accroche sur la tendance, 2-3 points clés, regard de junior data scientist, question pour engager."""
}


class PostGenerator:
    """
    Génère des posts LinkedIn via Claude.
    Utilise des templates selon le type de post demandé.
    """

    def __init__(self):
        self.claude = ClaudeClient()
        logger.info("PostGenerator initialisé")

    def generate(self, post_type: str, sujet: str, contexte: str = "") -> str:
        """
        Génère un post LinkedIn.

        Args:
            post_type: "conseil", "story" ou "veille"
            sujet: Le sujet principal du post
            contexte: Détails supplémentaires ou point de vue personnel

        Returns:
            Le texte du post LinkedIn généré
        """
        if post_type not in TEMPLATES:
            raise ValueError(f"Type invalide : {post_type}. Choisir parmi : {list(TEMPLATES.keys())}")

        user_prompt = TEMPLATES[post_type].format(sujet=sujet, contexte=contexte)
        logger.info(f"Génération post type='{post_type}' sujet='{sujet}'")

        post = self.claude.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=600
        )

        logger.info(f"Post généré ({len(post)} caractères)")
        return post