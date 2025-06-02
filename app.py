from flask import Flask, request, jsonify, render_template, send_from_directory
import openai
import os
from dotenv import load_dotenv
from services.response_handler import ResponseHandler
import requests  # Para llamar a ElevenLabs

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")  # Añadir al .env

app = Flask(__name__)
handler = ResponseHandler()

# Configuración de directorios
os.makedirs("temp", exist_ok=True)
os.makedirs("static/audio_responses", exist_ok=True)


def generate_audio(text, filename):
    """Genera audio usando ElevenLabs API"""
    url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        return True
    return False


@app.route("/")
def home():
    return render_template("recorder.html")


@app.route("/transcribe", methods=["POST"])
def handle_transcription():
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files["audio"]
        temp_path = os.path.join("temp", f"temp_{os.urandom(8).hex()}.mp3")
        audio_file.save(temp_path)

        with open(temp_path, "rb") as f:
            transcript = openai.Audio.transcribe(
                "whisper-1",
                file=f,
                language="es"
            )

        os.remove(temp_path)
        return jsonify({"text": transcript["text"]})

    except Exception as e:
        print(f"Transcription error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/chat", methods=["POST"])
def handle_chat():
    try:
        data = request.get_json()
        if not data or "query" not in data:
            return jsonify({"error": "Query parameter missing"}), 400

        response_text = handler.generate_response(data["query"])

        # Generar audio
        audio_filename = f"response_{os.urandom(8).hex()}.mp3"
        audio_path = os.path.join("static", "audio_responses", audio_filename)

        if generate_audio(response_text, audio_path):
            return jsonify({
                "text": response_text,
                "audio_url": f"/static/audio_responses/{audio_filename}"
            })
        else:
            return jsonify({
                "text": response_text,
                "audio_url": None
            })

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


if __name__ == "__main__":
    app.run(debug=True, port=5000)