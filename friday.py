import speech_recognition as sr
import webbrowser
import pyttsx3
from datetime import datetime
import musiclibrary
from dotenv import load_dotenv
import os
import time
import threading
import ollama

# === Setup ===
r = sr.Recognizer()
ai_is_speaking = threading.Lock()
client = ollama.Client(host='http://localhost:11434') 
def speak(text):
    """Smooth & quick TTS."""
    print(f"[Friday says]: {text}")
    engine = pyttsx3.init('sapi5')
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id)
    engine.setProperty('rate', 190)
    engine.say(text)
    engine.runAndWait()
    engine.stop()
    time.sleep(0.15)
def greet_user():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        speak("Jai Shree Krishna, How can I help you today?")
    elif 12 <= hour < 17:
        speak("Jai Shree Krishna, what's up boss?")
    elif 17 <= hour < 21:
        speak("Jai Shree Krishna, whats wrong?")
    else:
        speak("Jai Shree Krishna, how its going?")

#ollama aichatbot
def ask_ollama(prompt):
    def _ask():
        lock_acquired = ai_is_speaking.acquire(blocking=False)
        
       
        if not lock_acquired:
             return 

        try:
            stream = client.chat(
                model='llama3:8b-instruct-q4_0', 
                messages=[
                    {
                        "role": "system",
                        "content": "You are Friday, a friendly AI voice assistant. Respond concisely and clearly. Keep answers under 20 words."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                stream=True,
                options={
                    'temperature': 0.7,
                    'top_p': 0.8
                }
            )

            full_answer = ""
            
            # 2. Process the stream and collect the full answer
            for chunk in stream:
                content = chunk['message']['content']
                if content:
                    full_answer += content
            
            # 3. Speak the final answer
            final_text = full_answer.strip()
            speak(final_text)
            print("[Friday AI Response]:", final_text)

        except Exception as e:
            # Catch errors like ConnectionError or ResponseError
            print("Ollama Error:", e)
            # IMPORTANT: We speak the error to the user *before* releasing the lock
            speak("Sorry boss, Ollama server may not be running or the model is busy.")
            
        finally:
            if ai_is_speaking.locked():
                ai_is_speaking.release()

    threading.Thread(target=_ask, daemon=True).start()
    time.sleep(0.1)
# === Command Processor ===
def close_app(app_name, display_name):
    """Safely closes an app if running."""
    command = f'taskkill /f /im "{app_name}"'
    if os.system(command) == 0:
        speak(f"Closing {display_name}.")
    else:
        speak(f"{display_name} wasn't running, boss.")


def processcommand(c):
    c = c.lower().strip()
    print(f"[Command received]: {c}")
    # --- Command dictionary (fast lookup) ---
    commands = {
        "open google": lambda: (speak("Opening Google"), webbrowser.open("https://google.com")),
        "open instagram": lambda: (speak("Opening Instagram."), webbrowser.open("https://www.instagram.com")),
        "open youtube": lambda: (speak("Opening YouTube."), webbrowser.open("https://www.youtube.com")),
        "open chat gpt": lambda: (speak("Opening ChatGPT."), webbrowser.open("https://chat.openai.com")),
        "open whatsapp": lambda: (speak("Opening WhatsApp Web."), webbrowser.open("https://web.whatsapp.com")),
        "open settings": lambda: (speak("Opening Settings."), os.system("start ms-settings:")),
        "close settings": lambda: close_app("SystemSettings.exe", "Settings"),
        "close chrome": lambda: close_app("chrome.exe", "Chrome"),
        "open calculator": lambda: (speak("Opening Calculator."), os.system("start calc")),
        "close calculator": lambda: close_app("CalculatorApp.exe", "Calculator"),
        "shutdown": lambda: (speak("Shutting down in 5 seconds."), os.system("shutdown /s /t 5")),
        "restart": lambda: (speak("Restarting your system."), os.system("shutdown /r /t 5")),
    }

    # --- Instant command match ---
    for key, action in commands.items():
        if key in c:
            action()
            return "continue"

    # --- Music playback ---
    if c.startswith("play "):
        song = c.split(" ", 1)[1]
        if song in musiclibrary.music:
            speak(f"Playing {song}")
            webbrowser.open(musiclibrary.music[song])
        else:
            speak("Sorry, I couldn’t find that song.")
        return "continue"

    # --- Time info ---
    if "time" in c:
        speak("It's " + datetime.now().strftime("%I:%M %p"))
        return "continue"

    # --- Personal commands ---
    if "who is your boss" in c:
        speak("My boss is Dhruv.")
        return "continue"
    if "who is ashok" in c:
        speak("father of my boss")
        return "continue" # ADDED: Return to prevent fallback
    
    if any(name in c for name in ["who is seema", "who is cima", "who is sima"]):
        speak("mother of my boss")
        return "continue"
    
    if "who is aishwarya" in c:
        speak("sister of my boss")
        return "continue"
    if any(x in c for x in ["who are you", "what are you", "tell me about yourself"]):
        speak("I’m Friday, made by Dhruv, your personal assistant.")
        return "continue"
    if "radhe radhe" in c:
        speak("Radhe Radhe boss.")
        return "continue"
    if "jay shri krishna" in c or "jai shree krishna"  in c:
        speak("Jai Shree Krishna.")
        return "continue"
 
    # --- Sleep or Exit ---
    if any(x in c for x in ["stop", "sleep", "exit", "good bye"]):
        speak("Going to sleep. Jai Shree Krishna.")
        return "sleep"

    # --- Fallback to Ollama AI ---
    threading.Thread(target=ask_ollama, args=(c,), daemon=True).start()
    speak("Thinking...")
    return "continue"

# === Main Program ===
if __name__ == "__main__":
    speak("Initializing Friday...")
    greet_user()

    with sr.Microphone() as source:
        print("Calibrating mic for background noise...")
        r.adjust_for_ambient_noise(source, duration=1)
        r.energy_threshold = 250
        r.dynamic_energy_threshold = False

    active = False  # whether Friday is in active listening mode

    while True:
        if ai_is_speaking.locked():
            time.sleep(0.5) # Sleep briefly to avoid continuous cycling
            continue
        try:
            with sr.Microphone() as source:
                print("🎧 Listening...")
                audio = r.listen(source, timeout=4, phrase_time_limit=3)
            text = r.recognize_google(audio).lower()
            print(f"Heard: {text}")

            # Wake word
            if "friday" in text:
                active = True
                speak("Yes boss")
                continue

            # Continuous mode
            if active:
                result = processcommand(text)
                if result == "sleep":
                    active = False
                    continue

        except sr.UnknownValueError:
            continue
        except sr.WaitTimeoutError:
            continue
        except sr.RequestError:
            speak("Speech recognition service error.")
        except Exception as e:
            print("Error:", e)
