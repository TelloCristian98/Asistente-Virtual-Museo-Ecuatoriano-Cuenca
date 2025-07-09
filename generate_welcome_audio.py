import requests
import os

API_KEY = ""  # Reemplaza con tu clave
VOICE_MODEL = "eleven_multilingual_v2"
VOICE_ID = "pNInz6obpgDQGcFmaJgB"
TEXT = "Hola. Bienvenidos al Museo Militar de la Tercera División Tarqui en Cuenca. Aquí exploramos nuestra rica historia militar ecuatoriana. En nuestras cinco salas temáticas encontrarás objetos únicos como retratos de Simón Bolívar y Antonio José de Sucre en la Sala 1, estandartes capturados en la Sala 3, y equipamiento de la Guerra del Cenepa en la Sala 4. Presta atención a las zonas activas para descubrir detalles fascinantes. Esperamos que este recorrido virtual te encante. Di 'hey asistente' y usa comandos como 'llévanos a la sala 1' o 'qué información sobre la sala 2' para guiarte."
OUTPUT_FILE = "static/audio_responses/welcome.mp3"

url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
headers = {
    "xi-api-key": API_KEY,
    "Content-Type": "application/json"
}
data = {
    "text": TEXT,
    "model_id": VOICE_MODEL,
    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
}

response = requests.post(url, json=data, headers=headers)
if response.status_code == 200:
    with open(OUTPUT_FILE, "wb") as f:
        f.write(response.content)
    print(f"Audio generado y guardado como {OUTPUT_FILE}")
else:
    print(f"Error: {response.status_code} - {response.text}")