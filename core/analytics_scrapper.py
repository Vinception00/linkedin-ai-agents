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

    def __init__(self):
        self.db = PostsDB()
        logger.info("AnalyticsScraper initialisé")

    def _load_cookies(self, context) -> bool:
        if not COOKIES_FILE.exists():
            return False
        with open(COOKIES_FILE) as f:
            context.add_cookies(json.load(f))
        return True

    def _is_logged_in(self, page) -> bool:
        url = page.url
        return any(k in url for k in ["linkedin.com/feed", "linkedin.com/in/", "linkedin.com/posts"])

    def _parse_number(self, text: str) -> int:
        if not text:
            return 0
        # Retire les espaces insécables (U+202F, U+00A0) et normaux
        text = text.replace(" ", "").replace(" ", "").replace(" ", "")
        text = text.lower().replace(",", ".")
        if "k" in text:
            try:
                return int(float(text.replace("k", "")) * 1000)
            except ValueError:
                pass
        digits = "".join(c for c in text if c.isdigit())
        return int(digits) if digits else 0

    # ── Méthode principale : scrape depuis la page d'activité du profil ──────

    def sync_from_activity_page(self, username: str) -> int:
        """
        Scrape tous les posts depuis /in/{username}/recent-activity/all/
        Une seule navigation, récupère URLs + réactions + impressions.

        Returns:
            Nombre de posts mis à jour en base
        """
        activity_url = f"https://www.linkedin.com/in/{username}/recent-activity/all/"
        updated = 0

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.set_default_timeout(30000)

            self._load_cookies(context)
            page.goto(activity_url, timeout=60000)
            page.wait_for_timeout(4000)

            if not self._is_logged_in(page):
                logger.error("Cookies expirés — sync impossible")
                browser.close()
                return 0

            db_posts = self.db.get_all_posts()
            cards = page.locator('[data-urn*="activity"]').all()
            logger.info(f"{len(cards)} posts sur la page d'activité, {len(db_posts)} en DB")

            for card in cards:
                try:
                    urn = card.get_attribute("data-urn") or ""
                    m = re.search(r"activity:(\d+)", urn)
                    if not m:
                        continue

                    activity_id = m.group(1)
                    post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/"

                    # Impressions : dans le lien "Voir les statistiques"
                    impressions = 0
                    stats_link = card.locator('a:has-text("Voir les statistiques")').first
                    if stats_link.count() > 0:
                        first_line = stats_link.inner_text().split("\n")[0].strip()
                        impressions = self._parse_number(first_line)

                    # Réactions : bouton avec aria-label contenant "personnes"
                    likes = 0
                    reaction_btn = card.locator('button[aria-label*="personnes"]').first
                    if reaction_btn.count() > 0:
                        btn_text = reaction_btn.inner_text().split("\n")[0].strip()
                        likes = self._parse_number(btn_text)

                    # Commentaires
                    commentaires = 0
                    for csel in ['button[aria-label*="commentaire"]', 'button[aria-label*="comment"]']:
                        cel = card.locator(csel).first
                        if cel.count() > 0:
                            n = self._parse_number(cel.get_attribute("aria-label") or "")
                            if n > 0:
                                commentaires = n
                                break

                    # Texte du post pour le matching
                    post_preview = ""
                    for tsel in [
                        ".update-components-text",
                        ".feed-shared-update-v2__description",
                        ".break-words",
                    ]:
                        el = card.locator(tsel).first
                        if el.count() > 0:
                            post_preview = el.inner_text().strip()[:200]
                            if post_preview:
                                break

                    matched = self._match_db_post(db_posts, activity_id, post_preview)
                    if matched:
                        if not matched.get("url"):
                            self.update_post_url(matched["id"], post_url)
                        self.db.save_stats(matched["id"], likes, commentaires, 0, impressions)
                        updated += 1
                        logger.info(
                            f"Post #{matched['id']} sync : {likes} likes, "
                            f"{commentaires} commentaires, {impressions} impressions"
                        )
                    else:
                        logger.info(f"Aucun post DB correspondant à activity:{activity_id}")

                except Exception as e:
                    logger.error(f"Erreur sync card : {e}")

            browser.close()

        return updated

    def _match_db_post(self, db_posts: list, activity_id: str, preview: str) -> dict | None:
        # 1. Match par activity_id déjà dans l'URL stockée
        for p in db_posts:
            if activity_id in (p.get("url") or ""):
                return p

        # 2. Match par similarité de texte (Jaccard sur les mots)
        if preview:
            preview_norm = re.sub(r"\s+", " ", preview.lower())[:150]
            preview_words = set(preview_norm.split())
            best, best_score = None, 0.0
            for p in db_posts:
                content_norm = re.sub(r"\s+", " ", p["contenu"].lower())[:150]
                content_words = set(content_norm.split())
                if preview_words and content_words:
                    union = preview_words | content_words
                    score = len(preview_words & content_words) / len(union)
                    if score > best_score:
                        best_score = score
                        best = p
            if best_score > 0.25:
                return best

        return None

    # ── Scraping par URL de post (fallback si pas de username) ───────────────

    def scrape_post_stats(self, post_url: str, post_id: int, debug: bool = False):
        """Scrape les stats depuis l'URL directe du post."""
        logger.info(f"Scraping post_id={post_id}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.set_default_timeout(30000)
            self._load_cookies(context)

            try:
                page.goto(post_url, timeout=60000)
                page.wait_for_timeout(4000)

                if not self._is_logged_in(page):
                    logger.warning("Cookies expirés — scraping impossible")
                    return

                if debug:
                    p_debug = DEBUG_DIR / f"analytics_debug_{post_id}.png"
                    page.screenshot(path=str(p_debug), full_page=True)
                    logger.info(f"Screenshot : {p_debug}")

                # Réactions : bouton "X\nPaul Vibert et N autres personnes"
                likes = 0
                btn = page.locator('button[aria-label*="personnes"]').first
                if btn.count() > 0:
                    likes = self._parse_number(btn.inner_text().split("\n")[0].strip())

                # Impressions : lien "Voir les statistiques"
                vues = 0
                stats_link = page.locator('a:has-text("Voir les statistiques")').first
                if stats_link.count() > 0:
                    vues = self._parse_number(stats_link.inner_text().split("\n")[0].strip())
                else:
                    # Fallback span impressions
                    for sel in ['span:has-text("impressions")', 'span:has-text("Impressions")', "strong"]:
                        el = page.locator(sel).first
                        if el.count() > 0:
                            v = self._parse_number(el.inner_text().split("\n")[0].strip())
                            if v > 0:
                                vues = v
                                break

                # Commentaires
                commentaires = 0
                for csel in ['button[aria-label*="commentaire"]', 'button[aria-label*="comment"]']:
                    el = page.locator(csel).first
                    if el.count() > 0:
                        n = self._parse_number(el.get_attribute("aria-label") or "")
                        if n > 0:
                            commentaires = n
                            break

                logger.info(f"Stats post {post_id} : {likes} likes, {commentaires} commentaires, {vues} vues")
                self.db.save_stats(post_id, likes, commentaires, 0, vues)

            except Exception as e:
                logger.error(f"Erreur scraping : {e}")
                if debug:
                    try:
                        page.screenshot(path=str(DEBUG_DIR / f"analytics_error_{post_id}.png"))
                    except Exception:
                        pass
            finally:
                browser.close()

    def scrape_all_posts(self, debug: bool = False):
        posts = [p for p in self.db.get_all_posts() if p.get("url")]
        if not posts:
            logger.info("Aucun post avec URL")
            return
        logger.info(f"Scraping {len(posts)} posts...")
        for post in posts:
            self.scrape_post_stats(post["url"], post["id"], debug=debug)

    def update_post_url(self, post_id: int, url: str):
        self.db.conn.execute("UPDATE posts SET url = ? WHERE id = ?", (url, post_id))
        self.db.conn.commit()
        logger.info(f"URL mise à jour post_id={post_id} : {url}")

    def extract_username_from_db(self) -> str | None:
        """Extrait le username LinkedIn depuis les URLs stockées en base."""
        posts = self.db.get_all_posts()
        for p in posts:
            url = p.get("url") or ""
            m = re.search(r"linkedin\.com/(?:posts|in)/([^/_?]+)", url)
            if m:
                return m.group(1)
        return None
