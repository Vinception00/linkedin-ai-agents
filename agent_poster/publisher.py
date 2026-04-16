import json
import os
import sys
import subprocess
from pathlib import Path
from core.logger import get_logger

logger = get_logger("agent_poster.publisher")

COOKIES_FILE = Path("data/linkedin_cookies.json")


class LinkedInPublisher:

    def __init__(self):
        self.email = os.getenv("LINKEDIN_EMAIL")
        self.password = os.getenv("LINKEDIN_PASSWORD")
        if not self.email or not self.password:
            raise ValueError("LINKEDIN_EMAIL et LINKEDIN_PASSWORD manquants dans .env")
        logger.info("LinkedInPublisher initialise")

    def post(self, content: str, headless: bool = True, dry_run: bool = False) -> bool:
        worker = Path(__file__).parent / "publish_worker.py"
        cmd = [sys.executable, str(worker), content]
        if dry_run:
            cmd.append("--dry-run")
        if headless:
            cmd.append("--headless")

        logger.info(f"Lancement publish_worker (dry_run={dry_run})")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=Path(__file__).parent.parent
            )
            output = result.stdout.strip()
            logger.info(f"Worker output : {output}")

            if result.returncode != 0:
                logger.error(f"Worker erreur : {result.stderr}")
                return False

            if "PUBLISH_OK" in output or "DRY_RUN_OK" in output:
                return True

            logger.error(f"Output inattendu : {output}")
            return False

        except subprocess.TimeoutExpired:
            logger.error("Timeout")
            return False
        except Exception as e:
            logger.error(f"Erreur : {e}")
            return False
