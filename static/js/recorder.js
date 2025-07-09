document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded, initializing recorder.js');
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'es-ES';
    recognition.continuous = true;
    recognition.interimResults = true;
    let isActivated = false;
    let conversationContext = [];
    const statusElement = document.getElementById('status');
    const transcriptElement = document.getElementById('transcript');
    let audioContext = null; // Lazy initialization

    // Create fallback audio element
    const fallbackAudio = document.createElement('audio');
    document.body.appendChild(fallbackAudio);

    // Make resumeAudioContext globally accessible
    window.resumeAudioContext = function() {
        console.log('resumeAudioContext called');
        if (!audioContext) {
            console.log('Creating new AudioContext');
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioContext.state === 'suspended') {
            console.log('AudioContext is suspended, attempting resume');
            return audioContext.resume().then(() => {
                console.log('AudioContext resumed successfully');
                return true;
            }).catch(err => {
                console.error('Error resuming AudioContext:', err);
                transcriptElement.textContent = 'Error: No se pudo iniciar el audio.';
                return false;
            });
        }
        console.log('AudioContext already active');
        return Promise.resolve(true);
    };

    function updateStatus(state) {
        console.log('Updating status to:', state);
        statusElement.className = 'status ' + (state ? state : '');
        if (state === 'listening') {
            transcriptElement.classList.remove('alert-secondary', 'alert-success', 'alert-warning', 'alert-info');
            transcriptElement.classList.add('alert-success');
        } else if (state === 'processing') {
            transcriptElement.classList.remove('alert-secondary', 'alert-success', 'alert-warning', 'alert-info');
            transcriptElement.classList.add('alert-warning');
        } else if (state === 'speaking') {
            transcriptElement.classList.remove('alert-secondary', 'alert-success', 'alert-warning', 'alert-info');
            transcriptElement.classList.add('alert-info');
        } else {
            transcriptElement.classList.remove('alert-success', 'alert-warning', 'alert-info');
            transcriptElement.classList.add('alert-secondary');
        }
    }

    function spatializeAudio(source) {
        console.log('Spatializing audio');
        let pannerNode = audioContext.createPanner();
        pannerNode.panningModel = 'HRTF';
        pannerNode.distanceModel = 'inverse';
        pannerNode.refDistance = 1;
        pannerNode.maxDistance = 100;
        pannerNode.rolloffFactor = 1;
        pannerNode.coneInnerAngle = 360;
        pannerNode.coneOuterAngle = 0;
        pannerNode.coneOuterGain = 0;
        pannerNode.setPosition(1, 0, 0);
        source.connect(pannerNode);
        pannerNode.connect(audioContext.destination);
    }

    recognition.onresult = (event) => {
        console.log('onresult triggered, processing speech results');
        let interimTranscript = '';
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript.trim().toLowerCase();
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        transcriptElement.textContent = interimTranscript || finalTranscript;
        console.log('Transcript updated:', transcriptElement.textContent);

        if (finalTranscript.includes('hey asistente') && !isActivated) {
            console.log('Activation phrase "hey asistente" detected');
            isActivated = true;
            updateStatus('listening');
            transcriptElement.textContent = 'Escuchando tu pregunta...';
            setTimeout(() => {
                console.log('Stopping recognition after timeout');
                recognition.stop();
                startQueryRecording();
            }, 1000);
        }
    };

    recognition.onend = () => {
        console.log('Recognition ended, state:', recognition.state, 'isActivated:', isActivated);
        if (!isActivated && recognition) {
            try {
                if (recognition.state !== 'running') {
                    console.log('Attempting to restart recognition');
                    recognition.start();
                    console.log('SpeechRecognition restarted');
                } else {
                    console.log('Recognition already running, no restart needed');
                }
            } catch (err) {
                console.error('Error restarting SpeechRecognition:', err);
            }
        } else if (isActivated) {
            console.log('Resetting assistant due to activation end');
            resetAssistant();
        }
    };

    recognition.onerror = (event) => {
        console.log('Recognition error occurred:', event.error);
        if (event.error === 'no-speech') {
            if (isActivated) {
                console.log('No speech detected, resetting assistant');
                resetAssistant();
            } else if (recognition && recognition.state !== 'running') {
                try {
                    console.log('Attempting to restart recognition after no-speech');
                    recognition.stop();
                    setTimeout(() => {
                        recognition.start();
                        console.log('SpeechRecognition restarted after no-speech');
                    }, 200);
                } catch (err) {
                    console.error('Error restarting SpeechRecognition after no-speech:', err);
                }
            } else {
                console.log('Recognition already running or in invalid state, skipping restart');
            }
        } else {
            console.log('Other error detected:', event.error);
            transcriptElement.textContent = 'Error en el micrófono: ' + event.error;
            setTimeout(resetAssistant, 2000);
        }
    };

    function startQueryRecording() {
        console.log('Starting query recording');
        resumeAudioContext().then(isResumed => {
            console.log('AudioContext resumed status:', isResumed);
            if (!isResumed) {
                console.error('Failed to resume AudioContext, manual activation required');
                transcriptElement.textContent = 'Haz clic en "Activar Micrófono" para continuar.';
                return;
            }
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                console.error('getUserMedia not supported or unavailable');
                transcriptElement.textContent = 'Error: Micrófono no soportado. Verifica permisos.';
                resetAssistant();
                return;
            }

            navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
                console.log('Microphone access granted, starting media recorder');
                const mediaRecorder = new MediaRecorder(stream);
                let audioChunks = [];
                mediaRecorder.start();
                updateStatus('listening');

                mediaRecorder.ondataavailable = (event) => {
                    console.log('Data available, adding chunk');
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = () => {
                    console.log('Media recorder stopped, processing audio');
                    stream.getTracks().forEach(track => track.stop());
                    const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' });
                    processAudio(audioBlob);
                };

                setTimeout(() => {
                    console.log('Stopping media recorder after 5 seconds');
                    mediaRecorder.stop();
                }, 5000);
            }).catch(err => {
                console.error('Error accessing microphone:', err);
                transcriptElement.textContent = 'Error: No se pudo acceder al micrófono. Verifica permisos.';
                resetAssistant();
            });
        });
    }

    async function processAudio(audioBlob) {
        console.log('Processing audio blob');
        updateStatus('processing');
        try {
            const transcript = await transcribeAudio(audioBlob);
            console.log("Transcribed question:", transcript.text);
            transcriptElement.textContent = transcript.text;

            if (transcript.text.toLowerCase().startsWith('llévame a la sala ')) {
                console.log('Navigation command detected:', transcript.text);
                transcriptElement.textContent = 'Navegando a la sala...';
                window.parent.postMessage(transcript.text, 'http://10.40.21.232:8000');
            } else {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: transcript.text, context: conversationContext })
                });

                console.log('Fetch response status:', response.status);
                if (!response.ok) {
                    console.error('HTTP error response details:', response.status, await response.text());
                    throw new Error(`Error HTTP: ${response.status}`);
                }

                const text = await response.text();
                console.log('Raw response text received:', text);
                const data = JSON.parse(text);
                console.log("Server response parsed:", data);
                if (data.text && data.audio_url) {
                    conversationContext = data.context;
                    transcriptElement.textContent = data.text;
                    updateStatus('speaking');
                    await playResponse(data.audio_url);
                } else {
                    console.log("Error: Response missing audio_url or text:", data);
                    transcriptElement.textContent = 'Error: No se recibió respuesta válida';
                }
            }
        } catch (err) {
            console.error('Error processing audio:', err);
            transcriptElement.textContent = 'Error: No se pudo conectar al servidor';
        }
        resetAssistant();
    }

    async function playResponse(audioUrl) {
        console.log('Playing response from:', audioUrl);
        try {
            await resumeAudioContext();
            const response = await fetch(audioUrl);
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            spatializeAudio(source);
            source.start(0);
            console.log('Web Audio API playback started');
            return new Promise(resolve => {
                source.onended = () => {
                    console.log('Audio playback completed');
                    resolve();
                };
            });
        } catch (err) {
            console.error('Error with Web Audio API:', err);
            try {
                fallbackAudio.src = audioUrl;
                const playPromise = fallbackAudio.play();
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        console.log('Fallback audio playback started');
                    }).catch(fallbackErr => {
                        console.error('Error initiating fallback playback:', fallbackErr);
                        transcriptElement.textContent = 'Toca el círculo para reproducir la respuesta';
                    });
                }
                return new Promise(resolve => {
                    fallbackAudio.onended = () => {
                        console.log('Fallback audio playback completed');
                        resolve();
                    };
                });
            } catch (fallbackErr) {
                console.error('Error with fallback audio:', fallbackErr);
                transcriptElement.textContent = 'Error: No se pudo reproducir la respuesta';
            }
        }
    }

    async function transcribeAudio(audioBlob) {
        console.log('Transcribing audio blob');
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.mp3');
        try {
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                console.error('Transcription API error:', response.status, await response.text());
                throw new Error(`Error en transcripción: ${response.status}`);
            }
            return await response.json();
        } catch (err) {
            console.error('Error in transcription:', err);
            throw err;
        }
    }

    function resetAssistant() {
        console.log('Resetting assistant, isActivated:', isActivated);
        isActivated = false;
        updateStatus('');
        transcriptElement.textContent = 'Esperando "Hey Asistente"...';
        try {
            if (recognition) {
                console.log('Attempting to restart recognition in resetAssistant, state:', recognition.state);
                recognition.stop();
                setTimeout(() => {
                    if (recognition.state !== 'running') {
                        recognition.start();
                        console.log('SpeechRecognition restarted in resetAssistant');
                    } else {
                        console.log('Recognition already running, skipping start');
                    }
                }, 200);
            }
        } catch (err) {
            console.error('Error restarting SpeechRecognition in resetAssistant:', err);
        }
    }

    // Initial setup
    console.log('Initializing recognition');
    recognition.start();
});