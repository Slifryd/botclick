FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    wget curl git xvfb \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libpangocairo-1.0-0 libgtk-3-0 fonts-liberation fonts-unifont \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

ENV DISPLAY=:99

RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]
