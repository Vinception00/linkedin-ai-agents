import os
import json
import sys
import subprocess
from pathlib import Path
from core.logger import get_logger

logger = get_logger("agent_prospector.searcher")


class LinkedInSearcher:
    """
    Recherche des profils LinkedIn par mots-clés via Playwright.
    Lance search_worker.py en subprocess pour isoler la boucle d'événements.
    """

    def __init__(self):
        self.email = os.getenv("LINKEDIN_EMAIL")
        self.password = os.getenv("LINKEDIN_PASSWORD")
        if not self.email or not self.password:
            raise ValueError("LINKEDIN_EMAIL et LINKEDIN_PASSWORD manquants dans .env")
        logger.info("LinkedInSearcher initialisé")

    def search_people(
        self,
        keywords: str,
        max_results: int = 10,
        degree: str = "2"
    ) -> list[dict]:
        """
        Recherche des profils LinkedIn selon des mots-clés.

        Args:
            keywords: Ex. "Data Scientist Paris", "Machine Learning Engineer"
            max_results: Nombre max de profils à retourner
            degree: Degré de connexion — "1" (1er), "2" (2ème), "3" (3ème+)

        Returns:
            Liste de dicts avec clés : nom, titre, entreprise, url
        """
        if degree not in ("1", "2", "3"):
            degree = "2"

        worker = Path(__file__).parent / "search_worker.py"
        cmd = [
            sys.executable, str(worker),
            "--keywords", keywords,
            "--max-results", str(max_results),
            "--degree", degree
        ]

        logger.info(f"Recherche LinkedIn : '{keywords}' (max={max_results}, degré={degree})")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=Path(__file__).parent.parent
            )

            if result.returncode != 0:
                logger.error(f"Worker erreur : {result.stderr}")
                return []

            for line in result.stdout.strip().split("\n"):
                if line.startswith("RESULTS:"):
                    profiles = json.loads(line[8:])
                    logger.info(f"{len(profiles)} profils trouvés pour '{keywords}'")
                    return profiles

            logger.error(f"Output inattendu du worker : {result.stdout[:200]}")
            return []

        except subprocess.TimeoutExpired:
            logger.error("Timeout recherche LinkedIn (>120s)")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"JSON invalide retourné par le worker : {e}")
            return []
        except Exception as e:
            logger.error(f"Erreur searcher : {e}")
            return []
