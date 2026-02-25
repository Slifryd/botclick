import asyncio
import random
import logging
import re
import time
from playwright.async_api import async_playwright

# ==============================
# CONFIG
# ==============================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

URL = "https://playhyping.com/fr/vote"
PROFILES = ["Slifryd", "Leoboum"]
HEADLESS = True

VOTE_LABELS = ["VOTE #1", "VOTE #2", "VOTE #3"]


# ==============================
# HUMAN DELAY
# ==============================

async def human_delay(a=500, b=1200):
    await asyncio.sleep(random.uniform(a, b) / 1000)


# ==============================
# PARSE TIMER
# ==============================

def parse_timer(text):
    text = text.lower()

    hours = re.search(r"(\d+)h", text)
    minutes = re.search(r"(\d+)m", text)
    seconds = re.search(r"(\d+)s", text)

    total = 0
    if hours:
        total += int(hours.group(1)) * 3600
    if minutes:
        total += int(minutes.group(1)) * 60
    if seconds:
        total += int(seconds.group(1))

    return total


# ==============================
# LOGIN
# ==============================

async def login(page, username):
    log.info(f"[{username}] Connexion...")

    await page.goto(URL, wait_until="networkidle")
    await human_delay()

    invite_btn = page.locator("text=Invité")
    if await invite_btn.count() > 0:
        await invite_btn.click()
        await human_delay()

    pseudo = page.locator("input[placeholder='Entre ton pseudo ici']")
    await pseudo.fill(username)
    await human_delay()
    await pseudo.press("Enter")

    await asyncio.sleep(2)
    await page.reload(wait_until="networkidle")

    log.info(f"[{username}] Connecté ✓")


# ==============================
# ANALYSE + VOTE
# ==============================

async def analyze_vote(page, username, label):
    # Trouve le titre exact VOTE #X
    title = page.locator(f"h3:has-text('{label}')").first

    if await title.count() == 0:
        log.info(f"[{username}] {label} introuvable")
        return None

    # Remonte au bloc parent principal
    box = title.locator("xpath=ancestor::div[contains(@class,'rounded-2xl')]").first

    await box.scroll_into_view_if_needed()
    await human_delay()

    # Cherche le timer DANS CE BLOC UNIQUEMENT
    timer_element = box.locator("p:has-text('Disponible')").first

    if await timer_element.count() > 0:
        timer_text = await timer_element.inner_text()
        seconds = parse_timer(timer_text)

        log.info(
            f"[{username}] {label} → {timer_text.strip()} "
            f"({seconds} sec restantes)"
        )

        return seconds

    # 🔥 Si pas de timer → vote dispo
    try:
        await box.click()
        log.info(f"[{username}] {label} — clic effectué ✓")

        log.info(f"[{username}] Attente 30s validation...")
        await asyncio.sleep(30)

        for p in page.context.pages:
            if p != page:
                await p.close()

        return 0

    except Exception as e:
        log.warning(f"[{username}] {label} erreur clic : {e}")
        return None


# ==============================
# MAIN LOOP
# ==============================

async def vote_cycle(playwright):
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ]
    )

    while True:
        all_timers = []

        for username in PROFILES:
            log.info(f"===== TOUR DE {username} =====")

            context = await browser.new_context(locale="fr-FR")
            page = await context.new_page()

            await login(page, username)

            for label in VOTE_LABELS:
                await page.reload(wait_until="networkidle")
                await human_delay()

                result = await analyze_vote(page, username, label)

                if result and result > 0:
                    all_timers.append(result)

            await context.close()

        # 🔥 Calcul intelligent du prochain réveil
        if all_timers:
            sleep_time = min(all_timers)
        else:
            sleep_time = 300  # fallback 5 min

        log.info(f"Bot en veille pour {sleep_time} secondes")
        await asyncio.sleep(sleep_time)


# ==============================
# ENTRYPOINT
# ==============================

async def main():
    async with async_playwright() as p:
        await vote_cycle(p)


if __name__ == "__main__":
    asyncio.run(main())
