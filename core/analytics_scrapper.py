import json
import re
import sys
import subprocess
from pathlib import Path
from data.posts_db import PostsDB
from core.logger import get_logger

logger = get_logger("core.analytics_scraper")

WORKER = Path(__file__).parent / "analytics_worker.py"
ROOT = Path(__file__).parent.parent


class AnalyticsScraper:

    def __init__(self):
        self.db = PostsDB()
        logger.info("AnalyticsScraper initialisé")

    def _run_worker(self, args: list[str], timeout: int = 120) -> str:
        """Lance analytics_worker.py en subprocess et retourne stdout."""
        cmd = [sys.executable, str(WORKER)] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(ROOT),
            )
            if result.returncode != 0:
                logger.error(f"Worker erreur (rc={result.returncode}) : {result.stderr[:500]}")
            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error("Worker timeout")
            return ""
        except Exception as e:
            logger.error(f"Worker lancement impossible : {e}")
            return ""

    # ── Méthode principale : sync depuis la page d'activité ──────────────────

    def sync_from_activity_page(self, username: str) -> int:
        """
        Scrape tous les posts depuis /in/{username}/recent-activity/all/.
        Retourne le nombre de posts mis à jour en base.
        """
        logger.info(f"Sync activité pour username={username}")
        output = self._run_worker(["sync", "--username", username])

        if "ERROR:cookies_expired" in output:
            raise RuntimeError("Cookies LinkedIn expirés — reconnecte-toi via login.py")

        results_line = next((l for l in output.splitlines() if l.startswith("RESULTS:")), None)
        if not results_line:
            logger.error(f"Aucun RESULTS dans la sortie worker : {output[:300]}")
            raise RuntimeError("Le worker n'a retourné aucun résultat. Vérifie les cookies.")

        cards = json.loads(results_line[8:])
        logger.info(f"{len(cards)} cards reçues du worker")

        db_posts = self.db.get_all_posts()
        updated = 0

        for card in cards:
            activity_id = card["activity_id"]
            post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/"
            matched = self._match_db_post(db_posts, activity_id, card.get("preview", ""))

            if matched:
                if not matched.get("url"):
                    self.update_post_url(matched["id"], post_url)
                self.db.save_stats(
                    matched["id"],
                    card["likes"],
                    card["commentaires"],
                    0,
                    card["impressions"],
                )
                updated += 1
                logger.info(
                    f"Post #{matched['id']} sync : {card['likes']} likes, "
                    f"{card['commentaires']} commentaires, {card['impressions']} impressions"
                )
            else:
                logger.info(f"Aucun post DB correspondant à activity:{activity_id}")

        return updated

    # ── Scraping par URL directe ──────────────────────────────────────────────

    def scrape_post_stats(self, post_url: str, post_id: int, debug: bool = False):
        """Scrape les stats depuis l'URL directe du post."""
        logger.info(f"Scraping post_id={post_id}")
        output = self._run_worker(["scrape", "--url", post_url, "--post_id", str(post_id)])

        if "ERROR:cookies_expired" in output:
            raise RuntimeError("Cookies LinkedIn expirés — reconnecte-toi via login.py")

        stats_line = next((l for l in output.splitlines() if l.startswith("STATS:")), None)
        if not stats_line:
            logger.error(f"Aucun STATS dans la sortie worker : {output[:300]}")
            raise RuntimeError("Le worker n'a retourné aucun résultat. Vérifie les cookies.")

        stats = json.loads(stats_line[6:])
        likes = stats.get("likes", 0)
        commentaires = stats.get("commentaires", 0)
        vues = stats.get("vues", 0)

        logger.info(f"Stats post {post_id} : {likes} likes, {commentaires} commentaires, {vues} vues")
        self.db.save_stats(post_id, likes, commentaires, 0, vues)

    def scrape_all_posts(self, debug: bool = False):
        posts = [p for p in self.db.get_all_posts() if p.get("url")]
        if not posts:
            logger.info("Aucun post avec URL")
            return
        logger.info(f"Scraping {len(posts)} posts...")
        for post in posts:
            self.scrape_post_stats(post["url"], post["id"], debug=debug)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _match_db_post(self, db_posts: list, activity_id: str, preview: str) -> dict | None:
        for p in db_posts:
            if activity_id in (p.get("url") or ""):
                return p

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
