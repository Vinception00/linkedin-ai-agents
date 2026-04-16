import sys
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv(".env")

COOKIES_FILE = Path("data/linkedin_cookies.json")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    with open(COOKIES_FILE) as f:
        context.add_cookies(json.load(f))

    page.goto("https://www.linkedin.com/feed/")
    page.wait_for_timeout(3000)

    input("Clique sur Commencer un post dans le navigateur, puis appuie sur Entree ici...")

    print(f"URL : {page.url}")

    editors = page.locator("[contenteditable], .ql-editor, [role='textbox']").all()
    print(f"Editeurs trouves : {len(editors)}")
    for e in editors:
        print(f"  tag={e.evaluate('el => el.tagName')} class={e.get_attribute('class')} visible={e.is_visible()}")

    input("Entree pour fermer...")
    browser.close()