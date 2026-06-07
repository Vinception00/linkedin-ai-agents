"""
Worker Playwright pour la recherche de profils LinkedIn.
Lancé en subprocess par LinkedInSearcher pour isoler la boucle d'événements.
"""
import sys
import json
import argparse
import os
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

COOKIES_FILE = ROOT / "data" / "linkedin_cookies.json"

DEGREE_CODES = {"1": '"F"', "2": '"S"', "3": '"O"'}


def save_cookies(context):
    cookies = context.cookies()
    COOKIES_FILE.parent.mkdir(exist_ok=True)
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f)


def load_cookies(context):
    if not COOKIES_FILE.exists():
        return False
    with open(COOKIES_FILE) as f:
        context.add_cookies(json.load(f))
    return True


def login(page, context):
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    page.goto("https://www.linkedin.com/login", timeout=60000)
    page.wait_for_selector("#username, input[name='session_key']", timeout=15000)
    page.locator("#username, input[name='session_key']").first.fill(email)
    page.locator("#password, input[name='session_password']").first.fill(password)
    page.locator("button[type='submit']").first.click()

    try:
        page.wait_for_url("**/feed/**", timeout=20000)
        save_cookies(context)
        print("LOGIN_OK")
    except PlaywrightTimeout:
        print(f"LOGIN_FAILED: {page.url}")
        sys.exit(1)


def is_logged_in(page):
    return "linkedin.com/feed" in page.url or "linkedin.com/mynetwork" in page.url


def extract_profiles(page, max_results: int) -> list:
    profiles = []

    # Attend les résultats
    try:
        page.wait_for_selector(
            ".reusable-search__result-container, .search-results-container",
            timeout=15000
        )
    except PlaywrightTimeout:
        print("WARN: sélecteur résultats introuvable")
        return profiles

    page.wait_for_timeout(2000)

    cards = page.locator(".reusable-search__result-container").all()
    print(f"Cards trouvées : {len(cards)}")

    for card in cards[:max_results]:
        try:
            profile = {}

            # Nom — plusieurs sélecteurs de fallback
            for name_sel in [
                ".app-aware-link span[aria-hidden='true']",
                ".entity-result__title-text a span[aria-hidden='true']",
                ".entity-result__title-text span:not(.visually-hidden)"
            ]:
                el = card.locator(name_sel).first
                if el.count() > 0 and el.is_visible():
                    profile["nom"] = el.text_content().strip()
                    break

            if not profile.get("nom"):
                continue

            # Titre professionnel
            for title_sel in [
                ".entity-result__primary-subtitle",
                ".entity-result__summary"
            ]:
                el = card.locator(title_sel).first
                if el.count() > 0:
                    profile["titre"] = el.text_content().strip()
                    break
            else:
                profile["titre"] = ""

            # Entreprise / localisation
            el = card.locator(".entity-result__secondary-subtitle").first
            profile["entreprise"] = el.text_content().strip() if el.count() > 0 else ""

            # URL du profil
            link = card.locator("a.app-aware-link").first
            if link.count() > 0:
                href = link.get_attribute("href") or ""
                profile["url"] = href.split("?")[0]
            else:
                profile["url"] = ""

            profiles.append(profile)

        except Exception as e:
            print(f"Erreur extraction card : {e}")
            continue

    return profiles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", required=True, help="Mots-clés de recherche")
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--degree", default="2", choices=["1", "2", "3"],
                        help="Degré de connexion (1=1er, 2=2ème, 3=3ème+)")
    args = parser.parse_args()

    degree_code = DEGREE_CODES.get(args.degree, '"S"')
    encoded_kw = quote(args.keywords)
    search_url = (
        f"https://www.linkedin.com/search/results/people/"
        f"?keywords={encoded_kw}"
        f"&network=%5B{degree_code}%5D"
        f"&origin=FACETED_SEARCH"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-web-security", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.set_default_timeout(60000)

        load_cookies(context)

        try:
            page.goto("https://www.linkedin.com/feed/", timeout=60000)
        except PlaywrightTimeout:
            pass
        page.wait_for_timeout(3000)

        if not is_logged_in(page):
            print("Lancement login...")
            login(page, context)
            page.goto("https://www.linkedin.com/feed/", timeout=60000)
            page.wait_for_timeout(3000)

        print(f"Recherche : {search_url}")
        page.goto(search_url, timeout=60000)
        page.wait_for_timeout(3000)

        profiles = extract_profiles(page, args.max_results)
        browser.close()

        print(f"RESULTS:{json.dumps(profiles, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
