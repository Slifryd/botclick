import asyncio
import random
import logging
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────

PROFILES = [
    {"name": "Slifryd", "url": "https://playhyping.com/vote?username=Slifryd"},
    {"name": "Leoboum", "url": "https://playhyping.com/vote?username=Leoboum"},
]

# (texte du bouton, intervalle_min, intervalle_max) — en secondes
# Min = valeur + 1min, Max = valeur + 5min
CLICKS = [
    ("VOTE #1",  3*3600 + 60,  3*3600 + 300),   # 3h+1min à 3h+5min
    ("VOTE #2",  5400 + 60,    5400 + 300),      # 1h30+1min à 1h30+5min
    ("VOTE #3",  24*3600 + 60, 24*3600 + 300),   # 24h+1min à 24h+5min
]

HEADLESS = True

# ─────────────────────────────────────────────


async def human_delay(min_ms=400, max_ms=1200):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)


async def click_task(context, page, text: str, interval_min: int, interval_max: int, profile_name: str, click_label: str):
    click_count = 0
    while True:
        try:
            element = page.locator("div").filter(has_text=text).first
            await element.wait_for(state="visible", timeout=15_000)
            await human_delay(300, 900)
            await element.scroll_into_view_if_needed()
            await human_delay(200, 600)

            # Attend qu'un nouvel onglet s'ouvre après le clic
            async with context.expect_page(timeout=15_000) as new_page_info:
                await element.click()

            new_page = await new_page_info.value
            log.info(f"[{profile_name}] {click_label} — nouvel onglet ouvert, attente du chargement...")

            # Attend que la nouvelle page soit chargée (max 10s)
            try:
                await new_page.wait_for_load_state("networkidle", timeout=10_000)
            except Exception:
                pass  # On continue même si ça timeout

            log.info(f"[{profile_name}] {click_label} — page chargée, fermeture de l'onglet...")
            await new_page.close()

            click_count += 1
            log.info(f"[{profile_name}] {click_label} — clic #{click_count} ✓")

        except Exception as e:
            log.warning(f"[{profile_name}] {click_label} — échec du clic : {e}")

        wait = random.uniform(interval_min, interval_max)
        h, m = divmod(int(wait), 3600)
        m, s = divmod(m, 60)
        log.info(f"[{profile_name}] {click_label} — prochain clic dans {h}h{m:02d}m{s:02d}s")
        await asyncio.sleep(wait)


async def run_profile(playwright, profile: dict):
    name = profile["name"]
    url  = profile["url"]

    log.info(f"[{name}] Lancement du navigateur...")
    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="fr-FR",
        timezone_id="Europe/Paris",
        extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8"},
    )
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
    """)

    page = await context.new_page()
    log.info(f"[{name}] Chargement de {url}...")
    await page.goto(url, wait_until="networkidle")
    log.info(f"[{name}] Page chargée ✓")

    labels = ["Bouton 1 (3h)", "Bouton 2 (1h30)", "Bouton 3 (24h)"]

    await asyncio.sleep(random.uniform(0, 10))

    await asyncio.gather(*[
        click_task(context, page, text, imin, imax, name, labels[i])
        for i, (text, imin, imax) in enumerate(CLICKS)
    ])


async def main():
    async with async_playwright() as p:
        await asyncio.gather(*[
            run_profile(p, profile) for profile in PROFILES
        ])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot arrêté par l'utilisateur.")
