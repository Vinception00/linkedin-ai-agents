import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from data.posts_db import PostsDB
from core.logger import get_logger

logger = get_logger("core.analytics_scraper")

COOKIES_FILE = Path("data/linkedin_cookies.json")
DEBUG_DIR = Path("logs")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class AnalyticsScraper:
    """
    Scrape les stats d'engagement des posts LinkedIn.
    """

    def __init__(self):
        self.db = PostsDB()
        logger.info("AnalyticsScraper initialisé")

    def _load_cookies(self, context) -> bool:
        if not COOKIES_FILE.exists():
            return False
        with open(COOKIES_FILE, "r") as f:
            context.add_cookies(json.load(f))
        return True

    def _is_logged_in(self, page) -> bool:
        url = page.url
        return "linkedin.com/feed" in url or "linkedin.com/in/" in url or "linkedin.com/posts" in url

    def _parse_number(self, text: str) -> int:
        """Convertit '1,2k', '1 234', '1 234' en entier."""
        if not text:
            return 0
        # Retire les espaces fins (U+202F) et espaces normaux
        text = text.replace(" ", "").replace(" ", "").replace(" ", "")
        text = text.lower().replace(",", ".")
        if "k" in text:
            try:
                return int(float(text.replace("k", "")) * 1000)
            except ValueError:
                pass
        digits = "".join(c for c in text if c.isdigit())
        return int(digits) if digits else 0

    def _extract_number_from_aria(self, label: str) -> int:
        """Extrait un nombre depuis un aria-label comme '3 personnes ont réagi'."""
        match = re.search(r"[\d\s ,\.k]+", label, re.IGNORECASE)
        if match:
            return self._parse_number(match.group().strip())
        return 0

    def scrape_post_stats(self, post_url: str, post_id: int, debug: bool = False):
        """
        Scrape les stats d'un post LinkedIn depuis son URL.

        Args:
            post_url: URL du post (format /feed/update/urn:li:activity:... ou /posts/...)
            post_id: ID en base pour sauvegarder les stats
            debug: Si True, prend une screenshot de debug dans logs/
        """
        logger.info(f"Scraping post_id={post_id} url={post_url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-web-security", "--no-sandbox"]
            )
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.set_default_timeout(30000)

            self._load_cookies(context)

            try:
                page.goto(post_url, timeout=60000)
                page.wait_for_timeout(4000)

                if not self._is_logged_in(page):
                    logger.warning("Cookies expirés ou non valides — scraping impossible")
                    browser.close()
                    return

                if debug:
                    screenshot_path = DEBUG_DIR / f"analytics_debug_{post_id}.png"
                    page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"Screenshot debug : {screenshot_path}")

                likes = self._scrape_reactions(page)
                commentaires = self._scrape_comments(page)
                republications = self._scrape_reposts(page)
                vues = self._scrape_views(page)

                logger.info(
                    f"Stats post {post_id} : likes={likes}, "
                    f"commentaires={commentaires}, reposts={republications}, vues={vues}"
                )
                self.db.save_stats(post_id, likes, commentaires, republications, vues)

            except Exception as e:
                logger.error(f"Erreur scraping post {post_id} : {e}")
                if debug:
                    try:
                        page.screenshot(path=str(DEBUG_DIR / f"analytics_error_{post_id}.png"))
                    except Exception:
                        pass
            finally:
                browser.close()

    def _scrape_reactions(self, page) -> int:
        """Récupère le nombre de réactions/likes."""
        selectors = [
            # Aria-label sur le bouton de réaction (le plus fiable)
            "button[aria-label*='reaction']",
            "button[aria-label*='réaction']",
            "button[aria-label*='React']",
            # Compteurs textuels
            ".social-counts-reactions__count-value",
            ".social-counts-reactions__count",
            "[data-test-id='social-counts-reactions']",
            # Fallback générique — cherche le nombre dans la zone sociale
            ".social-details-social-counts__reactions-count",
            ".reactions-react-button__count",
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    aria = el.get_attribute("aria-label") or ""
                    text = el.inner_text().strip()
                    val = self._extract_number_from_aria(aria) or self._parse_number(text)
                    if val > 0:
                        logger.debug(f"Réactions via '{sel}' : {val}")
                        return val
            except Exception:
                continue
        return 0

    def _scrape_comments(self, page) -> int:
        """Récupère le nombre de commentaires."""
        selectors = [
            "button[aria-label*='comment']",
            "button[aria-label*='commentaire']",
            ".social-counts-comments__count-value",
            ".social-counts-comments",
            "[data-test-id='social-counts-comments']",
            ".social-details-social-counts__comments",
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    aria = el.get_attribute("aria-label") or ""
                    text = el.inner_text().strip()
                    val = self._extract_number_from_aria(aria) or self._parse_number(text)
                    if val > 0:
                        logger.debug(f"Commentaires via '{sel}' : {val}")
                        return val
            except Exception:
                continue
        return 0

    def _scrape_reposts(self, page) -> int:
        """Récupère le nombre de republications."""
        selectors = [
            "button[aria-label*='repost']",
            "button[aria-label*='republication']",
            "button[aria-label*='Repost']",
            "[data-test-id='social-counts-reposts']",
            ".social-counts-reposts",
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    aria = el.get_attribute("aria-label") or ""
                    text = el.inner_text().strip()
                    val = self._extract_number_from_aria(aria) or self._parse_number(text)
                    if val > 0:
                        logger.debug(f"Reposts via '{sel}' : {val}")
                        return val
            except Exception:
                continue
        return 0

    def _scrape_views(self, page) -> int:
        """
        Récupère les impressions/vues du post.
        Uniquement disponible sur tes propres posts quand tu es connecté.
        """
        selectors = [
            # Section analytics visible sous ton propre post
            ".post-analytics-entry__count",
            ".analytics-entry__meta-count",
            "[data-test-analytics]",
            # Texte contenant "impression" ou "vue"
            "span:has-text('impressions')",
            "span:has-text('vues')",
            "button[aria-label*='impression']",
            "button[aria-label*='vue']",
            # Fallback — cherche le lien analytics sous le post
            "a[href*='analytics'][href*='activity']",
        ]
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    aria = el.get_attribute("aria-label") or ""
                    text = el.inner_text().strip()
                    val = self._extract_number_from_aria(aria) or self._parse_number(text)
                    if val > 0:
                        logger.debug(f"Vues via '{sel}' : {val}")
                        return val
            except Exception:
                continue
        return 0

    def scrape_all_posts(self, debug: bool = False):
        """Scrape les stats de tous les posts en base qui ont une URL."""
        posts = self.db.get_all_posts()
        posts_with_url = [p for p in posts if p.get("url")]

        if not posts_with_url:
            logger.info("Aucun post avec URL en base — scraping ignoré")
            return

        logger.info(f"Scraping {len(posts_with_url)} posts...")
        for post in posts_with_url:
            self.scrape_post_stats(post["url"], post["id"], debug=debug)

    def update_post_url(self, post_id: int, url: str):
        """Met à jour l'URL d'un post existant en base (pour corriger les anciens posts)."""
        self.db.conn.execute(
            "UPDATE posts SET url = ? WHERE id = ?", (url, post_id)
        )
        self.db.conn.commit()
        logger.info(f"URL mise à jour pour post_id={post_id} : {url}")
