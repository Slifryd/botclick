FROM python:3.12-slim

# Dépendances système pour Playwright + NopeCHA + httpx
RUN apt-get update && apt-get install -y \
    # Outils généraux
    wget curl git xvfb \
    # Dépendances Playwright/Chromium
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libpangocairo-1.0-0 libgtk-3-0 fonts-liberation fonts-unifont \
    # Dépendances SSL/TLS pour httpx
    ca-certificates openssl libssl-dev \
    # Dépendances supplémentaires
    libfreetype6 libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copie requirements.txt et code
COPY requirements.txt .
COPY vote_sites.py .
COPY NOPECHA_SETUP.md .

# Upgrade pip et installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Installer les navigateurs Playwright
RUN playwright install chromium

# Configuration Xvfb pour display virtuel (optionnel, utile pour debug)
ENV DISPLAY=:99
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Variable d'environnement pour vérifier la config
ENV PYTHONUNBUFFERED=1

# Commande pour lancer le script
CMD ["python", "-u", "vote_sites.py"]
