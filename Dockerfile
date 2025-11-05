  # Dockerfile minimo per eseguire l'app Flask con ffmpeg nativo
FROM python:3.11-slim

# Installare ffmpeg e pacchetti minimi
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Impostazioni di lavoro
WORKDIR /app

# Copia e installa dipendenze Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia il codice dell'app
COPY . /app

# Crea la cartella per upload temporanei
RUN mkdir -p /app/uploads && chown -R root:root /app/uploads

# Porta e variabili d'ambiente
ENV PORT=8080
EXPOSE 8080

# Avvia con gunicorn (un solo worker per usare poche risorse)
CMD ["sh", "-c", "gunicorn -w 1 -b 0.0.0.0:${PORT:-8080} app:app"]
