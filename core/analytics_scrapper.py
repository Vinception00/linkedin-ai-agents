import json
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from data.posts_db import PostsDB
from core.logger import get_logger

logger = get_logger("core.analytics_scraper")

COOKIES_FILE = Path("data/linkedin_cookies.json")


class AnalyticsScraper:
    """
    Scrape les stats d'engagement des posts LinkedIn.
    Utilise les cookies existants pour éviter de se reconnecter.
    """

    def __init__(self):
        self.db = PostsDB()
        logger.info("AnalyticsScraper initialisé")

    def _load_cookies(self, context) -> bool:
        if not COOKIES_FILE.exists():
            return False
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        return True

    def scrape_post_stats(self, post_url: str, post_id: int):
        """
        Scrape les stats d'un post LinkedIn depuis son URL.
        """
        logger.info(f"Scraping stats pour post_id={post_id} url={post_url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            self._load_cookies(context)
            page.goto(post_url)
            page.wait_for_timeout(3000)

            try:
                # Likes
                likes = 0
                try:
                    likes_el = page.locator("[data-test-id='social-actions__reaction-count'], .social-counts-reactions__count").first
                    likes_text = likes_el.inner_text().strip()
                    likes = self._parse_number(likes_text)
                except:
                    pass

                # Commentaires
                commentaires = 0
                try:
                    comments_el = page.locator("[data-test-id='social-actions__comments-count'], .social-counts-comments").first
                    comments_text = comments_el.inner_text().strip()
                    commentaires = self._parse_number(comments_text)
                except:
                    pass

                # Republications
                republications = 0
                try:
                    reposts_el = page.locator("[data-test-id='social-actions__repost-count']").first
                    reposts_text = reposts_el.inner_text().strip()
                    republications = self._parse_number(reposts_text)
                except:
                    pass

                # Vues (disponibles uniquement sur tes propres posts)
                vues = 0
                try:
                    views_el = page.locator(".post-analytics-entry__count, [data-test-analytics]").first
                    views_text = views_el.inner_text().strip()
                    vues = self._parse_number(views_text)
                except:
                    pass

                logger.info(f"Stats : likes={likes}, commentaires={commentaires}, vues={vues}")
                self.db.save_stats(post_id, likes, commentaires, republications, vues)

            except Exception as e:
                logger.error(f"Erreur scraping : {e}")
            finally:
                browser.close()

    def scrape_all_posts(self):
        """Scrape les stats de tous les posts en base qui ont une URL."""
        posts = self.db.get_all_posts()
        posts_with_url = [p for p in posts if p.get("url")]

        if not posts_with_url:
            logger.info("Aucun post avec URL en base")
            return

        logger.info(f"Scraping {len(posts_with_url)} posts...")
        for post in posts_with_url:
            self.scrape_post_stats(post["url"], post["id"])

    def _parse_number(self, text: str) -> int:
        """Convertit '1,2k' ou '1 234' en entier."""
        text = text.lower().replace(" ", "").replace(",", ".")
        if "k" in text:
            return int(float(text.replace("k", "")) * 1000)
        digits = "".join(c for c in text if c.isdigit())
        return int(digits) if digits else 0