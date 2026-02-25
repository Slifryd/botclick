FROM python:3.12-slim

# Installer dépendances pour Chromium
RUN apt-get update && apt-get install -y \
    git curl wget unzip ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 libgtk-3-0 \
    fonts-liberation fonts-unifont \
 && rm -rf /var/lib/apt/lists/*

# Définir le dossier de travail
WORKDIR /app

# Copier le code dans le conteneur
COPY . /app

# Installer Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Installer Chromium pour Playwright
RUN playwright install chromium

# Lancer le script
CMD ["python", "-u", "main.py"]
