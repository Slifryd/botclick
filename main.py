import asyncio
import random
import logging
import time
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

URL = "https://playhyping.com/fr/vote"

PROFILES = ["Slifryd", "Leoboum"]
HEADLESS = False  # doit marcher maintenant

VOTES = {
    "VOTE #1": 3 * 3600,
    "VOTE #2": int(1.5 * 3600),
    "VOTE #3": 24 * 3600,
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


async def human_delay(a=800, b=1600):
    await asyncio.sleep(random.uniform(a, b) / 1000)


async def login(page, username):
    log.info(f"[{username}] Connexion...")
    await page.goto(URL, wait_until="domcontentloaded")
    await human_delay()

    await page.click("text=Invité")
    await human_delay()

    pseudo = page.locator("input[placeholder='Entre ton pseudo ici']")
    await pseudo.wait_for()
    await pseudo.fill(username)
    await human_delay()
    await pseudo.press("Enter")

    await page.wait_for_load_state("networkidle")
    log.info(f"[{username}] Connecté ✓")


async def try_vote(page, username, label):
    selector = f"div.cursor-pointer:has(h3:has-text('{label}'))"

    await page.wait_for_selector(selector, timeout=10000)
    btn = page.locator(selector).first

    await btn.scroll_into_view_if_needed()
    await human_delay()
    await btn.click(force=True)

    log.info(f"[{username}] {label} — cliqué ✓")

    await asyncio.sleep(5)

    for p in page.context.pages:
        if p != page:
            await p.close()

    return True


async def vote_cycle(playwright):
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-dev-shm-usage"
        ]
    )

    context = await browser.new_context(
        locale="fr-FR",
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 800}
    )

    # cache le webdriver
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

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
                        await page.reload(wait_until="domcontentloaded")
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

            await asyncio.sleep(30)

        log.info("Boucle complète terminée, pause 60s")
        await asyncio.sleep(60)


async def main():
    async with async_playwright() as p:
        await vote_cycle(p)


if __name__ == "__main__":
    asyncio.run(main())
