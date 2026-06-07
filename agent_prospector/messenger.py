import re
from core.claude_client import ClaudeClient
from core.logger import get_logger

logger = get_logger("agent_prospector.messenger")

SYSTEM_PROMPT = """Tu es un expert en networking professionnel LinkedIn.
Tu rédiges des messages personnalisés, chaleureux et authentiques, jamais génériques.
Tu ne génères jamais de messages commerciaux ou de spam.

MISE EN FORME obligatoire - texte brut humain uniquement :
- Interdit : tirets cadratins (— ou –), remplace-les par une virgule ou reformule
- Interdit : puces ou symboles (•, →, ✓, ★, ✅, ➜, etc.)
- Interdit : markdown (**gras**, # titres, *italique*)
- Écris en paragraphes naturels, séparés par des sauts de ligne
- Pas de numérotation visible dans le message final (1. 2. 3.)"""


def _clean_ai_formatting(text: str) -> str:
    """Supprime les artefacts de mise en forme typiques des LLM."""
    text = text.replace("—", ",").replace("–", "-")
    text = re.sub(r"[•→➜➡✓✔✅★⭐☑️◆◇▸▹]", "-", text)
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    text = re.sub(r"^#{1,3}\s+", "", text, flags=re.MULTILINE)
    return text.strip()


class ProspectMessenger:
    """
    Génère des messages LinkedIn personnalisés (connexion + InMail) via Claude.
    S'appuie sur le profil CV parsé et les infos de la cible.
    """

    def __init__(self):
        self.claude = ClaudeClient()
        logger.info("ProspectMessenger initialisé")

    def generate_connection_message(
        self,
        mon_profil: dict,
        cible: dict,
        objectif: str = "networking"
    ) -> str:
        """
        Génère un message de connexion LinkedIn (<= 300 caractères, limite LinkedIn).

        Args:
            mon_profil: Profil parsé du CV (clés : nom, titre, competences, resume…)
            cible: Profil de la cible (clés : nom, titre, entreprise, url…)
            objectif: "networking", "emploi" ou "collaboration"

        Returns:
            Message de connexion prêt à l'emploi (<= 300 caractères)
        """
        competences_str = ", ".join(mon_profil.get("competences", [])[:5])
        objectif_label = {
            "networking": "élargir mon réseau dans la data",
            "emploi": "explorer des opportunités dans ton domaine",
            "collaboration": "échanger sur un projet potentiel"
        }.get(objectif, objectif)

        user_prompt = f"""Rédige un message de connexion LinkedIn court et personnalisé.

Mon profil :
Nom : {mon_profil.get('nom', '')}
Titre : {mon_profil.get('titre', '')}
Compétences : {competences_str}
Résumé : {mon_profil.get('resume', '')}

Cible :
Nom : {cible.get('nom', '')}
Titre : {cible.get('titre', '')}
Entreprise : {cible.get('entreprise', '')}

Objectif : {objectif_label}

Règles STRICTES :
- Maximum 290 caractères (limite LinkedIn)
- Ne pas écrire "J'aimerais vous ajouter à mon réseau" ni phrase générique
- Mentionner un élément concret du profil cible qui justifie la connexion
- Vouvoiement naturel
- Une ou deux phrases maximum, pas de liste, pas de symboles
- Finir par une invitation ouverte à échanger

Réponds UNIQUEMENT avec le message, sans guillemets ni explication."""

        message = _clean_ai_formatting(self.claude.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=150
        ))

        if len(message) > 300:
            message = message[:297] + "..."

        logger.info(f"Message connexion généré pour {cible.get('nom', '?')} ({len(message)} chars)")
        return message

    def generate_inmail(
        self,
        mon_profil: dict,
        cible: dict,
        objectif: str = "emploi",
        details: str = ""
    ) -> str:
        """
        Génère un InMail LinkedIn développé (200-400 mots).

        Args:
            mon_profil: Profil parsé du CV
            cible: Profil de la cible
            objectif: "emploi", "partenariat" ou "conseil"
            details: Contexte supplémentaire (poste visé, projet…)

        Returns:
            InMail complet prêt à copier-coller
        """
        experiences_str = " | ".join([
            f"{e.get('poste', '')} chez {e.get('entreprise', '')}"
            for e in mon_profil.get("experiences", [])[:2]
        ])
        competences_str = ", ".join(mon_profil.get("competences", [])[:8])

        user_prompt = f"""Rédige un InMail LinkedIn professionnel et personnalisé.

Mon profil :
Nom : {mon_profil.get('nom', '')}
Titre : {mon_profil.get('titre', '')}
Compétences : {competences_str}
Expériences : {experiences_str}
Résumé : {mon_profil.get('resume', '')}

Profil cible :
Nom : {cible.get('nom', '')}
Titre : {cible.get('titre', '')}
Entreprise : {cible.get('entreprise', '')}

Objectif : {objectif}
Contexte / détails : {details or 'Non précisé'}

Écris le message en 3 ou 4 paragraphes courts séparés par des sauts de ligne :
Commence par une accroche personnalisée sur pourquoi CETTE personne précisément.
Présente-toi brièvement en 2-3 lignes.
Explique ce que tu cherches ou ce que tu apportes, de façon honnête et directe.
Termine par une invitation simple à échanger (pas une question fermée).

Ton : professionnel mais humain, comme un email qu'on écrirait soi-même
Longueur : 150-250 mots maximum
Vouvoiement naturel, pas de formules robotiques

Réponds UNIQUEMENT avec le message InMail, prêt à être copié-collé."""

        message = _clean_ai_formatting(self.claude.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=600
        ))

        logger.info(f"InMail généré pour {cible.get('nom', '?')} ({len(message)} chars)")
        return message

    def generate_batch(
        self,
        mon_profil: dict,
        cibles: list[dict],
        mode: str = "connexion",
        objectif: str = "networking",
        details: str = ""
    ) -> list[dict]:
        """
        Génère des messages pour une liste de profils.

        Args:
            mon_profil: Mon profil CV parsé
            cibles: Liste de profils cibles
            mode: "connexion" ou "inmail"
            objectif: Objectif des messages
            details: Contexte supplémentaire (pour InMail)

        Returns:
            Liste de dicts {profil, message}
        """
        results = []
        for cible in cibles:
            if mode == "connexion":
                message = self.generate_connection_message(mon_profil, cible, objectif)
            else:
                message = self.generate_inmail(mon_profil, cible, objectif, details)
            results.append({"profil": cible, "message": message})
        return results
