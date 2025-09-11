# bot/Dockerfile
FROM python:3.11

# Opcjonalnie: przyspiesza i upraszcza logi w kontenerach
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Systemowe zależności (minimalne). Jeśli używasz psycopg[binary], nie trzeba dev-packów.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata curl \
  && rm -rf /var/lib/apt/lists/*

# Katalog roboczy
WORKDIR /app

# Najpierw requirements (lepszy cache warstw)
COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

# Potem dopiero reszta kodu
COPY . /app

# (Opcjonalnie) utwórz nie-root usera
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Domyślna komenda (dostosuj jeśli masz inny plik/wejście)
CMD ["python", "bot.py"]

