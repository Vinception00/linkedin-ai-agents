import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from core.logger import get_logger

logger = get_logger("agent_poster.publisher")

COOKIES_FILE = Path("data/linkedin_cookies.json")


class LinkedInPublisher:
    """
    Poste sur LinkedIn via Playwright.
    Gère la session avec des cookies pour éviter de se reconnecter à chaque fois.
    """

    def __init__(self):
        self.email = os.getenv("LINKEDIN_EMAIL")
        self.password = os.getenv("LINKEDIN_PASSWORD")
        if not self.email or not self.password:
            raise ValueError("LINKEDIN_EMAIL et LINKEDIN_PASSWORD manquants dans .env")
        logger.info("LinkedInPublisher initialisé")

    def _save_cookies(self, context):
        """Sauvegarde les cookies de session dans un fichier."""
        cookies = context.cookies()
        COOKIES_FILE.parent.mkdir(exist_ok=True)
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f)
        logger.debug(f"Cookies sauvegardés ({len(cookies)} cookies)")

    def _load_cookies(self, context):
        """Charge les cookies sauvegardés si ils existent."""
        if not COOKIES_FILE.exists():
            return False
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        logger.debug("Cookies chargés")
        return True

    def _login(self, page, context):
        """Se connecte à LinkedIn et sauvegarde les cookies."""
        logger.info("Connexion à LinkedIn...")
        page.goto("https://www.linkedin.com/login")
        
        # Attend que les champs soient bien présents
        page.wait_for_selector("#username", timeout=10000)
        page.wait_for_selector("#password", timeout=10000)
        
        page.fill("#username", self.email)
        page.fill("#password", self.password)
        page.click("button[type=submit]")

        try:
            page.wait_for_url("**/feed/**", timeout=15000)
            logger.info("Connexion réussie")
            self._save_cookies(context)
        except PlaywrightTimeout:
            logger.error("Timeout lors de la connexion — vérifie tes identifiants")
            raise

    def _is_logged_in(self, page):
        """Vérifie si on est bien connecté."""
        return "feed" in page.url or "mynetwork" in page.url

    def post(self, content: str, headless: bool = True, dry_run: bool = False) -> bool:
        """
        Publie un post sur LinkedIn.

        Args:
            content: Le texte du post à publier
            headless: Si False, ouvre le navigateur visuellement
            dry_run: Si True, remplit le post mais ne publie pas

        Returns:
            True si le post a été publié (ou simulé), False sinon
        """
        logger.info(f"Démarrage du publisher LinkedIn (dry_run={dry_run})")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()

            cookies_loaded = self._load_cookies(context)

            if cookies_loaded:
                page.goto("https://www.linkedin.com/feed/")
                page.wait_for_timeout(2000)

            if not cookies_loaded or not self._is_logged_in(page):
                self._login(page, context)

            try:
                logger.info("Ouverture du champ de post...")
                post_button = page.locator("[role='button']:has-text('Commencer un post')")
                post_button.first.click()
                page.wait_for_timeout(2000)

                editor = page.locator(".ql-editor, [role='textbox']").first
                editor.click()
                editor.fill(content)
                page.wait_for_timeout(1000)

                if dry_run:
                    logger.info("DRY RUN — post visible mais non publié, fermeture dans 5 secondes...")
                    page.wait_for_timeout(5000)
                    browser.close()
                    return True

                publish_button = page.locator("button:has-text('Publier'), button:has-text('Post')")
                publish_button.last.click()
                page.wait_for_timeout(3000)

                logger.info("Post publié avec succès")
                browser.close()
                return True

            except Exception as e:
                logger.error(f"Erreur lors du posting : {e}")
                browser.close()
                return False