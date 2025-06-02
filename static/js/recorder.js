document.addEventListener('DOMContentLoaded', function() {
    // Elementos del DOM
    const recordBtn = document.getElementById('recordBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusElement = document.getElementById('status');
    const responseContainer = document.getElementById('responseContainer');
    const responseText = document.getElementById('responseText');
    const responseAudio = document.getElementById('responseAudio');
    
    // Variables de estado
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;

    // Configurar botones
    recordBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    stopBtn.style.display = 'none';
    responseContainer.style.display = 'none';
    responseAudio.style.display = 'none';

    // Función para iniciar grabación
    async function startRecording() {
        try {
            // Resetear UI
            responseContainer.style.display = 'none';
            responseAudio.style.display = 'none';
            responseAudio.src = '';
            statusElement.style.display = 'block';
            statusElement.textContent = "Preparando micrófono...";
            
            // Obtener acceso al micrófono
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Configurar grabador
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            // Eventos del grabador
            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };
            
            mediaRecorder.onstop = () => {
                stream.getTracks().forEach(track => track.stop());
            };
            
            // Iniciar grabación
            mediaRecorder.start(100); // Capturar datos cada 100ms
            isRecording = true;
            
            // Actualizar UI
            recordBtn.style.display = 'none';
            stopBtn.style.display = 'block';
            statusElement.textContent = "Grabando...";
            
        } catch (error) {
            console.error("Error al acceder al micrófono:", error);
            statusElement.textContent = "Error: " + error.message;
            resetUI();
        }
    }

    // Función para detener grabación
    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            statusElement.textContent = "Procesando...";
            stopBtn.style.display = 'none';
            
            // Procesar grabación cuando esté lista
            mediaRecorder.onstop = async () => {
                try {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
                    await processRecording(audioBlob);
                } catch (error) {
                    console.error("Error al procesar grabación:", error);
                    statusElement.textContent = "Error al procesar audio";
                } finally {
                    resetUI();
                }
            };
        }
    }

    // Función para procesar la grabación
    async function processRecording(audioBlob) {
        try {
            // 1. Transcribir audio a texto
            const transcript = await transcribeAudio(audioBlob);
            console.log("Pregunta transcrita:", transcript.text);
            
            // 2. Obtener respuesta del asistente
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: transcript.text })
            });
            
            if (!response.ok) {
                throw new Error(`Error HTTP: ${response.status}`);
            }
            
            const data = await response.json();
            
            // 3. Mostrar respuesta
            responseText.textContent = data.text;
            responseContainer.style.display = 'block';
            
            // 4. Reproducir audio si está disponible
            if (data.audio_url) {
                responseAudio.src = data.audio_url;
                responseAudio.style.display = 'block';
                responseAudio.load(); // Forzar carga del nuevo audio
                
                // Intentar reproducción automática (puede ser bloqueada por el navegador)
                responseAudio.play().catch(error => {
                    console.log("Reproducción automática bloqueada:", error);
                    // Mostrar botón de play alternativo
                });
            }
            
        } catch (error) {
            console.error("Error en processRecording:", error);
            statusElement.textContent = "Error: " + error.message;
        }
    }

    // Función para transcribir audio
    async function transcribeAudio(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.mp3');
        
        try {
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Error en transcripción: ${response.status}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error("Error en transcribeAudio:", error);
            throw error; // Re-lanzar para manejo en processRecording
        }
    }

    // Función para resetear UI
    function resetUI() {
        recordBtn.style.display = 'block';
        stopBtn.style.display = 'none';
        statusElement.style.display = 'none';
    }
});