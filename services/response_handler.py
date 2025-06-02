import openai
import os
from dotenv import load_dotenv
from .knowledge import MuseumKnowledge
import requests

load_dotenv()


class ResponseHandler:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.knowledge = MuseumKnowledge()
        self.cache = {}
        self.system_role = """
        Eres el asistente virtual oficial del Museo Militar Ecuatoriano en Cuenca. 
        Tu especialidad son las 5 salas del museo:
        - Sala 1: Batalla de Tarqui e Independencia
        - Sala 2: Batalla del Portete de Tarqui
        - Sala 3: Eventos históricos clave
        - Sala 4: Conflictos en la Cordillera del Cóndor
        - Sala 5: Labor actual del Ejército

        Reglas estrictas:
        1. Responde SOLO sobre temas del museo
        2. Usa EXCLUSIVAMENTE la información proporcionada
        3. Si no sabes algo, di: "Esa información no está en mis registros"
        4. Presentate como asistente del museo cuando te pregunten "quién eres"
        """

    def generate_response(self, user_query: str) -> str:
        # Respuesta predefinida para presentación
        if "quién eres" in user_query.lower():
            return "Soy el asistente virtual del Museo Militar Ecuatoriano en Cuenca. Puedo responder preguntas sobre nuestras 5 salas de exhibición."

        # Buscar en conocimiento local primero
        relevant_qa = self.knowledge.search(user_query)

        if not relevant_qa:
            return "Esa información no está en mis registros del museo."

        # Construir contexto específico
        context = "\n".join([
            f"Sala {qa['sala']}: {qa['completion']}"
            for qa in relevant_qa
        ])

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_role},
                    {"role": "user", "content": f"Información del museo:\n{context}\n\nPregunta: {user_query}"}
                ],
                temperature=0.3,  # Menos creatividad, más precisión
                max_tokens=200
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error en generación de respuesta: {e}")
            # Respuesta de fallback basada en los datasets
            return relevant_qa[0]['completion']

