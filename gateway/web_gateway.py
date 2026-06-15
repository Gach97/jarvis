"""Jarvis Web Gateway - Complete web-based setup and chat UI.

Serves:
  - Embedded HTML/CSS/JS web UI (no external dependencies)
  - REST API endpoints for setup (credentials, config, skills)
  - WebSocket endpoint for real-time agent communication
  - Media ingestion (audio/video from browser)
  - TTS output streaming back to browser

Port: 8765 (fixed)
All browser communication flows through this gateway into the agent/gateway event loop.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
import logging
import asyncio
import json
import os
import base64
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

app = FastAPI(title="Jarvis Web Gateway")

# In-memory session store for web UI (maps session_id to agent session info)
_web_sessions: Dict[str, Dict[str, Any]] = {}
_web_sessions_lock = asyncio.Lock()


def _get_web_ui_html() -> str:
    """Return the embedded web UI HTML."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jarvis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }
        .container {
            width: 100%;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        .setup-panel, .chat-panel { display: none; }
        .setup-panel.active, .chat-panel.active { display: flex; }
        
        .setup-panel {
            flex-direction: column;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            gap: 20px;
        }
        
        .chat-panel {
            flex-direction: column;
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            height: 100vh;
            max-height: 90vh;
        }
        
        h1 { color: #667eea; font-size: 32px; margin-bottom: 10px; }
        h2 { color: #667eea; font-size: 24px; margin-bottom: 15px; }
        .subtitle { color: #999; font-size: 14px; margin-bottom: 30px; }
        
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 15px;
        }
        label { font-weight: 600; color: #333; font-size: 14px; }
        input, select, textarea {
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            font-family: inherit;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .button-group { display: flex; gap: 10px; margin-top: 20px; }
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        button.primary { background: #667eea; color: white; }
        button.primary:hover { background: #5568d3; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); }
        button.secondary { background: #f0f0f0; color: #333; }
        button.secondary:hover { background: #e0e0e0; }
        
        .transcript {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 20px;
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 15px;
            background: #fafafa;
        }
        .message { margin-bottom: 12px; padding: 10px; border-radius: 6px; }
        .message.user { background: #e3f2fd; text-align: right; margin-left: 20%; }
        .message.assistant { background: #f5f5f5; text-align: left; margin-right: 20%; }
        .message.system { background: #fff9c4; font-size: 12px; color: #666; }
        
        .input-area {
            display: flex;
            gap: 10px;
            align-items: flex-end;
        }
        .input-area textarea {
            flex: 1;
            resize: none;
            height: 60px;
        }
        .input-area button { padding: 12px 20px; }
        
        .media-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        .media-controls button { padding: 10px 16px; font-size: 13px; }
        .status { font-size: 12px; color: #666; margin-top: 5px; }
        .error { color: #d32f2f; }
        .success { color: #388e3c; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Setup Panel -->
        <div id="setupPanel" class="setup-panel active">
            <h1>Jarvis Setup</h1>
            <p class="subtitle">Configure your Jarvis AI agent in a few steps</p>
            
            <div class="form-group">
                <label for="apiKey">API Key (OpenAI/Anthropic/OpenRouter)</label>
                <input type="password" id="apiKey" placeholder="sk-..." required>
            </div>
            
            <div class="form-group">
                <label for="provider">Provider</label>
                <select id="provider" required>
                    <option value="openrouter">OpenRouter</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="openai">OpenAI</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="model">Model</label>
                <input type="text" id="model" placeholder="e.g. claude-opus-4-20250514" required>
            </div>
            
            <div class="form-group">
                <label for="ttsProvider">Text-to-Speech Provider</label>
                <select id="ttsProvider">
                    <option value="piper">Piper (local, free)</option>
                    <option value="openai">OpenAI</option>
                    <option value="elevenlabs">ElevenLabs</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="sttProvider">Speech-to-Text Provider</label>
                <select id="sttProvider">
                    <option value="local">Local Whisper (free)</option>
                    <option value="openai">OpenAI</option>
                    <option value="groq">Groq</option>
                </select>
            </div>
            
            <div class="button-group">
                <button type="button" class="primary" onclick="saveSetup()">Start Using Jarvis</button>
            </div>
            <div id="setupStatus" class="status"></div>
        </div>
        
        <!-- Chat Panel -->
        <div id="chatPanel" class="chat-panel">
            <h2>Jarvis Chat</h2>
            <div class="media-controls">
                <button onclick="toggleAudioInput()" id="audioBtn">🎤 Record Audio</button>
                <button onclick="toggleVideoInput()" id="videoBtn">📹 Video</button>
                <button onclick="speakResponse()" id="speakBtn">🔊 Speak</button>
                <button class="secondary" onclick="logout()">Logout</button>
            </div>
            <div class="transcript" id="transcript"></div>
            <div class="input-area">
                <textarea id="messageInput" placeholder="Type a message..." onkeydown="if(event.key==='Enter' && !event.shiftKey) { sendMessage(); event.preventDefault(); }"></textarea>
                <button class="primary" onclick="sendMessage()">Send</button>
            </div>
            <div id="chatStatus" class="status"></div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let sessionId = null;
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;
        
        // Check if setup is complete
        function checkSetup() {
            const setup = localStorage.getItem('jarvisSetup');
            if (setup) {
                sessionId = JSON.parse(setup).sessionId;
                connectWebSocket();
                showChatPanel();
            }
        }
        
        function showSetupPanel() {
            document.getElementById('setupPanel').classList.add('active');
            document.getElementById('chatPanel').classList.remove('active');
        }
        
        function showChatPanel() {
            document.getElementById('setupPanel').classList.remove('active');
            document.getElementById('chatPanel').classList.add('active');
        }
        
        async function saveSetup() {
            const apiKey = document.getElementById('apiKey').value;
            const provider = document.getElementById('provider').value;
            const model = document.getElementById('model').value;
            const ttsProvider = document.getElementById('ttsProvider').value;
            const sttProvider = document.getElementById('sttProvider').value;
            
            if (!apiKey || !model) {
                document.getElementById('setupStatus').textContent = 'Missing required fields';
                document.getElementById('setupStatus').classList.add('error');
                return;
            }
            
            try {
                const resp = await fetch('/api/setup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ apiKey, provider, model, ttsProvider, sttProvider })
                });
                
                if (!resp.ok) throw new Error('Setup failed');
                const data = await resp.json();
                
                localStorage.setItem('jarvisSetup', JSON.stringify({
                    sessionId: data.sessionId,
                    provider, model, ttsProvider, sttProvider
                }));
                
                sessionId = data.sessionId;
                connectWebSocket();
                showChatPanel();
                addMessage('System', 'Setup complete! Jarvis is ready.');
            } catch (err) {
                document.getElementById('setupStatus').textContent = 'Setup failed: ' + err.message;
                document.getElementById('setupStatus').classList.add('error');
            }
        }
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const token = sessionId;
            ws = new WebSocket(`${protocol}//${window.location.host}/ws?token=${token}`);
            
            ws.onopen = () => {
                updateStatus('Connected to Jarvis');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                // Assistant text response
                if (data.assistant) {
                    addMessage('Jarvis', data.assistant);
                    // Auto-play TTS response if enabled
                    if (localStorage.getItem('ttsEnabled') !== 'false') {
                        updateStatus('Synthesizing audio...');
                    }
                }
                
                // Audio response (TTS synthesis)
                if (data.audio) {
                    playAudio(data.audio);
                    updateStatus('Playing response...');
                }
                
                // Error
                if (data.error) {
                    addMessage('System', 'Error: ' + data.error);
                    updateStatus('Error: ' + data.error);
                }
            };
            
            ws.onclose = () => {
                updateStatus('Disconnected');
            };
            
            ws.onerror = (err) => {
                updateStatus('Connection error');
                console.error(err);
            };
        }
        
        function sendMessage() {
            const text = document.getElementById('messageInput').value.trim();
            if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
            
            addMessage('You', text);
            ws.send(JSON.stringify({ type: 'text', content: text }));
            document.getElementById('messageInput').value = '';
        }
        
        function addMessage(sender, text) {
            const transcript = document.getElementById('transcript');
            const className = sender === 'You' ? 'user' : sender === 'System' ? 'system' : 'assistant';
            const div = document.createElement('div');
            div.className = 'message ' + className;
            div.innerHTML = `<strong>${sender}:</strong> ${escapeHtml(text)}`;
            transcript.appendChild(div);
            transcript.scrollTop = transcript.scrollHeight;
        }
        
        function escapeHtml(text) {
            const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
            return text.replace(/[&<>"']/g, m => map[m]);
        }
        
        function updateStatus(msg) {
            document.getElementById('chatStatus').textContent = msg;
        }
        
        async function toggleAudioInput() {
            if (isRecording) {
                mediaRecorder.stop();
                isRecording = false;
                document.getElementById('audioBtn').textContent = '🎤 Record Audio';
            } else {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
                    mediaRecorder.onstop = () => {
                        const blob = new Blob(audioChunks, { type: 'audio/wav' });
                        sendAudio(blob);
                    };
                    
                    mediaRecorder.start();
                    isRecording = true;
                    document.getElementById('audioBtn').textContent = '⏹️ Stop Recording';
                    updateStatus('Recording audio...');
                } catch (err) {
                    updateStatus('Microphone access denied: ' + err.message);
                }
            }
        }
        
        function toggleVideoInput() {
            updateStatus('Video input coming soon');
        }
        
        async function sendAudio(blob) {
            const reader = new FileReader();
            reader.onload = () => {
                const b64 = reader.result.split(',')[1];
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'audio', data: b64, ext: '.wav' }));
                    updateStatus('Audio sent for transcription');
                }
            };
            reader.readAsDataURL(blob);
        }
        
        function playAudio(b64Audio) {
            try {
                const audio = new Audio('data:audio/wav;base64,' + b64Audio);
                audio.onended = () => {
                    updateStatus('Response complete');
                };
                audio.onerror = (err) => {
                    console.error('Audio playback error:', err);
                    updateStatus('Audio playback failed');
                };
                audio.play().catch(err => {
                    console.error('Audio play() failed:', err);
                    updateStatus('Audio playback blocked');
                });
            } catch (err) {
                console.error('Audio creation error:', err);
            }
        }
        
        async function speakResponse(text) {
            try {
                const resp = await fetch('/api/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text })
                });
                
                if (!resp.ok) throw new Error('TTS failed');
                const data = await resp.json();
                
                if (data.audio) {
                    playAudio(data.audio);
                }
            } catch (err) {
                console.error('TTS error:', err);
            }
        }
        
        function logout() {
            localStorage.removeItem('jarvisSetup');
            location.reload();
        }
        
        // Initialize on page load
        checkSetup();
    </script>
</body>
</html>
"""


@app.get("/")
async def index():
    """Serve the web UI."""
    return HTMLResponse(_get_web_ui_html())


@app.get("/api/config")
async def get_config():
    """Fetch persisted web config (credentials may be partially masked)."""
    try:
        from gateway.web_config_persist import load_web_config
        config = load_web_config()
        
        if config:
            # Mask API key for security
            if config.get("apiKey"):
                key = config["apiKey"]
                config["apiKey"] = key[:10] + "..." if len(key) > 10 else "***"
            return JSONResponse(config)
        
        return JSONResponse({})
    except Exception as e:
        logger.exception("Failed to fetch config")
        return JSONResponse({}, status_code=500)


@app.post("/api/setup")
async def setup(request: Request):
    """Setup endpoint: save credentials and initialize session."""
    try:
        data = await request.json()
        api_key = data.get("apiKey", "").strip()
        provider = data.get("provider", "openrouter").strip()
        model = data.get("model", "").strip()
        tts_provider = data.get("ttsProvider", "piper").strip()
        stt_provider = data.get("sttProvider", "local").strip()
        
        if not api_key or not model:
            return JSONResponse({"error": "Missing credentials"}, status_code=400)
        
        # Create session ID
        session_id = f"web_{int(__import__('time').time())}"
        
        # Store setup in memory
        async with _web_sessions_lock:
            _web_sessions[session_id] = {
                "api_key": api_key,
                "provider": provider,
                "model": model,
                "tts_provider": tts_provider,
                "stt_provider": stt_provider,
                "created_at": __import__('datetime').datetime.now().isoformat(),
            }
        
        # Persist to config.yaml
        from gateway.web_config_persist import save_web_config
        save_web_config(
            api_key=api_key,
            provider=provider,
            model=model,
            tts_provider=tts_provider,
            stt_provider=stt_provider,
        )
        
        logger.info("Jarvis web setup complete: session %s", session_id)
        return JSONResponse({"sessionId": session_id, "status": "ok"})
    except Exception as e:
        logger.exception("Setup failed")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/tts")
async def text_to_speech(request: Request):
    """TTS endpoint: synthesize text to audio and return base64-encoded WAV."""
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        
        if not text:
            return JSONResponse({"error": "No text provided"}, status_code=400)
        
        # Use configured TTS provider (default: Piper local)
        tts_provider = data.get("tts_provider", "piper")
        api_key = data.get("api_key")
        
        from gateway.web_tts_provider import synthesize_and_stream
        
        audio_b64 = await synthesize_and_stream(text, tts_provider, api_key)
        
        if not audio_b64:
            return JSONResponse(
                {"error": "TTS synthesis failed"},
                status_code=500
            )
        
        return JSONResponse({"audio": audio_b64})
    except Exception as e:
        logger.exception("TTS endpoint failed")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: Optional[str] = Query(None)):
    """WebSocket endpoint for real-time chat."""
    # Token validation: check if session exists
    expected = os.environ.get("JARVIS_UI_TOKEN")
    if expected and token != expected:
        await ws.close(code=4401)
        return
    
    # If token looks like a session ID, validate it's in our web sessions
    if token and token.startswith("web_"):
        async with _web_sessions_lock:
            if token not in _web_sessions:
                await ws.close(code=4403)
                return
    
    await ws.accept()
    logger.info("WebSocket connected: %s", ws.client)
    
    session_config = None
    agent = None
    
    try:
        # Get session config
        if token and token.startswith("web_"):
            async with _web_sessions_lock:
                session_config = _web_sessions.get(token)
        
        # Initialize AIAgent with session credentials
        if session_config:
            try:
                from run_agent import AIAgent
                
                agent = AIAgent(
                    base_url=_get_provider_base_url(session_config["provider"]),
                    api_key=session_config["api_key"],
                    provider=session_config["provider"],
                    model=session_config["model"],
                    platform="jarvis",
                    session_id=token,
                    skip_memory=False,
                    quiet_mode=True,
                )
                logger.info("AIAgent initialized for session %s", token)
            except Exception as e:
                logger.exception("Failed to initialize AIAgent: %s", e)
                await ws.send_text(json.dumps({"error": f"Agent init failed: {e}"}))
        
        # Message loop
        while True:
            data = await ws.receive_text()
            
            try:
                msg = json.loads(data)
            except Exception:
                await ws.send_text(json.dumps({"error": "invalid json"}))
                continue
            
            msg_type = msg.get("type")
            
            # Text message: route to agent
            if msg_type == "text":
                content = msg.get("content", "").strip()
                if content and agent:
                    logger.debug("WebSocket text: %s", content)
                    
                    try:
                        # Run agent conversation
                        response = agent.chat(content)
                        
                        # Send response back
                        await ws.send_text(json.dumps({
                            "assistant": response
                        }))
                        
                        # If TTS is enabled, synthesize and stream audio back
                        if session_config:
                            tts_provider = session_config.get("tts_provider", "piper")
                            api_key = session_config.get("api_key")
                            
                            from gateway.web_tts_provider import synthesize_and_stream
                            
                            audio_b64 = await synthesize_and_stream(response, tts_provider, api_key)
                            if audio_b64:
                                await ws.send_text(json.dumps({
                                    "audio": audio_b64
                                }))
                    except Exception as e:
                        logger.exception("Agent chat failed: %s", e)
                        await ws.send_text(json.dumps({"error": f"Agent error: {e}"}))
                elif content:
                    # No agent configured yet
                    await ws.send_text(json.dumps({
                        "error": "Agent not initialized. Check your setup."
                    }))
            
            # Audio message: save and route to STT
            elif msg_type == "audio":
                try:
                    b64 = msg.get("data", "")
                    ext = msg.get("ext", ".wav")
                    audio_data = base64.b64decode(b64)
                    
                    fd, path = tempfile.mkstemp(suffix=ext)
                    os.close(fd)
                    with open(path, "wb") as f:
                        f.write(audio_data)
                    
                    logger.info("Saved audio for STT: %s", path)
                    
                    # Transcribe audio
                    transcribed = await _transcribe_audio(path, session_config)
                    if transcribed and agent:
                        logger.debug("Transcribed: %s", transcribed)
                        
                        try:
                            response = agent.chat(transcribed)
                            await ws.send_text(json.dumps({
                                "assistant": response
                            }))
                        except Exception as e:
                            logger.exception("Agent chat failed: %s", e)
                            await ws.send_text(json.dumps({"error": f"Agent error: {e}"}))
                    
                    try:
                        os.unlink(path)
                    except:
                        pass
                    
                except Exception as e:
                    logger.exception("Audio save failed")
                    await ws.send_text(json.dumps({"error": str(e)}))
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", ws.client)


def _get_provider_base_url(provider: str) -> str:
    """Get the base URL for a provider."""
    urls = {
        "openrouter": "https://openrouter.ai/api/v1",
        "anthropic": "https://api.anthropic.com",
        "openai": "https://api.openai.com/v1",
    }
    return urls.get(provider, "https://openrouter.ai/api/v1")


async def _transcribe_audio(audio_path: str, session_config: Optional[Dict] = None) -> Optional[str]:
    """Transcribe audio file to text using configured STT provider."""
    try:
        from gateway.web_stt_provider import transcribe_audio_file
        
        if not session_config:
            stt_provider = "local"
            api_key = None
        else:
            stt_provider = session_config.get("stt_provider", "local")
            api_key = session_config.get("api_key") if stt_provider in ("openai", "groq") else None
        
        # Call STT provider
        text = await transcribe_audio_file(
            audio_path,
            stt_provider=stt_provider,
            api_key=api_key,
        )
        
        return text
    except Exception as e:
        logger.exception("Transcription wrapper failed: %s", e)
        return None


def run(port: int = 8765, host: str = "127.0.0.1"):
    """Start the Jarvis Web Gateway."""
    import uvicorn
    from gateway.web_startup_hooks import initialize_web_gateway
    
    # Run initialization tasks
    initialize_web_gateway()
    
    logger.info("Starting Jarvis Web Gateway on %s:%d", host, port)
    logger.info("Open http://%s:%d in your browser to access Jarvis", host, port)
    
    uvicorn.run(app, host=host, port=port, log_level="info")
