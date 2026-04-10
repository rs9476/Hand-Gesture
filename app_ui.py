import tkinter as tk
from tkinter import messagebox
import subprocess
import sys

process = None


def start_app():
    global process
    if process is None:
        process = subprocess.Popen([sys.executable, "main.py"])
        status_label.config(text="Status: RUNNING", fg="green")


def stop_app():
    global process
    if process is not None:
        process.terminate()
        process = None
        status_label.config(text="Status: STOPPED", fg="red")


# UI Window
root = tk.Tk()
root.title("Gesture Controlled System")
root.geometry("500x500")
root.config(bg="#1e1e1e")

# Title
title = tk.Label(
    root,
    text="Gesture Control System",
    font=("Segoe UI", 20, "bold"),
    bg="#1e1e1e",
    fg="white"
)
title.pack(pady=20)

# Buttons Frame
frame = tk.Frame(root, bg="#1e1e1e")
frame.pack(pady=20)

start_btn = tk.Button(
    frame,
    text="START",
    font=("Segoe UI", 14),
    width=10,
    bg="#4CAF50",
    fg="white",
    command=start_app
)
start_btn.grid(row=0, column=0, padx=10)

stop_btn = tk.Button(
    frame,
    text="STOP",
    font=("Segoe UI", 14),
    width=10,
    bg="#f44336",
    fg="white",
    command=stop_app
)
stop_btn.grid(row=0, column=1, padx=10)

# Instructions
instructions = """
Gesture Controls:

1 Finger  → Open YouTube 🌐
2 Fingers → Volume Up 🔊
3 Fingers → Volume Down 🔉
4 Fingers → Mute 🔇
5 Fingers → Lock Screen 🔒
"""

inst_label = tk.Label(
    root,
    text=instructions,
    font=("Segoe UI", 12),
    bg="#1e1e1e",
    fg="lightgray",
    justify="left"
)
inst_label.pack(pady=20)

# Status
status_label = tk.Label(
    root,
    text="Status: STOPPED",
    font=("Segoe UI", 12, "bold"),
    bg="#1e1e1e",
    fg="red"
)
status_label.pack(pady=20)

# Footer
footer = tk.Label(
    root,
    text="AI Gesture System",
    font=("Segoe UI", 10),
    bg="#1e1e1e",
    fg="gray"
)
footer.pack(side="bottom", pady=10)

root.mainloop()