import asyncio
import random
import logging
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

URL = "https://playhyping.com/fr/vote"
PROFILES = ["Slifryd", "Leoboum"]
HEADLESS = True

VOTE_LABELS = ["VOTE #1", "VOTE #2", "VOTE #3"]

# 🔥 Plage horaire autorisée
START_HOUR = 6
STOP_HOUR = 2


# ==============================
# HORAIRES
# ==============================

def seconds_until_start():
    now = datetime.now()
    start_today = now.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)

    if now >= start_today:
        start_today += timedelta(days=1)

    return int((start_today - now).total_seconds())


def is_allowed_hour():
    now = datetime.now().hour
    return START_HOUR <= now < STOP_HOUR


# ==============================
# HUMAN DELAY
# ==============================

async def human_delay(a=500, b=1200):
    await asyncio.sleep(random.uniform(a, b) / 1000)


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
# CHECK & VOTE
# ==============================

async def check_vote(page, username, label):
    box = page.locator("div.rounded-2xl").filter(has_text=label).first

    if await box.count() == 0:
        log.info(f"[{username}] {label} introuvable")
        return None

    await box.scroll_into_view_if_needed()
    await human_delay()

    timer_element = box.locator("p")

    if await timer_element.count() > 0:
        text = await timer_element.inner_text()

        if "Disponible" in text:
            seconds = parse_timer(text)

            log.info(
                f"[{username}] {label} → {text.strip()} "
                f"({seconds} sec restantes)"
            )

            return seconds

    # 🔥 Si pas de timer = vote dispo
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
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )

    while True:

        # 🔥 Gestion horaire
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

        if all_timers:
            sleep_time = min(all_timers)
            log.info(f"Prochain vote dispo dans {sleep_time} secondes")
        else:
            sleep_time = 300
        nombre = random.randint(10, 300) + sleep_time
        log.info(f"Bot en veille pour {nombre} secondes")
        await asyncio.sleep(nombre)


# ==============================
# ENTRYPOINT
# ==============================

async def main():
    async with async_playwright() as p:
        await vote_cycle(p)


if __name__ == "__main__":
    asyncio.run(main())
