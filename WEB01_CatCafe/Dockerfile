# ---------------------------------------------------------------------------
# WEB01_CatCafe — deliberately vulnerable Flask app for CTF training
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# iputils-ping is needed by the (vulnerable) /admin diagnostics tool.
RUN apt-get update \
 && apt-get install -y --no-install-recommends iputils-ping \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py init_db.py entrypoint.sh ./
COPY templates/ ./templates/
COPY static/    ./static/

# Final flag lives at the filesystem root so RCE can grab it.
COPY flag.txt /flag.txt
RUN chmod 644 /flag.txt && chmod +x /app/entrypoint.sh

EXPOSE 4000
ENTRYPOINT ["/app/entrypoint.sh"]
