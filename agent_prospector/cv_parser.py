import json
import re
import pdfplumber
from pathlib import Path
from core.claude_client import ClaudeClient
from core.logger import get_logger

logger = get_logger("agent_prospector.cv_parser")

SYSTEM_PROMPT = """Tu es un expert en analyse de CV professionnels.
Extrais les informations structurées d'un CV de façon précise.
Réponds toujours avec un JSON valide uniquement, sans texte autour."""


class CVParser:
    """
    Parse un CV PDF et extrait les informations clés via pdfplumber + Claude.
    """

    def __init__(self):
        self.claude = ClaudeClient()
        logger.info("CVParser initialisé")

    def extract_text(self, pdf_path: str | Path) -> str:
        """Extrait le texte brut d'un PDF."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"CV introuvable : {pdf_path}")

        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        logger.info(f"CV extrait : {len(text)} caractères depuis {pdf_path.name}")
        return text

    def parse(self, pdf_path: str | Path) -> dict:
        """
        Parse le CV et retourne un dict structuré.

        Returns:
            dict avec clés : nom, titre, email, linkedin_url,
            competences, experiences, formation, langues, resume
        """
        raw_text = self.extract_text(pdf_path)

        user_prompt = f"""Analyse ce CV et extrais les informations en JSON strict.

CV :
{raw_text}

JSON attendu (respecte exactement cette structure) :
{{
  "nom": "Prénom Nom",
  "titre": "Titre professionnel actuel",
  "email": "email@exemple.com ou null",
  "linkedin_url": "https://linkedin.com/in/... ou null",
  "competences": ["skill1", "skill2", "skill3"],
  "experiences": [
    {{
      "poste": "Titre du poste",
      "entreprise": "Nom entreprise",
      "duree": "Jan 2024 - Mars 2025",
      "description": "Description courte du rôle"
    }}
  ],
  "formation": [
    {{
      "diplome": "Nom du diplôme",
      "ecole": "Nom de l'école",
      "annee": "2023"
    }}
  ],
  "langues": ["Français", "Anglais"],
  "resume": "Résumé du profil en 2-3 phrases."
}}"""

        response = self.claude.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=1500
        )

        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            raise ValueError(f"Réponse Claude non parseable : {response[:200]}")

        profile = json.loads(json_match.group())
        logger.info(f"CV parsé : {profile.get('nom', 'Inconnu')}")
        return profile

    def parse_from_text(self, raw_text: str) -> dict:
        """Parse depuis un texte brut (sans PDF, utile pour les tests ou Streamlit upload)."""
        user_prompt = f"""Analyse ce CV et extrais les informations en JSON strict.

CV :
{raw_text}

JSON attendu (respecte exactement cette structure) :
{{
  "nom": "Prénom Nom",
  "titre": "Titre professionnel actuel",
  "email": "email@exemple.com ou null",
  "linkedin_url": "https://linkedin.com/in/... ou null",
  "competences": ["skill1", "skill2", "skill3"],
  "experiences": [
    {{
      "poste": "Titre du poste",
      "entreprise": "Nom entreprise",
      "duree": "Jan 2024 - Mars 2025",
      "description": "Description courte"
    }}
  ],
  "formation": [
    {{
      "diplome": "Nom du diplôme",
      "ecole": "Nom de l'école",
      "annee": "2023"
    }}
  ],
  "langues": ["Français", "Anglais"],
  "resume": "Résumé du profil en 2-3 phrases."
}}"""

        response = self.claude.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=1500
        )

        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if not json_match:
            raise ValueError(f"Réponse Claude non parseable : {response[:200]}")

        profile = json.loads(json_match.group())
        logger.info(f"CV parsé depuis texte : {profile.get('nom', 'Inconnu')}")
        return profile
