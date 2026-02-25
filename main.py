import asyncio
import random
import logging
import time
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

URL = "https://playhyping.com/fr/vote"

PROFILES = ["Slifryd", "Leoboum"]  # tes pseudos
HEADLESS = True  # False pour voir le navigateur

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

    await page.locator("text=Invité").click()
    await human_delay()

    pseudo = page.locator("input[placeholder='Entre ton pseudo ici']")
    await pseudo.fill(username)
    await human_delay()
    await pseudo.press("Enter")

    await asyncio.sleep(2)
    await page.reload(wait_until="networkidle")
    log.info(f"[{username}] Connecté ✓")


async def try_vote(page, username, label):
    selector = f"div.cursor-pointer:has(h3:has-text('{label}'))"
    btn = page.locator(selector).first

    if await btn.count() == 0:
        log.info(f"[{username}] {label} — bouton introuvable")
        return False

    await btn.scroll_into_view_if_needed()
    await human_delay()
    await btn.click()
    log.info(f"[{username}] {label} — cliqué ✓")

    await asyncio.sleep(5)

    # ferme les onglets pubs
    for p in page.context.pages:
        if p != page:
            await p.close()

    return True


async def vote_cycle(playwright):
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )
    context = await browser.new_context(locale="fr-FR")
    page = await context.new_page()

    next_times = {
        username: {label: 0 for label in VOTES}
        for username in PROFILES
    }

    while True:
        for username in PROFILES:
            log.info(f"===== TOUR DE {username} =====")
            await login(page, username)

            now = time.time()
            for label, cooldown in VOTES.items():
                if now >= next_times[username][label]:
                    try:
                        await page.reload(wait_until="networkidle")
                        await human_delay()
                        success = await try_vote(page, username, label)

                        if success:
                            next_times[username][label] = time.time() + cooldown
                            h = cooldown // 3600
                            m = (cooldown % 3600) // 60
                            log.info(f"[{username}] {label} — prochain vote dans {h}h{m}m")
                        else:
                            next_times[username][label] = time.time() + 120
                    except Exception as e:
                        log.warning(f"[{username}] {label} — erreur : {e}")
                        next_times[username][label] = time.time() + 120

            await asyncio.sleep(30)  # pause avant joueur suivant

        log.info("Boucle complète terminée, pause 60s")
        await asyncio.sleep(60)


async def main():
    async with async_playwright() as p:
        await vote_cycle(p)


if __name__ == "__main__":
    asyncio.run(main())
