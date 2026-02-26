import asyncio
import random
import logging
import re
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from nopecha.api.httpx import AsyncHTTPXAPIClient

# ==============================
# CONFIG
# ==============================

URL = "https://playhyping.com/fr/vote"
PROFILES = ["Slifryd", "Leoboum"]
HEADLESS = True

VOTE_LABELS = ["VOTE #1", "VOTE #2"]

START_HOUR = 6
STOP_HOUR = 2

# ==============================
# CONFIG NOPECHA - À COMPLETER
# ==============================

NOPECHA_API_KEY = "YOUR_NOPECHA_API_KEY"  # ← Remplacer par votre clé API
NOPECHA_ENABLED = False  # Passer à True si vous avez une clé API

# ==============================
# CONFIG SITES - À PERSONNALISER
# ==============================

SITES_CONFIG = {
    "playhyping": {
        "keywords": ["playhyping.com"],
        "captcha_type": "hcaptcha"  # CAPTCHA à résoudre avant vote
    },
    "serveur-prive": {
        "keywords": ["serveur-prive.net"],
        "input_field": "#username",
        "submit_button": "#voteBtn",
        "wait_time": 2,
        "is_form": True,
        "captcha_type": "mtcaptcha"  # MTcaptcha en lettre
    },
    "serveursminecraft": {
        "keywords": ["serveursminecraft.org"],
        "first_button": "a[data-toggle='modal'][data-target='#vote']",
        "wait_before_second": 10,
        "second_button": "input[type='submit'].btn.btn-success",
        "wait_time": 2,
        "is_two_step": True,
        "captcha_type": "recaptcha",  # reCaptcha après le premier clic
        "captcha_after_first_click": True  # Important : CAPTCHA après le clic
    },
    "top-serveurs": {
        "keywords": ["top-serveurs.net"],
        "input_field": "#playername",
        "submit_button": "span.btn-content",
        "wait_time": 2,
        "wait_before_click": 10,
        "is_form": True,
        "captcha_type": "cloudflare"  # Cloudflare CAPTCHA
    },
    "discord": {
        "keywords": ["discord.gg", "discord.com"],
        "selectors": ["button", "a[href*='join']"],
        "wait_time": 5,
        "captcha_type": None
    },
    "twitch": {
        "keywords": ["twitch.tv"],
        "selectors": ["button[aria-label*='Suivre']", "button:has-text('Suivre')"],
        "wait_time": 3,
        "captcha_type": None
    },
    "youtube": {
        "keywords": ["youtube.com"],
        "selectors": ["button[aria-label*='S\\'abonner']", "yt-button-shape"],
        "wait_time": 4,
        "captcha_type": None
    },
    "twitter": {
        "keywords": ["twitter.com", "x.com"],
        "selectors": ["button[aria-label*='Suivre']", "[role='button']:has-text('Suivre')"],
        "wait_time": 3,
        "captcha_type": None
    },
    "instagram": {
        "keywords": ["instagram.com"],
        "selectors": ["button:has-text('Suivre')"],
        "wait_time": 3,
        "captcha_type": None
    },
    "tiktok": {
        "keywords": ["tiktok.com"],
        "selectors": ["button[data-e2e='follow-button']"],
        "wait_time": 3,
        "captcha_type": None
    },
    "generic": {
        "keywords": [],
        "selectors": ["button", "a.btn", "[role='button']"],
        "wait_time": 2,
        "captcha_type": None
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
# HORAIRES
# ==============================

def is_allowed_hour():
    now = datetime.now()
    h = now.hour

    if START_HOUR < STOP_HOUR:
        return START_HOUR <= h < STOP_HOUR
    else:
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


def detect_site(url):
    """Détecte quel site a été ouvert"""
    url_lower = url.lower()
    
    for site_name, config in SITES_CONFIG.items():
        if site_name != "generic":
            for keyword in config["keywords"]:
                if keyword in url_lower:
                    return site_name
    
    return "generic"


async def solve_captcha(page, username, site_name="generic"):
    """Résout les CAPTCHAs avec NopeCHA selon le site"""
    
    if not NOPECHA_ENABLED:
        return False
    
    config = SITES_CONFIG.get(site_name, SITES_CONFIG["generic"])
    captcha_type = config.get("captcha_type")
    
    # Si pas de CAPTCHA configuré pour ce site
    if not captcha_type:
        return False
    
    try:
        nopecha = AsyncHTTPXAPIClient(NOPECHA_API_KEY)
        url = page.url
        
        # Résoudre hCaptcha
        if captcha_type == "hcaptcha":
            sitekey = await page.get_attribute('[data-sitekey]', 'data-sitekey')
            if sitekey:
                log.info(f"[{username}] hCaptcha détecté sur {site_name}, résolution...")
                solution = await nopecha.solve_hcaptcha(sitekey, url)
                
                if solution and solution.get("data"):
                    token = solution["data"]
                    log.info(f"[{username}] ✓ hCaptcha résolu")
                    await page.evaluate(f"""
                        document.querySelector('[name="g-recaptcha-response"]').innerHTML = '{token}';
                    """)
                    return True
        
        # Résoudre reCaptcha v2
        elif captcha_type == "recaptcha":
            sitekey = await page.get_attribute('[data-sitekey]', 'data-sitekey')
            if sitekey:
                log.info(f"[{username}] reCaptcha détecté sur {site_name}, résolution...")
                solution = await nopecha.solve_recaptcha(sitekey, url)
                
                if solution and solution.get("data"):
                    token = solution["data"]
                    log.info(f"[{username}] ✓ reCaptcha résolu")
                    await page.evaluate(f"""
                        document.querySelector('[name="g-recaptcha-response"]').innerHTML = '{token}';
                    """)
                    return True
        
        # Résoudre Cloudflare Turnstile
        elif captcha_type == "cloudflare":
            sitekey = await page.get_attribute('[data-sitekey]', 'data-sitekey')
            if sitekey:
                log.info(f"[{username}] Cloudflare Turnstile détecté sur {site_name}, résolution...")
                # Turnstile nécessite un proxy - on va essayer sans pour le moment
                solution = await nopecha.solve_turnstile(sitekey, url)
                
                if solution and solution.get("data"):
                    token = solution["data"]
                    log.info(f"[{username}] ✓ Turnstile résolu")
                    await page.evaluate(f"""
                        document.querySelector('[name="cf-turnstile-response"]').value = '{token}';
                    """)
                    return True
        
        # Résoudre MTcaptcha (texte/lettres)
        elif captcha_type == "mtcaptcha":
            log.info(f"[{username}] MTcaptcha détecté sur {site_name}, résolution...")
            
            # Chercher l'image du CAPTCHA MTcaptcha
            captcha_img = await page.get_attribute('img[alt*="captcha"], img[src*="captcha"], img[class*="captcha"]', 'src')
            if captcha_img:
                # Utiliser la reconnaissance de texte
                solution = await nopecha.recognize_textcaptcha([captcha_img])
                
                if solution and solution.get("data"):
                    token = solution["data"][0] if isinstance(solution["data"], list) else solution["data"]
                    log.info(f"[{username}] ✓ MTcaptcha résolu : {token}")
                    
                    # Remplir le champ de réponse du CAPTCHA
                    captcha_input = await page.query_selector('input[name*="captcha"], input[placeholder*="captcha"]')
                    if captcha_input:
                        await page.fill('input[name*="captcha"], input[placeholder*="captcha"]', token)
                        return True
        
        return False
        
    except Exception as e:
        log.warning(f"[{username}] Erreur résolution CAPTCHA : {e}")
        return False

# ==============================
# HANDLE POPUP CLICKS
# ==============================

async def handle_popup_clicks(popup, username, site_name):
    """Effectue les clics nécessaires sur le popup/site"""
    
    config = SITES_CONFIG.get(site_name, SITES_CONFIG["generic"])
    
    log.info(f"[{username}] Popup détecté : {site_name} ({popup.url})")
    await human_delay()
    
    try:
        # Attendre que la page se charge
        await asyncio.sleep(config["wait_time"])
        
        # Résoudre les CAPTCHAs si configuré pour ce site
        await solve_captcha(popup, username, site_name)
        
        # Si c'est un formulaire avec remplissage de pseudo
        if config.get("is_form"):
            log.info(f"[{username}] Remplissage du formulaire sur {site_name}")
            
            # Remplir le champ username
            input_field = popup.locator(config["input_field"])
            if await input_field.count() > 0:
                await input_field.fill(username)
                await human_delay(300, 500)
                log.info(f"[{username}] ✓ Pseudo rempli : {username}")
            
            # Attendre avant clic si configuré
            wait_before = config.get("wait_before_click", 0)
            if wait_before > 0:
                log.info(f"[{username}] Attente {wait_before}s avant clic...")
                await asyncio.sleep(wait_before)
            
            # Cliquer le bouton submit
            submit_btn = popup.locator(config["submit_button"])
            if await submit_btn.count() > 0:
                await submit_btn.scroll_into_view_if_needed()
                await human_delay(200, 400)
                
                bounding = await submit_btn.bounding_box()
                if bounding:
                    x = bounding["x"] + bounding["width"] / 2
                    y = bounding["y"] + bounding["height"] / 2
                    
                    await popup.mouse.move(x - 30, y - 30)
                    await human_delay(100, 200)
                    await popup.mouse.move(x, y)
                    await human_delay(100, 150)
                    await popup.mouse.down()
                    await human_delay(50, 100)
                    await popup.mouse.up()
                    
                    log.info(f"[{username}] ✓ Formulaire soumis sur {site_name}")
                    await human_delay(1000, 2000)
                    return True
            
            return False
        
        # Si c'est deux étapes (clic -> attente -> clic)
        if config.get("is_two_step"):
            log.info(f"[{username}] Mode deux étapes détecté sur {site_name}")
            
            # Premier clic
            first_btn = popup.locator(config["first_button"])
            if await first_btn.count() > 0:
                await first_btn.scroll_into_view_if_needed()
                await human_delay(200, 400)
                
                bounding = await first_btn.bounding_box()
                if bounding:
                    x = bounding["x"] + bounding["width"] / 2
                    y = bounding["y"] + bounding["height"] / 2
                    
                    await popup.mouse.move(x - 30, y - 30)
                    await human_delay(100, 200)
                    await popup.mouse.move(x, y)
                    await human_delay(100, 150)
                    await popup.mouse.down()
                    await human_delay(50, 100)
                    await popup.mouse.up()
                    
                    log.info(f"[{username}] ✓ Premier clic effectué")
                    
                    # Résoudre CAPTCHA si configuré et qu'il apparait après le clic
                    if config.get("captcha_after_first_click"):
                        await asyncio.sleep(2)  # Laisser le CAPTCHA s'afficher
                        await solve_captcha(popup, username, site_name)
                    
                    # Attendre avant le second clic
                    wait_time = config.get("wait_before_second", 5)
                    log.info(f"[{username}] Attente {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    
                    # Deuxième clic
                    second_btn = popup.locator(config["second_button"])
                    if await second_btn.count() > 0:
                        await second_btn.scroll_into_view_if_needed()
                        await human_delay(200, 400)
                        
                        bounding = await second_btn.bounding_box()
                        if bounding:
                            x = bounding["x"] + bounding["width"] / 2
                            y = bounding["y"] + bounding["height"] / 2
                            
                            await popup.mouse.move(x - 30, y - 30)
                            await human_delay(100, 200)
                            await popup.mouse.move(x, y)
                            await human_delay(100, 150)
                            await popup.mouse.down()
                            await human_delay(50, 100)
                            await popup.mouse.up()
                            
                            log.info(f"[{username}] ✓ Deuxième clic effectué")
                            await human_delay(1000, 2000)
                            return True
            
            return False
        
        # Sinon, chercher et cliquer les sélecteurs
        for selector in config["selectors"]:
            try:
                element = popup.locator(selector).first
                if await element.count() > 0:
                    log.info(f"[{username}] Élément trouvé : {selector}")
                    
                    await element.scroll_into_view_if_needed()
                    await human_delay(200, 500)
                    
                    bounding = await element.bounding_box()
                    if bounding:
                        x = bounding["x"] + bounding["width"] / 2
                        y = bounding["y"] + bounding["height"] / 2
                        
                        await popup.mouse.move(x - 50, y - 50)
                        await human_delay(100, 300)
                        await popup.mouse.move(x, y)
                        await human_delay(100, 200)
                        
                        await popup.mouse.down()
                        await human_delay(50, 150)
                        await popup.mouse.up()
                        
                        log.info(f"[{username}] ✓ Clic effectué sur {site_name}")
                        await human_delay(1000, 2000)
                        
                        return True
                        
            except Exception as e:
                log.debug(f"[{username}] Sélecteur '{selector}' failed: {e}")
                continue
        
        log.warning(f"[{username}] Aucun élément cliquable trouvé sur {site_name}")
        return False
        
    except Exception as e:
        log.warning(f"[{username}] Erreur gestion popup : {e}")
        return False


async def process_all_popups(page, username):
    """Traite tous les popups qui s'ouvrent"""
    
    def popup_handler(popup):
        site_name = detect_site(popup.url)
        asyncio.create_task(handle_popup_clicks(popup, username, site_name))
    
    # Écouter les popups
    page.on("popup", popup_handler)

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

        # Enregistrer le handler pour les popups AVANT le clic
        await process_all_popups(page, username)

        await human_delay(800, 1500)

        bounding = await box.bounding_box()
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

        # Résoudre les CAPTCHAs si configuré pour playhyping
        await solve_captcha(page, username, "playhyping")

        log.info(f"[{username}] Attente 20s validation...")
        await asyncio.sleep(20)

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
            next_sleep = min(all_timers)
        else:
            next_sleep = 300

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
