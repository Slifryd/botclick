import asyncio
import random
import logging
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
import json
import os, tempfile
async def inject_nopecha_settings(context, api_key):
    settings = json.load(open("nopecha_settings.json"))
    settings["keys"] = api_key  # injecte la clé API

    # Ouvre une page sur l'extension pour injecter dans son localStorage
    ext_page = await context.new_page()
    await ext_page.goto(f"chrome-extension://dknlfmjaanfblgfdfebhijalfmhmjjjo/index.html")
    
    await ext_page.evaluate(f"""
        () => {{
            const settings = {json.dumps(settings)};
            for (const [key, value] of Object.entries(settings)) {{
                localStorage.setItem(key, JSON.stringify(value));
            }}
        }}
    """)
    
    await ext_page.close()
    log.info("NopeCHA settings injectés ✓")
# ==============================
# CONFIG
# ==============================

URL = "https://playhyping.com/fr/vote"
PROFILES = [
    {"username": "Slifryd", "proxy": None},
    {"username": "Leoboum", "proxy": {
        "server": "http://104.238.30.63:63744",
    }},
]
HEADLESS = True

VOTE_LABELS = ["VOTE #1", "VOTE #2", "VOTE #3"]

START_HOUR = 6
STOP_HOUR = 2

NOPECHA_EXT_PATH = "./0.5.5_0"

# ==============================
# CONFIG SITES
# ==============================

SITES_CONFIG = {
    "playhyping": {
        "keywords": ["playhyping.com"],
    },
    "generic": {
        "keywords": [],
        "selectors": ["button", "a.btn", "[role='button']"],
        "wait_time": 2,
    },
    "serveursminecraft-org": {
        "keywords": ["serveursminecraft.org"],
        "wait_time": 5,
        "open_vote_button": "a.btn.btn-success[data-target='#vote']",
        "confirm_button": "input.btn.btn-success[value='Confirmer le vote']",
        "wait_before_confirm": 45,
    },
    "serveur-prive": {
        "keywords": ["serveur-prive.net"],
        "input_field": "#username",
        "submit_button": "#voteBtn",
        "wait_time": 2,
        "is_form": True,
        "wait_before_submit": 20,
    },
    "serveursminecraft": {
        "keywords": ["serveur-minecraft.com"],
        "input_field": "#form_username",
        "submit_button": "button[type='submit'].btn.btn-info",
        "wait_time": 3,
        "is_form": True,
        "wait_before_submit": 45,
    },
    "top-serveurs": {
        "keywords": ["top-serveurs.net"],
        "input_field": "#playername",
        "submit_button": "span.btn-content",
        "wait_time": 2,
        "wait_before_click": 10,
        "is_form": True,
    }
}

# ==============================
# LOGGING
# ==============================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ==============================
# UTILS
# ==============================

def parse_timer(text):
    text = text.lower()
    hours = re.search(r"(\d+)h", text)
    minutes = re.search(r"(\d+)m", text)
    seconds = re.search(r"(\d+)s", text)
    total = 0
    if hours: total += int(hours.group(1)) * 3600
    if minutes: total += int(minutes.group(1)) * 60
    if seconds: total += int(seconds.group(1))
    return total

def detect_site(url):
    url_lower = url.lower()
    for site_name, config in SITES_CONFIG.items():
        if site_name != "generic":
            for keyword in config["keywords"]:
                if keyword in url_lower:
                    return site_name
    return "generic"

def is_allowed_hour():
    now = datetime.now()
    h = now.hour
    if START_HOUR < STOP_HOUR:
        return START_HOUR <= h < STOP_HOUR
    else:
        return h >= START_HOUR or h < STOP_HOUR

def seconds_until_start():
    now = datetime.now()
    start = now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
    if now >= start:
        start += timedelta(days=1)
    return int((start - now).total_seconds())

# ==============================
# POPUP HANDLER
# ==============================

async def handle_popup_clicks(popup, username, site_name):
    config = SITES_CONFIG.get(site_name, SITES_CONFIG["generic"])
    log.info(f"[{username}] Popup : {site_name} ({popup.url})")
    # ===== SERVEURSMINECRAFT.ORG =====
    if site_name == "serveursminecraft-org":
        log.info(f"[{username}] Ouverture modale vote serveursminecraft.org")

        # 1. clic sur "Voter pour HYPING"
        open_btn = popup.locator(config["open_vote_button"])
        await open_btn.wait_for(state="visible", timeout=15000)
        await open_btn.click()
        log.info(f"[{username}] ✓ Bouton vote cliqué")

        # 2. attendre que NopeCHA résolve le captcha
        wait_time = config.get("wait_before_confirm", 45)
        log.info(f"[{username}] Attente captcha {wait_time}s...")
        await asyncio.sleep(wait_time)

        # 3. clic sur "Confirmer le vote"
        confirm_btn = popup.locator(config["confirm_button"])
        await confirm_btn.wait_for(state="visible", timeout=15000)
        await confirm_btn.click()
        log.info(f"[{username}] ✓ Vote confirmé sur serveursminecraft.org")

        try:
            await popup.wait_for_close(timeout=60000)
        except:
            pass

        return True
    try:
        await asyncio.sleep(config.get("wait_time", 2))

        # ===== FORM SITES =====
        if config.get("is_form"):
            log.info(f"[{username}] Remplissage formulaire sur {site_name}")

            await popup.evaluate(
                """(data) => {
                    const el = document.querySelector(data.selector);
                    if (el) {
                        el.value = data.value;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""",
                {
                    "selector": config["input_field"],
                    "value": username
                }
            )

            wait_before = config.get("wait_before_submit", config.get("wait_before_click", 0))
            if wait_before > 0:
                log.info(f"[{username}] Attente captcha {wait_before}s...")
                await asyncio.sleep(wait_before)

            submit_btn = popup.locator(config["submit_button"])
            if await submit_btn.count() > 0:
                await submit_btn.click()
                log.info(f"[{username}] ✓ Vote soumis sur {site_name}")

                try:
                    await popup.wait_for_close(timeout=60000)
                except:
                    pass

                return True

        # ===== GENERIC CLICK (VISIBLE ONLY) =====
        for selector in config.get("selectors", []):
            elements = popup.locator(selector)
            count = await elements.count()

            for i in range(count):
                el = elements.nth(i)
                if await el.is_visible():
                    await el.click()
                    log.info(f"[{username}] ✓ Clic générique visible")
                    return True

        return False

    except Exception as e:
        log.warning(f"[{username}] Erreur popup : {e}")
        return False

async def process_all_popups(page, username):
    tasks = []

    def popup_handler(popup):
        site_name = detect_site(popup.url)
        task = asyncio.create_task(handle_popup_clicks(popup, username, site_name))
        tasks.append(task)

    page.on("popup", popup_handler)
    return tasks

# ==============================
# LOGIN
# ==============================

async def login(page, username):
    log.info(f"[{username}] Connexion...")

    await page.goto(URL, wait_until="networkidle")

    for name in ["Invité", "Leoboum", "Slifryd"]:
        try:
            locator = page.locator("main").get_by_text(name, exact=True)
            if await locator.count() > 0:
                await locator.click()
        except Exception as e:
            log.warning(f"[{username}] Impossible de cliquer sur '{name}': {e}")

    pseudo = page.locator("input[placeholder='Entre ton pseudo ici']")
    await pseudo.fill(username)

    await pseudo.press("Enter")

    await asyncio.sleep(2)
    await page.reload(wait_until="networkidle")

    log.info(f"[{username}] Connecté ✓")

# ==============================
# CHECK & VOTE
# ==============================

async def check_vote(page, username, label):
    box = page.locator("div.rounded-2xl").filter(has_text=label).first

    if await box.count() == 0:
        return None

    timer = box.locator("p:has-text('Disponible')")
    if await timer.count() > 0:
        text = await timer.inner_text()
        seconds = parse_timer(text)
        log.info(f"[{username}] {label} → {text.strip()}")
        return seconds

    log.info(f"[{username}] {label} DISPONIBLE → vote")

    popup_tasks = await process_all_popups(page, username)

    bounding = await box.bounding_box()
    x = bounding["x"] + bounding["width"] / 2
    y = bounding["y"] + bounding["height"] / 2
    await page.mouse.click(x, y)

    for _ in range(10):
        await asyncio.sleep(0.5)
        if popup_tasks:
            break

    if popup_tasks:
        await asyncio.wait_for(asyncio.gather(*popup_tasks), timeout=120)

    return 0

# ==============================
# MAIN
# ==============================
NOPECHA_API_KEY = os.environ.get("NOPECHA_API_KEY", "")
async def vote_cycle(playwright):
    args = [
        f"--disable-extensions-except={NOPECHA_EXT_PATH}",
        f"--load-extension={NOPECHA_EXT_PATH}",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]

    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=os.path.join(tempfile.gettempdir(), "test_ext"),
        headless=HEADLESS,
        args=args,
    )

    await asyncio.sleep(3)

    for bg in context.background_pages:
        log.info(f">>> EXTENSION ID : {bg.url}")

    await context.close()
async def main():
    async with async_playwright() as p:
        await vote_cycle(p)

if __name__ == "__main__":
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
