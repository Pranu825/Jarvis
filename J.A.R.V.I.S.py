import os
import subprocess
import pyautogui
import pyttsx3
import speech_recognition as sr
import serial
import socket
import open3d as o3d
import threading
import psutil
import time
import mediapipe as mp
import math
import requests
import json
import cv2

# -------------------- Settings --------------------
GEMINI_API_KEY = "AIzaSyAlo9_nqpO8ESSH0vUuRzMawm6MKYDL_Vk"
ARDUINO_PORT = 'COM3'  # Change if needed
ARDUINO_BAUD = 9600
PASSWORD = "2324"  # Set your password
TCP_PORT = 9999
TCP_HOST = '0.0.0.0'  # Accept from any device

# -------------------- Initialize --------------------
engine = pyttsx3.init()
arduino = None
try:
    arduino = serial.Serial(ARDUINO_PORT, ARDUINO_BAUD, timeout=1)
except:
    pass
r = sr.Recognizer()

# -------------------- Helper Functions --------------------
def speak(text):
    print(f"Jarvis: {text}")
    engine.say(text)
    engine.runAndWait()

def listen():
    with sr.Microphone() as source:
        audio = r.listen(source)
        try:
            query = r.recognize_google(audio)
            return query.lower()
        except:
            return ""

def open_app(app_name):
    try:
        if "chrome" in app_name:
            os.system("start chrome")
        elif "notepad" in app_name:
            os.system("start notepad")
        elif "word" in app_name:
            os.system("start winword")
        elif "explorer" in app_name:
            os.system("start explorer")
        else:
            speak("App not recognized.")
    except Exception as e:
        speak(f"Failed to open: {e}")

def system_control(command):
    if "shutdown" in command:
        os.system("shutdown /s /t 1")
    elif "restart" in command:
        os.system("shutdown /r /t 1")
    elif "battery" in command:
        battery = psutil.sensors_battery()
        speak(f"Battery is at {battery.percent} percent")

def control_mouse(action):
    if "left" in action:
        pyautogui.moveRel(-100, 0)
    elif "right" in action:
        pyautogui.moveRel(100, 0)
    elif "up" in action:
        pyautogui.moveRel(0, -100)
    elif "down" in action:
        pyautogui.moveRel(0, 100)
    elif "click" in action:
        pyautogui.click()

def arduino_control(cmd):
    if arduino:
        arduino.write((cmd + '\n').encode())
    else:
        speak("Arduino not connected.")

def gemini_chat(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, headers=headers, params=params, json=data)
    if response.ok:
        reply = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return reply
    else:
        return "Failed to connect to Gemini."

def open_3d_project(filepath):
    mesh = o3d.io.read_triangle_mesh(filepath)
    o3d.visualization.draw_geometries([mesh])

def modify_3d_project(filepath, action):
    mesh = o3d.io.read_triangle_mesh(filepath)
    if "color" in action:
        mesh.paint_uniform_color([1, 0, 0])  # red
    elif "crop" in action:
        bbox = mesh.get_axis_aligned_bounding_box()
        cropped = mesh.crop(bbox)
        mesh = cropped
    o3d.visualization.draw_geometries([mesh])

def tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((TCP_HOST, TCP_PORT))
    server.listen()
    print(f"[TCP Server] Listening on port {TCP_PORT}")
    while True:
        client, addr = server.accept()
        data = client.recv(1024).decode()
        if "open" in data:
            open_app(data.replace("open ", ""))
        elif "shutdown" in data:
            system_control("shutdown")
        client.close()

def hand_tracking_mouse():
    mpHands = mp.solutions.hands
    hands = mpHands.Hands(max_num_hands=1)
    mpDraw = mp.solutions.drawing_utils
    cap = cv2.VideoCapture(0)

    screenWidth, screenHeight = pyautogui.size()

    while True:
        success, img = cap.read()
        if not success:
            continue

        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(imgRGB)

        if results.multi_hand_landmarks:
            for handLms in results.multi_hand_landmarks:
                lmList = []
                for id, lm in enumerate(handLms.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lmList.append((cx, cy))
                if lmList:
                    x, y = lmList[8]  # Index finger tip
                    screen_x = screenWidth * (x / w)
                    screen_y = screenHeight * (y / h)
                    pyautogui.moveTo(screen_x, screen_y)
                mpDraw.draw_landmarks(img, handLms, mpHands.HAND_CONNECTIONS)

        cv2.imshow("Hand Tracking Mouse", img)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

# -------------------- Main JARVIS --------------------
def main():
    # Password Authentication
    password = input("Enter Password: ")
    if password != PASSWORD:
        print("Access Denied.")
        exit()

    speak("Welcome back Boss. Jarvis is now Online.")

    # Start TCP server in background
    threading.Thread(target=tcp_server, daemon=True).start()

    # Start Webcam Hand Tracking Mouse control in background
    threading.Thread(target=hand_tracking_mouse, daemon=True).start()

    while True:
        speak("How can I help you?")
        query = listen()
        print(f"You said: {query}")

        if "open" in query:
            open_app(query)
        elif "shutdown" in query or "restart" in query or "battery" in query:
            system_control(query)
        elif "move" in query or "click" in query:
            control_mouse(query)
        elif "light on" in query:
            arduino_control("LIGHT_ON")
        elif "light off" in query:
            arduino_control("LIGHT_OFF")
        elif "chat" in query:
            speak("What should I ask?")
            user_input = listen()
            response = gemini_chat(user_input)
            speak(response)
        elif "open project" in query:
            speak("Tell me the 3D project filename in assets.")
            filename = listen()
            open_3d_project(f"assets/{filename}")
        elif "modify project" in query:
            speak("Tell me the filename.")
            filename = listen()
            speak("What modification?")
            action = listen()
            modify_3d_project(f"assets/{filename}", action)
        elif "exit" in query or "sleep" in query:
            speak("Going to sleep. Goodbye.")
            break
        else:
            speak("Command not recognized.")

# -------------------- Auto Start --------------------
if __name__ == "__main__":
    main()