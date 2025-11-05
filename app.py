#!/usr/bin/env python3
import os
import uuid
import subprocess
import threading
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename

# Minimal Flask app — no auth, no limits (per tua richiesta)
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg"}
ALLOWED_AUDIO_EXT = {"mp3", "wav", "m4a", "aac", "ogg"}
FFMPEG_BIN = "ffmpeg"  # assume ffmpeg è nel PATH

app = Flask(__name__, static_folder="static", template_folder="templates")
# app.secret_key non necessario per uso privato, ma Flask richiede una chiave per flash()
app.secret_key = "dev-secret"

BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def allowed_file(filename: str, allowed_set: set):
    return bool(filename and "." in filename and filename.rsplit(".", 1)[-1].lower() in allowed_set)

def schedule_delete(paths, delay=300):
    def _delete():
        for p in paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
    t = threading.Timer(delay, _delete)
    t.daemon = True
    t.start()

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    if "image" not in request.files or "audio" not in request.files:
        flash("Devi caricare immagine e audio.", "error")
        return redirect(url_for("index"))

    image = request.files["image"]
    audio = request.files["audio"]

    if not image or not audio or image.filename == "" or audio.filename == "":
        flash("File mancanti.", "error")
        return redirect(url_for("index"))

    if not allowed_file(image.filename, ALLOWED_IMAGE_EXT):
        flash("Formato immagine non supportato.", "error")
        return redirect(url_for("index"))

    if not allowed_file(audio.filename, ALLOWED_AUDIO_EXT):
        flash("Formato audio non supportato.", "error")
        return redirect(url_for("index"))

    uid = uuid.uuid4().hex
    img_ext = secure_filename(image.filename).rsplit(".", 1)[-1].lower()
    aud_ext = secure_filename(audio.filename).rsplit(".", 1)[-1].lower()

    image_path = str(UPLOAD_DIR / f"{uid}_img.{img_ext}")
    audio_path = str(UPLOAD_DIR / f"{uid}_aud.{aud_ext}")
    output_path = str(UPLOAD_DIR / f"{uid}_out.mp4")

    try:
        image.save(image_path)
        audio.save(audio_path)
    except Exception:
        flash("Errore nel salvataggio dei file.", "error")
        return redirect(url_for("index"))

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-loop", "1",
        "-framerate", "2",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        output_path,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        # pulizia rapida dei file upload
        schedule_delete([image_path, audio_path], delay=10)
        err = (e.stderr or e.stdout or str(e))[:400]
        flash(f"Errore durante la generazione del video: {err}", "error")
        return redirect(url_for("index"))
    except Exception as e:
        schedule_delete([image_path, audio_path], delay=10)
        flash(f"Errore interno: {e}", "error")
        return redirect(url_for("index"))

    # programma la cancellazione dei file (incluso l'output) dopo 5 minuti
    schedule_delete([image_path, audio_path, output_path], delay=300)

    try:
        return send_file(output_path, as_attachment=True, download_name="video.mp4")
    except TypeError:
        # compatibilità con Flask più vecchie
        return send_file(output_path, as_attachment=True, attachment_filename="video.mp4")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
