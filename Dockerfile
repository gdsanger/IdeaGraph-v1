# Basis: schlankes Python-Image
FROM python:3.12-slim

# Keine .pyc, ungepuffertes Logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System-Dependencies (wenn du z.B. Postgres, Pillow etc. brauchst)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Arbeitsverzeichnis
WORKDIR /app

RUN mkdir -p /app/data

# 1) Dependencies rein (damit Docker-Cache sinnvoll genutzt wird)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# 2) Jetzt den Rest des Codes kopieren
COPY . .

# Exposed Port in der Container-Welt
EXPOSE 8002

# Standard-Command: Gunicorn mit Django
# "myproject.wsgi:application" an dein Projekt anpassen!
CMD ["gunicorn", "--bind", "0.0.0.0:8002", "ideagraph.wsgi:application"]
