FROM python:3.12-slim

# Installer les dépendances système nécessaires à Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl wget unzip ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 libgtk-3-0 \
    fonts-liberation fonts-unifont \
    && rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers requirements.txt dans le container
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Installer Chromium pour Playwright
RUN python -m playwright install chromium

# Copier tout le code du bot
COPY . .

# Lancer le bot
CMD ["python", "-u", "main.py"]
