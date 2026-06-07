"""
Worker Playwright pour la recherche de profils LinkedIn.
Lancé en subprocess par LinkedInSearcher pour isoler la boucle d'événements.
"""
import sys
import json
import argparse
import re
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


def is_logged_in(page):
    return "linkedin.com/feed" in page.url or "linkedin.com/mynetwork" in page.url


def extract_profiles(page, max_results: int) -> list:
    """
    LinkedIn utilise des class names obfusqués — on s'appuie sur les liens /in/
    dont le inner_text est long et contient des double-sauts (card complète).
    Structure : "Nom [· 2e]\n\nTitre\n\nLieu\n\nSe connecter\n\n..."
    """
    page.wait_for_timeout(3000)

    links = page.locator('a[href*="/in/"]').all()
    print(f"Total liens /in/ : {len(links)}", flush=True)

    profiles = []
    seen_urls = set()

    for link in links:
        if len(profiles) >= max_results:
            break
        try:
            href = (link.get_attribute("href") or "").split("?")[0].rstrip("/")
            if not href or href in seen_urls:
                continue
            if not re.search(r"/in/[^/]+", href):
                continue

            text = link.inner_text().strip()
            # Les cartes de profil sont longues et ont des double-sauts de ligne
            if "\n\n" not in text or len(text) < 40:
                continue

            # Split sur double saut — chaque bloc est une section de la carte
            sections = [s.strip() for s in text.split("\n\n") if s.strip()]
            if len(sections) < 2:
                continue

            # Section 0 : "Nom [badge newline] · 2e" ou "Nom · 2e"
            # Prend la première ligne non-vide de la section, avant tout "·"
            first_line = sections[0].split("\n")[0].strip()
            # Enlève le marqueur de degré (· 2e, · 1er, etc.) s'il est sur la même ligne
            name_part = re.split(r"\s*[·•]\s*\d", first_line)[0].strip()
            if not name_part or len(name_part) < 2:
                continue

            # Section 1 : titre professionnel
            titre = sections[1] if len(sections) > 1 else ""
            titre = re.sub(r"^Poste[s]?\s+(?:actuel|précédents?)\s*:?\s*", "", titre).strip()

            # Section 2 : lieu/entreprise (skip "Se connecter")
            SKIP = {"se connecter", "follow", "message", "pending"}
            entreprise = ""
            for sec in sections[2:4]:
                if sec.lower() not in SKIP:
                    entreprise = sec
                    break

            seen_urls.add(href)
            profiles.append({
                "nom": name_part,
                "titre": titre,
                "entreprise": entreprise,
                "url": href,
            })
            print(f"  Profil : {name_part} — {titre[:50]}", flush=True)

        except Exception as e:
            print(f"Erreur extraction lien : {e}", flush=True)

    return profiles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", required=True)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--degree", default="2", choices=["1", "2", "3"])
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
        browser = p.chromium.launch(headless=True, args=["--disable-web-security", "--no-sandbox"])
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
            import os
            email = os.getenv("LINKEDIN_EMAIL")
            password = os.getenv("LINKEDIN_PASSWORD")
            page.goto("https://www.linkedin.com/login", timeout=60000)
            page.wait_for_selector("#username", timeout=15000)
            page.fill("#username", email)
            page.fill("#password", password)
            page.click("button[type='submit']")
            try:
                page.wait_for_url("**/feed/**", timeout=20000)
                save_cookies(context)
            except PlaywrightTimeout:
                print(f"LOGIN_FAILED: {page.url}")
                browser.close()
                sys.exit(1)

        print(f"Recherche : {search_url}", flush=True)
        page.goto(search_url, timeout=60000)
        page.wait_for_timeout(4000)

        profiles = extract_profiles(page, args.max_results)
        browser.close()

    print(f"RESULTS:{json.dumps(profiles, ensure_ascii=False)}", flush=True)


if __name__ == "__main__":
    main()
