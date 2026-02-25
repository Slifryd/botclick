import asyncio
import random
import logging
import time
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

URL = "https://playhyping.com/fr/vote"

PROFILES = ["Slifryd", "Leoboum"]

HEADLESS = True

# Cooldowns en secondes
VOTES = {
    "VOTE #1": 3 * 3600,
    "VOTE #2": int(1.5 * 3600),
    "VOTE #3": 24 * 3600,
}


async def human_delay(a=500, b=1200):
    await asyncio.sleep(random.uniform(a, b) / 1000)


async def login(page, username):
    log.info(f"[{username}] Connexion...")
    await page.goto(URL, wait_until="networkidle")
    await human_delay()

    invite_btn = page.locator("text=Invité")
    await invite_btn.click()
    await human_delay()

    input_pseudo = page.locator("input[placeholder='Entre ton pseudo ici']")
    await input_pseudo.fill(username)
    await human_delay()

    await input_pseudo.press("Enter")
    await asyncio.sleep(2)

    await page.reload(wait_until="networkidle")
    log.info(f"[{username}] Connecté ✓")


async def try_vote(page, username, label):
    selector = f"div.cursor-pointer:has(h3:has-text('{label}'))"
    btn = page.locator(selector).first

    if await btn.count() == 0:
        log.info(f"[{username}] {label} — bouton absent")
        return False

    await btn.scroll_into_view_if_needed()
    await human_delay()
    await btn.click()
    log.info(f"[{username}] {label} — cliqué ✓")

    await asyncio.sleep(5)

    # Ferme les onglets pubs
    for p in page.context.pages:
        if p != page:
            await p.close()

    return True


async def vote_manager(page, username):
    next_times = {label: 0 for label in VOTES}

    while True:
        now = time.time()

        for label, cooldown in VOTES.items():
            if now >= next_times[label]:
                try:
                    await page.reload(wait_until="networkidle")
                    await human_delay()
                    success = await try_vote(page, username, label)

                    if success:
                        next_times[label] = time.time() + cooldown
                        h = cooldown // 3600
                        m = (cooldown % 3600) // 60
                        log.info(f"[{username}] {label} — prochain vote dans {h}h{m}m")
                    else:
                        # réessaie dans 2 minutes si bouton absent
                        next_times[label] = time.time() + 120

                except Exception as e:
                    log.warning(f"[{username}] {label} — erreur : {e}")
                    next_times[label] = time.time() + 120

        await asyncio.sleep(60)


async def run_profile(playwright, username):
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )

    context = await browser.new_context(locale="fr-FR")
    page = await context.new_page()

    await login(page, username)
    await vote_manager(page, username)


async def main():
    async with async_playwright() as p:
        await asyncio.gather(*[
            run_profile(p, username) for username in PROFILES
        ])


if __name__ == "__main__":
    asyncio.run(main())
