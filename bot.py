import asyncio
import random
import logging
from playwright.async_api import async_playwright


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

URL = "https://playhyping.com/fr/vote"

PROFILES = ["Slifryd", "Leoboum"]

# (label, intervalle en secondes)
VOTES = [
    ("VOTE #1", 3 * 3600),
    ("VOTE #2", int(1.5 * 3600)),
    ("VOTE #3", 24 * 3600),
]

HEADLESS = True


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


async def click_vote(page, username, label):
    selector = f"div.cursor-pointer:has(h3:has-text('{label}'))"
    btn = page.locator(selector).first

    if await btn.count() == 0:
        log.info(f"[{username}] {label} — indisponible (cooldown)")
        return

    await btn.scroll_into_view_if_needed()
    await human_delay()
    await btn.click()
    log.info(f"[{username}] {label} — cliqué ✓")

    await asyncio.sleep(5)

    # Ferme les popups/onglets ouverts
    for p in page.context.pages:
        if p != page:
            await p.close()


async def vote_loop(page, username, label, interval):
    while True:
        try:
            await page.reload(wait_until="networkidle")
            await human_delay()
            await click_vote(page, username, label)
        except Exception as e:
            log.warning(f"[{username}] {label} — erreur : {e}")

        h = interval // 3600
        m = (interval % 3600) // 60
        log.info(f"[{username}] {label} — prochain essai dans {h}h{m}m")
        await asyncio.sleep(interval)


async def run_profile(playwright, username):
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )

    context = await browser.new_context(locale="fr-FR")
    page = await context.new_page()

    await login(page, username)

    tasks = [
        vote_loop(page, username, label, interval)
        for label, interval in VOTES
    ]

    await asyncio.gather(*tasks)


async def main():
    async with async_playwright() as p:
        await asyncio.gather(*[
            run_profile(p, username) for username in PROFILES
        ])


if __name__ == "__main__":
    asyncio.run(main())
