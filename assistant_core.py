import os
import json
import queue
import subprocess
import webbrowser
import datetime
from click import command
import pyttsx3
import speech_recognition as sr
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import pyautogui
import openai
import time
import sys
import pygetwindow as gw
import numpy as np
import cv2
import mss
with mss.mss() as sct:
    print("Detected monitors:", sct.monitors)
import base64
from PIL import ImageGrab

# ========== CONFIG ==========
OPENROUTER_API_KEY = "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"
VOSK_MODEL_PATH = r".\vosk-model-small-en-us-0.15"

WAKE_WORDS = ["hey"]
EXIT_COMMANDS = ["shutdown", "terminate", "exit", "goodbye"]

# ========== SPEAK ==========
def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    for voice in engine.getProperty('voices'):
        if "male" in voice.name.lower() and ("uk" in voice.id.lower() or "english_rp" in voice.id.lower()):
            engine.setProperty('voice', voice.id)
            break
    engine.say(text)
    engine.runAndWait()

# ========== GPT FUNCTION ==========
openai.api_key = OPENROUTER_API_KEY
openai.api_base = "https://openrouter.ai/api/v1"

def ask_billion(message):
    try:
        response = openai.ChatCompletion.create(
            model="mistralai/mistral-7b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Billion, an intelligent British-accented AI assistant. "
                        "Speak with respect and clarity. Address the user as 'sir'. Be short, efficient, and highly responsive."
                    )
                },
                {"role": "user", "content": message}
            ],
            temperature=0.6,
            top_p=0.9
        )
        return response.choices[0].message["content"]
    except Exception as e:
        print("❌ GPT Error:", e)
        return "I'm unable to process that, sir."

# ========== HELPER FUNCTIONS ==========
def time_greeting():
    hour = datetime.datetime.now().hour
    if hour < 12:
        return "Good morning, sir."
    elif hour < 17:
        return "Good afternoon, sir."
    else:
        return "Good evening, sir."

def listen_once(prompt=None):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        if prompt:
            speak(prompt)
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source, timeout=6, phrase_time_limit=6)
            command = r.recognize_google(audio).lower()
            print(f"🗣️ You said: {command}")
            return command
        except:
            speak("No input received, sir.")
            return ""

def open_browser_and_search(site, prompt):
    speak(f"Opening {site}, sir.")
    if "youtube" in site:
        webbrowser.open("https://www.youtube.com")
    else:
        webbrowser.open("https://www.google.com")
    time.sleep(5)
    query = listen_once(prompt)
    if query:
        pyautogui.write(query)
        time.sleep(0.5)
        pyautogui.press("enter")

def play_song_on_youtube(song_name):
    speak(f"Searching YouTube for {song_name}, sir.")
    webbrowser.open(f"https://www.youtube.com/results?search_query={song_name.replace(' ', '+')}")
    time.sleep(5)
    pyautogui.press("tab")
    pyautogui.press("enter")

def open_file_manager():
    speak("Opening file manager, sir.")
    subprocess.Popen("explorer")
    time.sleep(2)
    folder = listen_once("Which folder shall I open, sir?")
    if folder:
        pyautogui.write(folder)
        pyautogui.press("enter")

# ========== KEYBOARD COMMANDS ==========
def handle_keyboard_commands(command):
    actions = {
        "select all": "ctrl+a",
        "copy": "ctrl+c",
        "cut": "ctrl+x",
        "paste": "ctrl+v",
        "delete": "delete",
        "enter": "enter",
        "save": "ctrl+s",
        "undo": "ctrl+z",
        "redo": "ctrl+y",
        "close window": "alt+f4"
    }

    command_handled = False

    for phrase, keys in actions.items():
        if phrase in command:
            speak(f"Executing {phrase}, sir.")
            if "+" in keys:
                pyautogui.hotkey(*keys.split("+"))
            else:
                pyautogui.press(keys)
            command_handled = True
            time.sleep(1)

            # Confirm deletion
            if "delete" in phrase:
                pyautogui.press("enter")
                time.sleep(1)
            break

    return command_handled 

# ========== MAIN LISTENING FUNCTION ==========
def active_mode():
    recognizer = sr.Recognizer()
    while True:
        with sr.Microphone() as source:
            print("🎤 Listening...")
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=10)
                command = recognizer.recognize_google(audio).lower()
                print(f"🗣️ You said: {command}")

                if any(exit in command for exit in EXIT_COMMANDS):
                    speak("Shutting down. Goodbye, sir.")
                    sys.exit(0)

                if "wait" in command or "hold" in command:
                    speak("Standing by, sir.")
                    return

                if "open file manager" in command:
                    open_file_manager()
                    return

                if "open recycle bin" in command:
                    speak("Opening Recycle Bin, sir.")
                    subprocess.Popen("explorer shell:RecycleBinFolder")
                    time.sleep(2)
                    continue

                if any(phrase in command for phrase in ["i want to build", "i want to make", "i went to build", "i need to build", "create a login page", "make a login page"]):
                   ai_to_ai_problem_solver(command)
                   continue


                if "open google" in command:
                    open_browser_and_search("google", "What would you like to search, sir?")
                    continue

                if "open youtube" in command:
                    open_browser_and_search("youtube", "What shall I search for on YouTube, sir?")
                    continue

                if "play" in command and "youtube" in command:
                    song = command.replace("play", "").replace("on youtube", "").strip()
                    play_song_on_youtube(song)
                    continue
                
                if "close" in command:
                   app_name = command.replace("close", "").strip()
                   if app_name:
                      close_window(app_name)
                      continue
                   
                

                if handle_keyboard_commands(command):
                    continue

                reply = ask_billion(command)
                print("💬 Billion:", reply)
                speak(reply)

            except sr.WaitTimeoutError:
                speak("No input detected. Returning to standby.")
                return
            except sr.UnknownValueError:
                speak("I did not understand, sir.")
            except sr.RequestError:
                speak("Microphone error, sir.")
                return


# ========== WAKE WORD LISTENER ==========
def wake_word_loop(model):
    print("🎧 Listening for 'Hey Billion'...")
    q = queue.Queue()
    rec = KaldiRecognizer(model, 16000)

    def callback(indata, frames, time, status):
        if status:
            print("⚠️", status)
        q.put(bytes(indata))

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=callback):
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                spoken = result.get("text", "").lower()
                if not spoken:
                    continue
                print("🧠 Heard:", spoken)
                if any(wake in spoken for wake in WAKE_WORDS):
                    speak("Yes, sir.")
                    active_mode()

# ========== AI PROBLEM SOLVER ==========
def ai_to_ai_problem_solver(user_request):
    import pyperclip
    import re

    speak("One moment, sir. Opening ChatGPT.")
    webbrowser.open("https://chat.openai.com/")
    time.sleep(12)

    # Click into GPT input
        # Focus the GPT input box reliably
    speak("Focusing the input field, sir.")
    time.sleep(2)
    pyautogui.moveTo(650, 720)  # Adjust these coordinates if needed
    pyautogui.click()
    time.sleep(0.5)
    pyautogui.click()  # Double click to ensure it's focused

    # Clear any existing text and type the user's exact request
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("backspace")
    pyautogui.write(user_request, interval=0.01)
    pyautogui.press("enter")
    speak("Sent the request. Waiting for GPT to respond.")
    time.sleep(45)


    # Copy full chat
    pyautogui.click(x=600, y=500)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(1)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(2)

    try:
        full_response = pyperclip.paste()

        # First: try extracting triple-backtick code blocks
        code_blocks = re.findall(r"```(?:\w*\n)?(.*?)```", full_response, re.DOTALL)

        if code_blocks:
            combined_code = "\n\n".join(code_blocks).strip()
        else:
            # Fallback: try to extract indented lines or code-like content
            lines = full_response.splitlines()
            code_lines = [line for line in lines if (
                line.strip().startswith("<") or line.strip().startswith("def ")
                or line.strip().startswith("function ") or line.strip().startswith("class ")
                or line.strip().startswith("#") or line.strip().startswith("import ")
                or line.strip().startswith("const ") or line.strip().startswith("let ")
                or line.strip().startswith("var ") or len(line.strip()) > 30
            )]
            combined_code = "\n".join(code_lines).strip()

        if len(combined_code) < 10:
            speak("Sir, the response didn’t contain clear code.")
            print("⚠️ Full response was:\n", full_response)
            return

    except Exception as e:
        speak("Clipboard error occurred, sir.")
        print("❌ Error:", e)
        return

    # Paste only code into Notepad
    speak("Opening Notepad to paste clean code.")
    subprocess.Popen("notepad.exe")
    time.sleep(2)
    pyautogui.hotkey("alt", "space")
    pyautogui.press("x")
    time.sleep(1)
    pyautogui.write(combined_code, interval=0.004)
    speak("Done pasting the code, sir.")


def close_window(app_name):
    try:
        # get all window titles
        all_windows = gw.getAllTitles()
        
        for title in all_windows:
            if app_name.lower() in title.lower():
                win = gw.getWindowsWithTitle(title)[0]
                win.close()
                speak(f"Closed {app_name}, sir.")
                return

        speak(f"I couldn’t find {app_name}, sir.")
    except Exception as e:
        speak(f"Error while closing {app_name}, sir.")
        print("❌", e)


# ========== MAIN ==========
if __name__ == "__main__":
    try:
        model = Model(VOSK_MODEL_PATH)
        speak(f"{time_greeting()} Always at your service, Sir.")
        wake_word_loop(model)
    except Exception as e:
        print("❌ Error loading model:", e)
