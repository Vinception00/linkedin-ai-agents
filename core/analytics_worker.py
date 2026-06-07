"""
Worker subprocess pour le scraping analytics LinkedIn.
Lancé via subprocess pour isoler Playwright de l'event loop Streamlit.

Usage :
  python analytics_worker.py sync --username prenom-nom-123
  python analytics_worker.py scrape --url https://... --post_id 1
"""

import sys
import json
import re
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

COOKIES_FILE = ROOT / "data" / "linkedin_cookies.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def load_cookies(context) -> bool:
    if not COOKIES_FILE.exists():
        return False
    with open(COOKIES_FILE) as f:
        context.add_cookies(json.load(f))
    return True


def is_logged_in(page) -> bool:
    return any(k in page.url for k in ["linkedin.com/feed", "linkedin.com/in/", "linkedin.com/posts"])


def parse_number(text: str) -> int:
    if not text:
        return 0
    text = text.replace(" ", "").replace(" ", "").replace(" ", "")
    text = text.lower().replace(",", ".")
    if "k" in text:
        try:
            return int(float(text.replace("k", "")) * 1000)
        except ValueError:
            pass
    digits = "".join(c for c in text if c.isdigit())
    return int(digits) if digits else 0


def cmd_sync(args):
    """Scrape tous les posts depuis /in/{username}/recent-activity/all/"""
    activity_url = f"https://www.linkedin.com/in/{args.username}/recent-activity/all/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(30000)

        load_cookies(context)
        page.goto(activity_url, timeout=60000)
        page.wait_for_timeout(4000)

        if not is_logged_in(page):
            print("ERROR:cookies_expired")
            browser.close()
            sys.exit(1)

        cards = page.locator('[data-urn*="activity"]').all()
        print(f"CARDS:{len(cards)}", flush=True)

        results = []
        for card in cards:
            try:
                urn = card.get_attribute("data-urn") or ""
                m = re.search(r"activity:(\d+)", urn)
                if not m:
                    continue

                activity_id = m.group(1)

                impressions = 0
                stats_link = card.locator('a:has-text("Voir les statistiques")').first
                if stats_link.count() > 0:
                    first_line = stats_link.inner_text().split("\n")[0].strip()
                    impressions = parse_number(first_line)

                likes = 0
                reaction_btn = card.locator('button[aria-label*="personnes"]').first
                if reaction_btn.count() > 0:
                    btn_text = reaction_btn.inner_text().split("\n")[0].strip()
                    likes = parse_number(btn_text)

                commentaires = 0
                for csel in ['button[aria-label*="commentaire"]', 'button[aria-label*="comment"]']:
                    cel = card.locator(csel).first
                    if cel.count() > 0:
                        n = parse_number(cel.get_attribute("aria-label") or "")
                        if n > 0:
                            commentaires = n
                            break

                post_preview = ""
                for tsel in [".update-components-text", ".feed-shared-update-v2__description", ".break-words"]:
                    el = card.locator(tsel).first
                    if el.count() > 0:
                        post_preview = el.inner_text().strip()[:200]
                        if post_preview:
                            break

                results.append({
                    "activity_id": activity_id,
                    "likes": likes,
                    "commentaires": commentaires,
                    "impressions": impressions,
                    "preview": post_preview,
                })
            except Exception as e:
                print(f"CARD_ERROR:{e}", flush=True)

        browser.close()

    print(f"RESULTS:{json.dumps(results)}", flush=True)


def cmd_scrape(args):
    """Scrape les stats depuis l'URL directe d'un post."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(30000)

        load_cookies(context)
        page.goto(args.url, timeout=60000)
        page.wait_for_timeout(4000)

        if not is_logged_in(page):
            print("ERROR:cookies_expired")
            browser.close()
            sys.exit(1)

        likes = 0
        btn = page.locator('button[aria-label*="personnes"]').first
        if btn.count() > 0:
            likes = parse_number(btn.inner_text().split("\n")[0].strip())

        vues = 0
        stats_link = page.locator('a:has-text("Voir les statistiques")').first
        if stats_link.count() > 0:
            vues = parse_number(stats_link.inner_text().split("\n")[0].strip())
        else:
            for sel in ['span:has-text("impressions")', 'span:has-text("Impressions")', "strong"]:
                el = page.locator(sel).first
                if el.count() > 0:
                    v = parse_number(el.inner_text().split("\n")[0].strip())
                    if v > 0:
                        vues = v
                        break

        commentaires = 0
        for csel in ['button[aria-label*="commentaire"]', 'button[aria-label*="comment"]']:
            el = page.locator(csel).first
            if el.count() > 0:
                n = parse_number(el.get_attribute("aria-label") or "")
                if n > 0:
                    commentaires = n
                    break

        browser.close()

    stats = {"likes": likes, "commentaires": commentaires, "vues": vues}
    print(f"STATS:{json.dumps(stats)}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)

    p_sync = sub.add_parser("sync")
    p_sync.add_argument("--username", required=True)

    p_scrape = sub.add_parser("scrape")
    p_scrape.add_argument("--url", required=True)
    p_scrape.add_argument("--post_id", type=int, required=True)

    args = parser.parse_args()

    if args.mode == "sync":
        cmd_sync(args)
    elif args.mode == "scrape":
        cmd_scrape(args)
