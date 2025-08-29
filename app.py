from flask import Flask, render_template, request, jsonify
import threading
import time
import datetime
import json
import queue
import subprocess
import webbrowser
import os
import sys

# ====== Import core behaviors from your assistant_core ======
from assistant_core import (
    speak, ask_billion, time_greeting, open_browser_and_search,
    play_song_on_youtube, open_file_manager, handle_keyboard_commands,
    close_window, ai_to_ai_problem_solver
)

# ====== Optional speech & wake word backends ======
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False
    print("⚠️ SpeechRecognition not available. Install: pip install SpeechRecognition")

try:
    from vosk import Model, KaldiRecognizer
    import sounddevice as sd
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("⚠️ Vosk not available. Wake-word detection disabled (pip install vosk sounddevice).")

# ====== Flask app ======
app = Flask(__name__)

# ====== Global state ======
class AssistantState:
    def __init__(self):
        self.is_listening = False           # continuous active_mode speech loop
        self.is_wake_word_active = False    # wake word detection loop
        self.is_processing = False
        self.chat_history = []
        self.system_status = "ONLINE"

        # Threads & control flags
        self._active_thread = None
        self._wake_thread = None
        self._stop_active = threading.Event()
        self._stop_wake = threading.Event()

        # Wake words & exits (aligned with your first file)
        self.WAKE_WORDS = ["hey"]
        self.EXIT_COMMANDS = ["shutdown", "terminate", "exit", "goodbye"]

    def add_chat_message(self, sender, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.chat_history.append({
            "sender": sender,
            "message": message,
            "timestamp": timestamp
        })
        if len(self.chat_history) > 100:
            self.chat_history.pop(0)

state = AssistantState()

# ====== Speech helpers replicated to match your first file ======
def listen_once(prompt: str | None = None, timeout=6, phrase_time_limit=6) -> str:
    """One-shot speech recognition via Google (online)."""
    if not SPEECH_AVAILABLE:
        return ""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        if prompt:
            speak(prompt)
        # small calibration helps in noisy rooms
        r.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            text = r.recognize_google(audio).lower()
            print(f"🗣️ You said: {text}")
            return text
        except sr.WaitTimeoutError:
            speak("No input received, sir.")
            return ""
        except sr.UnknownValueError:
            speak("I did not understand, sir.")
            return ""
        except sr.RequestError:
            speak("Network error with speech service, sir.")
            return ""

def _handle_parsed_command(command: str) -> bool:
    """
    Mirrors your first file's active_mode command handling.
    Returns True if a branch handled the command.
    """
    cmd = command.strip().lower()
    if not cmd:
        return True  # nothing to do, but considered handled

    # Exit commands
    if any(exit_cmd in cmd for exit_cmd in state.EXIT_COMMANDS):
        speak("Shutting down. Goodbye, sir.")
        # In Flask we don't sys.exit(); just mark system OFFLINE
        state.system_status = "OFFLINE"
        return True

    # Pause/standby
    if "wait" in cmd or "hold" in cmd:
        speak("Standing by, sir.")
        return True

    # File manager with follow-up
    if "open file manager" in cmd:
        open_file_manager()  # this already prompts in your core OR we can follow-up:
        # If your assistant_core's open_file_manager is simple, prompt here:
        # folder = listen_once("Which folder shall I open, sir?")
        # if folder:
        #     # we can emulate typing nav with pyautogui inside assistant_core
        return True

    # Recycle bin
    if "open recycle bin" in cmd:
        try:
            subprocess.Popen("explorer shell:RecycleBinFolder")
            speak("Opening Recycle Bin, sir.")
        except Exception:
            speak("I could not open the Recycle Bin, sir.")
        return True

    # Dev/build intent → AI-to-AI problem solver
    if any(phrase in cmd for phrase in [
        "i want to build", "i want to make", "i went to build", "i need to build",
        "create a login page", "make a login page", "create a", "make a"
    ]):
        threading.Thread(target=ai_to_ai_problem_solver, args=(cmd,), daemon=True).start()
        speak("I'll help you with that, sir. Opening the development environment.")
        return True

    # Google / YouTube helpers (use your imported helpers that do the typing/search)
    if "open google" in cmd:
        open_browser_and_search("google", "What would you like to search, sir?")
        return True

    if "open youtube" in cmd:
        open_browser_and_search("youtube", "What shall I search for on YouTube, sir?")
        return True

    if "play" in cmd and "youtube" in cmd:
        song = cmd.replace("play", "").replace("on youtube", "").strip()
        if song:
            play_song_on_youtube(song)
        else:
            query = listen_once("Which song, sir?")
            if query:
                play_song_on_youtube(query)
        return True

    # Close window/app
    if cmd.startswith("close "):
        app_name = cmd.replace("close", "", 1).strip()
        if app_name:
            close_window(app_name)
        else:
            speak("Please tell me which application to close, sir.")
        return True

    # Keyboard shortcuts & basic editing
    if handle_keyboard_commands(cmd):
        return True

    return False  # not handled; fall back to AI

def _active_mode_loop():
    """Continuous active-mode loop; listens and handles speech commands."""
    if not SPEECH_AVAILABLE:
        speak("Speech recognition is unavailable, sir.")
        return
    r = sr.Recognizer()
    while not state._stop_active.is_set():
        with sr.Microphone() as source:
            print("🎤 Listening...")
            r.adjust_for_ambient_noise(source, duration=0.4)
            try:
                audio = r.listen(source, timeout=8, phrase_time_limit=10)
                command = r.recognize_google(audio).lower()
                print(f"🗣️ You said: {command}")

                if _handle_parsed_command(command):
                    # command handled or exit/standby; if system turned offline, stop loop
                    if state.system_status != "ONLINE":
                        state._stop_active.set()
                        break
                    continue

                # Fallback to AI if nothing matched
                reply = ask_billion(command)
                print("💬 Billion:", reply)
                speak(reply)

            except sr.WaitTimeoutError:
                speak("No input detected. Returning to standby.")
                break
            except sr.UnknownValueError:
                speak("I did not understand, sir.")
            except sr.RequestError:
                speak("Microphone or network error, sir.")
                break

def _wake_word_loop(vosk_model_path: str):
    """Wake-word detector using Vosk + sounddevice; on 'hey' → speak & start active mode once."""
    if not VOSK_AVAILABLE:
        speak("Wake word detection is unavailable, sir.")
        return

    try:
        model = Model(vosk_model_path)
    except Exception as e:
        print("❌ Error loading Vosk model:", e)
        speak("Failed to load the wake word model, sir.")
        return

    print("🎧 Listening for 'Hey'...")
    q = queue.Queue()
    rec = KaldiRecognizer(model, 16000)

    def callback(indata, frames, time_info, status):
        if status:
            print("⚠️", status)
        q.put(bytes(indata))

    try:
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=callback):
            while not state._stop_wake.is_set():
                data = q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    spoken = result.get("text", "").lower()
                    if not spoken:
                        continue
                    print("🧠 Heard:", spoken)
                    if any(w in spoken for w in state.WAKE_WORDS):
                        speak("Yes, sir.")
                        # Launch a single active-mode session
                        _start_active_mode_background()
                        # optional: brief cooldown to avoid re-trigger
                        time.sleep(2)
    except Exception as e:
        print("❌ Wake loop error:", e)
        speak("Wake word stream failed, sir.")

# ====== Thread start/stop helpers ======
def _start_active_mode_background():
    if state._active_thread and state._active_thread.is_alive():
        return
    state._stop_active.clear()
    state.is_listening = True
    t = threading.Thread(target=_active_mode_loop, daemon=True)
    state._active_thread = t
    t.start()

def _stop_active_mode_background():
    state._stop_active.set()
    state.is_listening = False

def _start_wake_word_background(vosk_model_path: str):
    if not VOSK_AVAILABLE:
        return False
    if state._wake_thread and state._wake_thread.is_alive():
        return True
    state._stop_wake.clear()
    state.is_wake_word_active = True
    t = threading.Thread(target=_wake_word_loop, args=(vosk_model_path,), daemon=True)
    state._wake_thread = t
    t.start()
    return True

def _stop_wake_word_background():
    state._stop_wake.set()
    state.is_wake_word_active = False

# ====== Routes ======
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/command', methods=['POST'])
def handle_command():
    try:
        data = request.get_json()
        command = data.get('command', '').lower().strip()

        if not command:
            return jsonify({"success": False, "error": "No command provided"})

        state.is_processing = True

        # Exit commands
        if any(exit_cmd in command for exit_cmd in state.EXIT_COMMANDS):
            response = "Shutting down. Goodbye, sir."
            state.add_chat_message("JARVIS", response)
            state.system_status = "OFFLINE"
            return jsonify({"success": True, "response": response, "action": "shutdown"})

        # System actions (use your imported helpers where applicable)
        if "open file manager" in command:
            open_file_manager()
            response = "Opening file manager, sir."
            state.add_chat_message("JARVIS", response)
            return jsonify({"success": True, "response": response})

        if "open recycle bin" in command:
            try:
                subprocess.Popen("explorer shell:RecycleBinFolder")
                response = "Opening Recycle Bin, sir."
                state.add_chat_message("JARVIS", response)
                return jsonify({"success": True, "response": response})
            except Exception as e:
                return jsonify({"success": False, "error": f"Failed to open recycle bin: {str(e)}"})

        if "open google" in command:
            open_browser_and_search("google", "What would you like to search, sir?")
            response = "Opening Google, sir."
            state.add_chat_message("JARVIS", response)
            return jsonify({"success": True, "response": response})

        if "open youtube" in command:
            open_browser_and_search("youtube", "What shall I search for on YouTube, sir?")
            response = "Opening YouTube, sir."
            state.add_chat_message("JARVIS", response)
            return jsonify({"success": True, "response": response})

        if "play" in command and "youtube" in command:
            song = command.replace("play", "").replace("on youtube", "").strip()
            if not song:
                # ask once (text flow uses AI fallback otherwise)
                song = " "
            play_song_on_youtube(song)
            response = f"Searching YouTube for {song.strip() or 'your song'}, sir."
            state.add_chat_message("JARVIS", response)
            return jsonify({"success": True, "response": response})

        if command.startswith("close "):
            app_name = command.replace("close", "", 1).strip()
            if app_name:
                close_window(app_name)
                response = f"Attempting to close {app_name}, sir."
                state.add_chat_message("JARVIS", response)
                return jsonify({"success": True, "response": response})

        # Keyboard commands
        if handle_keyboard_commands(command):
            response = "Command executed, sir."
            state.add_chat_message("JARVIS", response)
            return jsonify({"success": True, "response": response})

        # Dev builder (AI-to-AI)
        if any(phrase in command for phrase in ["i want to build", "i want to make", "i went to build", "i need to build", "create a", "make a"]):
            threading.Thread(target=ai_to_ai_problem_solver, args=(command,), daemon=True).start()
            response = "I'll help you with that, sir. Opening the development environment."
            state.add_chat_message("JARVIS", response)
            return jsonify({"success": True, "response": response})

        # Time
        if "time" in command or "what time" in command:
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            response = f"The current time is {current_time}, sir."
            state.add_chat_message("JARVIS", response)
            return jsonify({"success": True, "response": response})

        # Fallback to AI
        ai_response = ask_billion(command)
        state.add_chat_message("JARVIS", ai_response)
        return jsonify({"success": True, "response": ai_response})

    except Exception as e:
        return jsonify({"success": False, "error": f"Command processing error: {str(e)}"})
    finally:
        state.is_processing = False

@app.route('/api/speak', methods=['POST'])
def handle_speak():
    try:
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({"success": False, "error": "No text provided"})

        def speak_async():
            try:
                speak(text)
            except Exception as e:
                print(f"TTS Error: {e}")

        threading.Thread(target=speak_async, daemon=True).start()
        return jsonify({"success": True, "message": "Speech initiated"})
    except Exception as e:
        return jsonify({"success": False, "error": f"TTS error: {str(e)}"})

@app.route('/api/listen', methods=['POST'])
def handle_listen():
    """
    Body:
      { "type": "start_continuous" }  -> starts active speech loop
      { "type": "stop_continuous" }   -> stops active speech loop
      { "type": "start_wake_word", "vosk_model_path": "path/to/vosk-model-small-en-us-0.15" }
      { "type": "stop_wake_word" }
    """
    try:
        data = request.get_json() or {}
        listen_type = data.get('type', 'single')
        vosk_model_path = data.get('vosk_model_path', r".\vosk-model-small-en-us-0.15")

        if listen_type == 'start_continuous':
            if not SPEECH_AVAILABLE:
                return jsonify({"success": False, "error": "Speech recognition not available"})
            _start_active_mode_background()
            return jsonify({"success": True, "message": "Continuous listening started"})

        elif listen_type == 'stop_continuous':
            _stop_active_mode_background()
            return jsonify({"success": True, "message": "Continuous listening stopped"})

        elif listen_type == 'start_wake_word':
            if not VOSK_AVAILABLE:
                return jsonify({"success": False, "error": "Vosk wake-word not available"})
            started = _start_wake_word_background(vosk_model_path)
            if started:
                return jsonify({"success": True, "message": "Wake word detection started"})
            return jsonify({"success": True, "message": "Wake word detection already running"})

        elif listen_type == 'stop_wake_word':
            _stop_wake_word_background()
            return jsonify({"success": True, "message": "Wake word detection stopped"})

        else:
            return jsonify({"success": False, "error": "Invalid listen type"})

    except Exception as e:
        return jsonify({"success": False, "error": f"Listen error: {str(e)}"})

@app.route('/api/status')
def get_status():
    try:
        current_time = datetime.datetime.now().strftime("%I : %M : %S %p")

        # Determine speech recognition status
        if state.is_listening:
            speech_status = "LISTENING"
        elif state.is_wake_word_active:
            speech_status = "WAKE_WORD_ACTIVE"
        elif SPEECH_AVAILABLE:
            speech_status = "READY"
        else:
            speech_status = "OFFLINE"

        return jsonify({
            "success": True,
            "time": current_time,
            "components": {
                "speech_recognition": speech_status,
                "tts": "ONLINE" if SPEECH_AVAILABLE else "OFFLINE",
                "ai": "ONLINE",
                "system": state.system_status
            },
            "processing": state.is_processing
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/speech-status')
def get_speech_status():
    return jsonify({
        "success": True,
        "speech_status": {
            "google_sr_available": SPEECH_AVAILABLE,
            "vosk_available": VOSK_AVAILABLE,
            "tts_available": SPEECH_AVAILABLE
        }
    })

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    try:
        state.chat_history.clear()
        return jsonify({"success": True, "message": "Chat history cleared"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ====== Startup greeting ======
def _greet_on_start():
    try:
        greeting = time_greeting()
        speak(f"{greeting} Always at your service, sir.")
    except Exception as e:
        print("Greeting failed:", e)

if __name__ == '__main__':
    print("🚀 Starting JARVIS Voice Assistant Web Interface...")
    print(f"📊 Speech Recognition: {'✅' if SPEECH_AVAILABLE else '❌'}")
    print(f"🎯 Wake Word Detection: {'✅' if VOSK_AVAILABLE else '❌'}")
    print("🌐 Open http://localhost:5000 in your browser")

    # greet once on boot (non-blocking)
    threading.Thread(target=_greet_on_start, daemon=True).start()

    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
