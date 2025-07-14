from flask import Flask, request, jsonify, send_from_directory
import openai
import os
import requests
from dotenv import load_dotenv
from datetime import datetime
import uuid
import traceback
from flask_cors import CORS
import ssl
import shutil  # Para mover archivos

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/chat": {"origins": ["http://localhost:8000", "http://10.40.21.232:8000", "http://192.168.100.57:8000", "https://192.168.100.67:63747", "https://172.20.10.2:63747", "*"]}})  # Expanded origins

# Crear carpeta static si no existe
os.makedirs("static", exist_ok=True)

# Mover welcome.mp3 desde audio_responses a static si existe
audio_source = os.path.join("static", "audio_responses", "welcome.mp3")
audio_dest = os.path.join("static", "welcome.mp3")
if os.path.exists(audio_source) and not os.path.exists(audio_dest):
    shutil.move(audio_source, audio_dest)
    print(f"Movido welcome.mp3 de {audio_source} a {audio_dest}")
elif not os.path.exists(audio_dest):
    print("Advertencia: welcome.mp3 no encontrado en audio_responses ni en static. Asegúrate de moverlo manualmente a static/.")

# Configuración de directorios
os.makedirs("static/audio_responses", exist_ok=True)

# Configuración de voz ecuatoriana
VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Voz femenina latina, dinámica
VOICE_MODEL = "eleven_multilingual_v2"

# Declarar contexto de conversación global
conversation_context = []

# System prompt con detalles específicos del museo
SYSTEM_PROMPT = """
Eres un asistente virtual del Museo Militar de la tercera División Tarquiin en Cuenca, especializado en guiar a visitantes por sus cinco salas temáticas. Usa un tono amigable, claro y con acento ecuatoriano neutro. Responde en un máximo de 200 palabras (45 segundos) con una estructura clara: 
1. Introducción: Contextualiza la sala o pregunta (ej. "Estás en la Sala 1, dedicada a los héroes").
2. Cuerpo: Describe exhibiciones específicas o responde con detalles (ej. "Aquí hay retratos de Simón Bolívar y Antonio José de Sucre").
3. Conclusión: Resume o invita a explorar más (ej. "Explora las otras salas para más historia").
Para "¿Quién eres?", di: "Soy tu asistente virtual del Museo Militar de la tercera División Tarqui, aquí para guiarte por la historia militar de Ecuador."
Para "bienvenida", di: "Hola. Bienvenidos al Museo Militar de la tercera División Tarqui. Aquí presentamos una parte de nuestra inconmensurable historia militar ecuatoriana. En nuestras salas temáticas encontrarán diferentes objetos, retratos, fotografías y otros elementos de gran valor histórico. Le recomendamos prestar atención a las zonas activas para obtener información que puede ser de su interés. Esperamos que este recorrido virtual sea de su completo agrado."
Usa solo información verificada:
- Sala 1: Héroes. Retratos de Simón Bolívar y Antonio José de Sucre, carta manuscrita de Sucre, uniforme del Granadero de Tarqui de la Batalla de Tarqui de 1829.
- Sala 2: Portete. Retratos de Antonio José de Sucre, José de la Mar y otros comandantes, detalles tácticos de la batalla del Portete de Tarqui.
- Sala 3: Tarqui. Estandartes peruanos capturados, cronología de la Batalla de Tarqui, imagen de la topografía del portete.
- Sala 4: CENEPA. Cronología de la Guerra del Cenepa de 1995, Capitán Giovanni Calles, General Paco Moncayo, equipamiento militar (armas, mochilas, botas).
- Sala 5: Tiwinsa. Evolución del ejército actual, apoyo en pandemia COVID-19 y terremoto de Manabí 2016, rol de la mujer militar en operaciones especiales.
Para preguntas generales, resume: "El Museo Militar de la tercera División Tarqui muestra la historia militar ecuatoriana en cinco salas, desde la independencia hasta hoy."
Si no es sobre el museo, di: "Lo siento, pregunta sobre las salas del museo."
"""

@app.route("/chat", methods=["POST"])
def handle_chat():
    global conversation_context
    print("Chat endpoint hit")
    try:
        data = request.get_json()
        if not data or "query" not in data:
            print("No query in request data:", data)
            return jsonify({"error": "Query parameter missing"}), 400

        query = data["query"].strip().lower()
        print(f"Received query: {query}")

        # Manejar navegación
        if query.startswith("llévame a la sala ") or query.startswith("vamos a la sala ") or query.startswith("quiero ir a la sala "):
            sala_number = ''.join(filter(str.isdigit, query))
            if sala_number and 1 <= int(sala_number) <= 5:
                print(f"Detected navigation to sala: {sala_number}")
                return jsonify({"text": f"Navegando a Sala {sala_number}", "audio_url": None})
            else:
                print("Invalid sala number or out of range")
                text_response = "Lo siento, solo hay salas del 1 al 5. ¿A cuál te gustaría ir?"
                audio_filename = f"response_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}.mp3"
                audio_path = os.path.join("static", "audio_responses", audio_filename)
                if generate_audio(text_response, audio_path):
                    return jsonify({
                        "text": text_response,
                        "audio_url": f"/static/audio_responses/{audio_filename}",
                        "context": conversation_context
                    })
                else:
                    return jsonify({"text": text_response, "audio_url": None, "context": conversation_context})
        # Manejar "¿Quién eres?"
        elif "quién eres" in query:
            text_response = "Soy tu asistente virtual del Museo Militar de la tercera División Tarqui, aquí para guiarte por la historia militar de Ecuador."
            audio_filename = f"response_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}.mp3"
            audio_path = os.path.join("static", "audio_responses", audio_filename)
            if generate_audio(text_response, audio_path):
                return jsonify({
                    "text": text_response,
                    "audio_url": f"/static/audio_responses/{audio_filename}",
                    "context": conversation_context
                })
            else:
                return jsonify({"text": text_response, "audio_url": None, "context": conversation_context})
        # Manejar "bienvenida"
        elif query == "bienvenida":
            text_response = "Hola. Bienvenidos al Museo Militar de la tercera División Tarqui. Aquí presentamos una parte de nuestra inconmensurable historia militar ecuatoriana. En nuestras salas temáticas encontrarán diferentes objetos, retratos, fotografías y otros elementos de gran valor histórico. Le recomendamos prestar atención a las zonas activas para obtener información que puede ser de su interés. Esperamos que este recorrido virtual sea de su completo agrado."
            audio_filename = f"response_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}.mp3"
            audio_path = os.path.join("static", "audio_responses", audio_filename)
            if generate_audio(text_response, audio_path):
                return jsonify({
                    "text": text_response,
                    "audio_url": f"/static/audio_responses/{audio_filename}",
                    "context": conversation_context
                })
            else:
                return jsonify({"text": text_response, "audio_url": None, "context": conversation_context})
        else:
            # Generar respuesta con OpenAI
            print("Generating text response for query")
            text_response = generate_text_response(query)

            # Generar audio con voz ecuatoriana
            audio_filename = f"response_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}.mp3"
            audio_path = os.path.join("static", "audio_responses", audio_filename)

            if generate_audio(text_response, audio_path):
                conversation_context.append({"role": "user", "content": query})
                conversation_context.append({"role": "assistant", "content": text_response})
                if len(conversation_context) > 10:
                    conversation_context = conversation_context[-10:]
                print(f"Audio generated: {audio_path}")
                return jsonify({
                    "text": text_response,
                    "audio_url": f"/static/audio_responses/{audio_filename}",
                    "context": conversation_context
                })
            else:
                print("Error: Audio generation failed")
                return jsonify({
                    "text": text_response,
                    "audio_url": None,
                    "context": conversation_context
                })

    except Exception as e:
        print(f"Chat error: {str(e)} with stack trace:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def generate_text_response(query: str) -> str:
    """Genera una respuesta estructurada usando OpenAI"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + conversation_context + [
        {"role": "user", "content": query}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=200  # ~45 segundos
        )
        text_response = response.choices[0].message.content
        return convert_numbers_to_spanish(text_response)
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "Lo siento, pregunta sobre las salas del museo."

def generate_audio(text: str, filepath: str) -> bool:
    """Genera audio con voz ecuatoriana usando ElevenLabs"""
    if not ELEVENLABS_API_KEY:
        print("Error: API key de ElevenLabs no configurada")
        return False

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "text": text,
        "model_id": VOICE_MODEL,
        "voice_settings": {
            "stability": 0.3,
            "similarity_boost": 1.0,
            "style": 0.8,  # Más expresividad
            "speaker_boost": True
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        print(f"ElevenLabs response: {response.status_code}")
        with open(filepath, "wb") as f:
            f.write(response.content)
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error generating audio with ElevenLabs: {e}")
        return False

def convert_numbers_to_spanish(text: str) -> str:
    """Convierte números en texto a palabras en español"""
    number_map = {
        "0": "cero", "1": "uno", "2": "dos", "3": "tres", "4": "cuatro", "5": "cinco",
        "6": "seis", "7": "siete", "8": "ocho", "9": "nueve", "10": "diez",
        "11": "once", "12": "doce", "13": "trece", "14": "catorce", "15": "quince",
        "16": "dieciséis", "17": "diecisiete", "18": "dieciocho", "19": "diecinueve", "20": "veinte"
    }

    for num, word in number_map.items():
        text = text.replace(f" {num} ", f" {word} ")
        text = text.replace(f" {num}.", f" {word}.")
        text = text.replace(f"({num})", f"({word})")

    return text

def get_sala_description(sala_number):
    salas = {
        1: "Sala 1. Héroes. Retratos de Simón Bolívar y Antonio José de Sucre, carta manuscrita de Sucre, uniforme del Granadero de Tarqui de la Batalla de Tarqui de 1829.",
        2: "Sala 2. Portete. Retratos de Antonio José de Sucre, José de la Mar y otros comandantes, detalles tácticos de la batalla del Portete de Tarqui.",
        3: "Sala 3. Tarqui. Estandartes peruanos capturados, cronología de la Batalla de Tarqui, imagen de la topografía del portete.",
        4: "Sala 4. CENEPA. Cronología de la Guerra del Cenepa de 1995, Capitán Giovanni Calles, General Paco Moncayo, equipamiento militar (armas, mochilas, botas).",
        5: "Sala 5. Tiwinsa. Evolución del ejército actual, apoyo en pandemia COVID-19 y terremoto de Manabí 2016, rol de la mujer militar en operaciones especiales."
    }
    return salas.get(sala_number, "Información no disponible.")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return "Museo Militar Ecuatoriano Assistant", 200  # Minimal response to avoid 404

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile="certs/cert.pem", keyfile="certs/key.pem")
        print("SSL context loaded successfully")
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"Error loading SSL context: {e}")
        raise