# Dockerfile aggiornato: usa uno start script che esegue gunicorn con exec
# in modo che le variabili d'ambiente (PORT) vengano espanse e i segnali
# vengano inoltrati correttamente (migliore rispetto a "sh -c").
FROM python:3.11-slim

# Installare ffmpeg e pacchetti minimi
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia e installa dipendenze Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copia il codice dell'app
COPY . /app

# Crea lo script di avvio che esegue gunicorn con 'exec' permettendo
# l'espansione di $PORT e garantendo che i segnali vengano inoltrati
RUN printf '#!/bin/sh\nset -e\n: "${PORT:=8080}"\nexec gunicorn -w 1 -b 0.0.0.0:${PORT} app:app\n' > /app/start.sh && \
    chmod +x /app/start.sh

# Crea la cartella per upload temporanei
RUN mkdir -p /app/uploads && chown -R root:root /app/uploads

ENV PORT=8080
EXPOSE 8080

# Usa lo script come entrypoint (exec dentro lo script)
ENTRYPOINT ["/app/start.sh"]
