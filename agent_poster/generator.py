import re
from core.claude_client import ClaudeClient
from core.logger import get_logger

logger = get_logger("agent_poster.generator")

from datetime import datetime


def _clean_ai_formatting(text: str) -> str:
    """Supprime les artefacts de mise en forme typiques des LLM."""
    text = text.replace("—", ",").replace("–", "-")
    text = re.sub(r"[•→➜➡✓✔✅★⭐☑️◆◇▸▹]", "-", text)
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    text = re.sub(r"^#{1,3}\s+", "", text, flags=re.MULTILINE)
    return text.strip()

SYSTEM_PROMPT = f"""Tu es un expert en personal branding LinkedIn pour les profils data science juniors.
Nous sommes en {datetime.now().year}, tiens-en compte dans toutes tes références temporelles.

RÈGLES DE CONTENU :
- N'invente jamais d'anecdotes personnelles ou d'expériences vécues à la première personne
- Ne génère pas de phrases comme "j'ai passé X heures", "mon manager m'a dit", "ma première mission"
- Pour les posts conseil : présente les tips directement, de façon pédagogique et engageante
- Pour les posts story : développe UNIQUEMENT le contexte réel fourni par l'utilisateur, sans en inventer
- Pour les posts veille : exprime un point de vue analytique sur la tendance, pas une anecdote
- Tes posts font entre 150 et 250 mots
- Maximum 3 hashtags pertinents à la fin

MISE EN FORME — texte brut uniquement, comme un vrai humain :
- Interdit : tirets cadratins (— ou –), remplace-les par une virgule ou reformule la phrase
- Interdit : puces ou symboles décoratifs (•, →, ✓, ★, ✅, ➜, etc.)
- Interdit : markdown (**gras**, *italique*, # titres)
- Utilise uniquement des sauts de ligne pour aérer
- Pour les listes dans un post, écris "1." "2." "3." ou commence chaque ligne par un verbe d'action
- Parle comme un humain, évite le jargon corporate"""

TEMPLATES = {
    "conseil": """Rédige un post LinkedIn de type conseil/tips sur le sujet suivant : {sujet}
Contexte additionnel : {contexte}

Structure : 
- Accroche forte qui pose le problème ou l'enjeu
- 3 à 5 tips numérotés courts et concrets avec exemples de code si pertinent
- Conclusion avec question ouverte pour engager la communauté

Ne commence pas par "J'ai vécu" ou une anecdote inventée. Va droit au but.""",

    "story": """Rédige un post LinkedIn de type storytelling basé UNIQUEMENT sur ce contexte réel : {sujet}
Détails fournis par l'auteur : {contexte}

Structure :
- Hook basé sur le contexte fourni
- Développe l'histoire en 2-3 paragraphes courts en restant fidèle aux faits donnés
- Leçon concrète tirée de cette expérience
- Question ouverte finale

IMPORTANT : N'ajoute aucun détail inventé. Si le contexte est court, reste concis plutôt que d'inventer.""",

    "veille": """Rédige un post LinkedIn de veille/actualité sur ce sujet : {sujet}
Mon point de vue personnel : {contexte}

Structure :
- Accroche sur la tendance ou l'actualité
- 2-3 points clés factuels et analysés
- Point de vue de data scientist junior sur les implications concrètes
- Question pour engager la communauté

Présente-toi comme quelqu'un qui observe et analyse, pas comme quelqu'un qui a vécu quelque chose d'inventé."""
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

        post = _clean_ai_formatting(post)
        logger.info(f"Post généré ({len(post)} caractères)")
        return post