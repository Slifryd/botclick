import asyncio
import random
import logging
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# ==============================
# CONFIG
# ==============================

URL = "https://playhyping.com/fr/vote"
PROFILES = ["Slifryd", "Leoboum"]
HEADLESS = True

VOTE_LABELS = ["VOTE #1", "VOTE #2", "VOTE #3"]

START_HOUR = 6     # Autorisé à partir de 06:00
STOP_HOUR = 2      # Stop à 02:00 (le lendemain)

# ==============================
# LOGGING
# ==============================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ==============================
# HORAIRES
# ==============================

def is_allowed_hour():
    now = datetime.now()
    h = now.hour

    if START_HOUR < STOP_HOUR:
        return START_HOUR <= h < STOP_HOUR
    else:
        # passe minuit
        return h >= START_HOUR or h < STOP_HOUR


def seconds_until_start():
    now = datetime.now()

    if START_HOUR < STOP_HOUR:
        start = now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
        if now >= start:
            start += timedelta(days=1)
    else:
        if now.hour < STOP_HOUR:
            return 0
        start = now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
        if now >= start:
            start += timedelta(days=1)

    return int((start - now).total_seconds())

# ==============================
# UTILS
# ==============================

async def human_delay(a=500, b=1200):
    await asyncio.sleep(random.uniform(a, b) / 1000)


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

    invite = page.locator("text=Invité")
    if await invite.count() > 0:
        await invite.click()
        await human_delay()

    pseudo = page.locator("input[placeholder='Entre ton pseudo ici']")
    await pseudo.fill(username)
    await human_delay()
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
        log.info(f"[{username}] {label} introuvable")
        return None

    await box.scroll_into_view_if_needed()
    await human_delay()

    # Cherche timer
    timer = box.locator("p:has-text('Disponible')")

    if await timer.count() > 0:
        text = await timer.inner_text()
        seconds = parse_timer(text)

        log.info(
            f"[{username}] {label} → {text.strip()} "
            f"({seconds} sec restantes)"
        )

        return seconds

    # 🔥 Vote dispo
    try:
        log.info(f"[{username}] {label} DISPONIBLE → vote")

        box_click = box

        await human_delay(800, 1500)

        bounding = await box_click.bounding_box()
        if not bounding:
            log.warning(f"[{username}] Bounding box introuvable")
            return None

        x = bounding["x"] + bounding["width"] / 2
        y = bounding["y"] + bounding["height"] / 2

        await page.mouse.move(x, y)
        await human_delay(200, 400)
        await page.mouse.down()
        await human_delay(100, 200)
        await page.mouse.up()

        log.info(f"[{username}] Clic réel effectué ✓")

        log.info(f"[{username}] Attente 30s validation...")
        await asyncio.sleep(30)

        # ferme popups
        for p in page.context.pages:
            if p != page:
                log.info(f"[{username}] Fermeture popup {p.url}")
                await p.close()

        return 0

    except Exception as e:
        log.warning(f"[{username}] Erreur clic : {e}")
        return None

# ==============================
# MAIN LOOP
# ==============================

async def vote_cycle(playwright):
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )

    while True:

        # 🔥 Gestion plage horaire
        if not is_allowed_hour():
            sleep_time = seconds_until_start()
            log.info(f"⏸ Hors plage horaire → sommeil {sleep_time} sec")
            await asyncio.sleep(sleep_time)
            continue

        all_timers = []

        for username in PROFILES:
            log.info(f"===== TOUR DE {username} =====")

            context = await browser.new_context(locale="fr-FR")
            page = await context.new_page()

            await login(page, username)

            for label in VOTE_LABELS:
                await page.reload(wait_until="networkidle")
                await human_delay()

                result = await check_vote(page, username, label)

                if result and result > 0:
                    all_timers.append(result)

            await context.close()

        # 🔥 Calcul prochain réveil intelligent
        if all_timers:
            next_sleep = min(all_timers)
        else:
            next_sleep = 300  # fallback

        random_delay = random.randint(10, 300)
        final_sleep = next_sleep + random_delay

        log.info(f"Prochain check dans {final_sleep} secondes")
        await asyncio.sleep(final_sleep)

# ==============================
# ENTRY
# ==============================

async def main():
    async with async_playwright() as p:
        await vote_cycle(p)

if __name__ == "__main__":
    asyncio.run(main())