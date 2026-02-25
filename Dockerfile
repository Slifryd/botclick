# Dockerfile pour le bot clicker multi-joueurs avec Playwright
FROM python:3.12-slim

# Variables d'environnement pour Playwright
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Installer les dépendances système nécessaires pour Chromium
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        wget \
        unzip \
        ca-certificates \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgtk-3-0 \
        fonts-liberation \
        fonts-unifont \
        wget \
        ca-certificates \
        curl \
        unzip \
    && rm -rf /var/lib/apt/lists/*

# Créer le dossier de travail
WORKDIR /app

# Copier les fichiers requirements et bot
COPY requirements.txt ./
COPY bot.py ./

# Installer Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Installer Chromium via Playwright
RUN playwright install chromium

# Commande pour lancer le bot
CMD ["python", "-u", "bot.py"]
