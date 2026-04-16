import sys
import json
import argparse
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

COOKIES_FILE = ROOT / "data" / "linkedin_cookies.json"


def save_cookies(context):
    cookies = context.cookies()
    COOKIES_FILE.parent.mkdir(exist_ok=True)
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f)


def load_cookies(context):
    if not COOKIES_FILE.exists():
        return False
    with open(COOKIES_FILE, "r") as f:
        cookies = json.load(f)
    context.add_cookies(cookies)
    return True


def login(page, context):
    email = os.getenv("LINKEDIN_EMAIL")
    password = os.getenv("LINKEDIN_PASSWORD")

    if "login" not in page.url:
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
        print(f"LOGIN_FAILED - URL : {page.url}")
        sys.exit(1)


def is_logged_in(page):
    url = page.url
    return "linkedin.com/feed" in url or "linkedin.com/mynetwork" in url


def open_post_modal(page):
    """Ouvre la modal en simulant un vrai clic humain."""
    try:
        btn = page.locator("[role='button']:has-text('Commencer un post')").first
        box = btn.bounding_box()
        if box:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            print(f"Coordonnees bouton : x={x} y={y}")

            # Simule un vrai mouvement de souris humain
            page.mouse.move(x - 50, y - 20)
            page.wait_for_timeout(300)
            page.mouse.move(x, y, steps=10)
            page.wait_for_timeout(300)
            page.mouse.down()
            page.wait_for_timeout(100)
            page.mouse.up()
            page.wait_for_timeout(3000)

            # Vérifie si la modal est ouverte
            editors = page.locator(".ql-editor").all()
            print(f"Editeurs apres clic : {len(editors)}")
            return len(editors) > 0
    except Exception as e:
        print(f"Erreur open_post_modal : {e}")
    return False

def find_editor(page):
    for selector in [".ql-editor", "[contenteditable='true']", "[role='textbox']"]:
        try:
            el = page.locator(selector).first
            if el.is_visible():
                print(f"Editeur trouve : {selector}")
                return el
        except:
            pass
    for frame in page.frames:
        try:
            el = frame.locator(".ql-editor").first
            if el.is_visible():
                print(f"Editeur trouve dans frame : {frame.url[:50]}")
                return el
        except:
            pass
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("content", help="Contenu du post")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=args.headless,
            args=["--disable-web-security", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(60000)

        load_cookies(context)

        try:
            page.goto("https://www.linkedin.com/feed/", timeout=60000)
        except PlaywrightTimeout:
            page.goto("https://www.linkedin.com/feed/", timeout=60000)

        page.wait_for_timeout(4000)

        if not is_logged_in(page):
            print("Lancement login...")
            login(page, context)
            page.goto("https://www.linkedin.com/feed/", timeout=60000)
            page.wait_for_timeout(4000)

        print(f"URL : {page.url}")

        # Ouvre la modal
        print("Ouverture modal...")
        open_post_modal(page)
        page.wait_for_timeout(3000)


        editor = find_editor(page)

        if editor is None:
            print("EDITOR_NOT_FOUND")
            browser.close()
            sys.exit(1)

        print("Editeur trouve - remplissage...")
        editor.click()
        page.wait_for_timeout(500)

        # Colle le contenu via le presse-papier
        page.evaluate(f"navigator.clipboard.writeText({json.dumps(args.content)})")
        page.keyboard.press("Control+v")
        page.wait_for_timeout(1000)


        # Screenshot APRES remplissage
        page.screenshot(path=str(ROOT / "debug_after_click.png"))
        print("Screenshot sauvegarde")

        if args.dry_run:
            print("DRY_RUN_OK")
            page.wait_for_timeout(3000)
            browser.close()
            sys.exit(0)

        publish_button = page.locator("button:has-text('Publier'), button:has-text('Post')")
        publish_button.last.click()
        page.wait_for_timeout(3000)
        print("PUBLISH_OK")
        browser.close()


if __name__ == "__main__":
    main()
