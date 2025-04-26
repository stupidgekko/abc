import cv2
import numpy as np
from PIL import Image, ImageGrab  
import time
from datetime import datetime
from collections import deque
import os
import threading
import customtkinter as ctk
from tkinter import messagebox
import keyboard
import pyaudio
import wave

SCREEN_SIZE = (1280, 720)  
FPS = 15
MAX_DURATION = 60  
OUTPUT_DIR = "recordings" 

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

class ScreenRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CLIPEAWEA")
        self.root.geometry("400x500")  
        self.root.configure(bg="#050003")  
        self.root.resizable(False, False)
        self.root.iconbitmap("icon.ico")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.is_running = True
        self.duration = 15  
        self.clip_key = "0"  
        self.frame_buffer = deque(maxlen=FPS * MAX_DURATION)
        self.recording_thread = None
        self.is_saving = False 
        self.script_active = False  
        self.current_fps = 0  

        # Variables para audio
        self.record_audio = False
        self.record_microphone = False
        self.audio_chunk = 1024
        self.audio_format = pyaudio.paInt16
        self.audio_channels = 2
        self.audio_rate = 44100

        # Frame principal
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=10, fg_color="#101010")
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Configuración de grabación
        self.config_frame = ctk.CTkFrame(self.main_frame, corner_radius=15, fg_color="#1C1C1E")
        self.config_frame.pack(pady=10, fill="x", padx=20)

        self.max_time_label = ctk.CTkLabel(
            self.config_frame,
            text="Max Time:",
            font=("Roboto", 14),
            text_color="#E0E1DD"
        )
        self.max_time_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.max_time_value = ctk.CTkLabel(
            self.config_frame,
            text="None",
            font=("Roboto", 14),
            text_color="#E0E1DD"
        )
        self.max_time_value.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        self.size_label = ctk.CTkLabel(
            self.config_frame,
            text="Size:",
            font=("Roboto", 14),
            text_color="#E0E1DD"
        )
        self.size_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.size_value = ctk.CTkLabel(
            self.config_frame,
            text="720p",
            font=("Roboto", 14),
            text_color="#E0E1DD"
        )
        self.size_value.grid(row=1, column=1, padx=10, pady=5, sticky="e")

        # Slider para duración de clip
        self.clip_duration_frame = ctk.CTkFrame(self.main_frame, corner_radius=15, fg_color="#1C1C1E")
        self.clip_duration_frame.pack(pady=10, fill="x", padx=20)

        self.clip_duration_label = ctk.CTkLabel(
            self.clip_duration_frame,
            text=f"{self.duration}s",
            font=("Roboto", 14),
            text_color="#E0E1DD"
        )
        self.clip_duration_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.clip_duration_slider = ctk.CTkSlider(
            self.clip_duration_frame,
            from_=5,
            to=60,
            number_of_steps=55,
            command=self.update_clip_duration,
            width=200,  # Reducimos el ancho del slider
            fg_color="#370454",
            progress_color="#8A0BD2",
            button_color="#8A0BD2",
            button_hover_color="#370454"
        )
        self.clip_duration_slider.set(self.duration)
        self.clip_duration_slider.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        # Opciones de audio
        self.audio_frame = ctk.CTkFrame(self.main_frame, corner_radius=15, fg_color="#1C1C1E")
        self.audio_frame.pack(pady=10, fill="x", padx=20)

        self.narration_label = ctk.CTkLabel(
            self.audio_frame,
            text="Narration:",
            font=("Roboto", 14),
            text_color="#E0E1DD"
        )
        self.narration_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.narration_slider = ctk.CTkSwitch(
            self.audio_frame,
            text="",
            command=self.toggle_narration,
            onvalue=True,
            offvalue=False,
            progress_color="#8A0BD2",
            button_color="#8A0BD2",
            button_hover_color="#370454",
            switch_width=40,
            switch_height=20
        )
        self.narration_slider.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        self.narration_icon = ctk.CTkLabel(
            self.audio_frame,
            text="🎤",
            font=("Roboto", 20),
            text_color="#fff"
        )
        self.narration_icon.grid(row=0, column=2, padx=10, pady=5, sticky="e")

        self.computer_audio_label = ctk.CTkLabel(
            self.audio_frame,
            text="Computer Audio:",
            font=("Roboto", 14),
            text_color="#E0E1DD"
        )
        self.computer_audio_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.computer_audio_slider = ctk.CTkSwitch(
            self.audio_frame,
            text="",
            command=self.toggle_computer_audio,
            onvalue=True,
            offvalue=False,
            progress_color="#8A0BD2",
            button_color="#8A0BD2",
            button_hover_color="#370454",
            switch_width=40,
            switch_height=20
        )
        self.computer_audio_slider.grid(row=1, column=1, padx=10, pady=5, sticky="e")
        self.computer_audio_icon = ctk.CTkLabel(
            self.audio_frame,
            text="🔊",
            font=("Roboto", 20),
            text_color="#fff"
        )
        self.computer_audio_icon.grid(row=1, column=2, padx=10, pady=5, sticky="e")

        # Toggle para activar/desactivar el script
        self.toggle_frame = ctk.CTkFrame(self.main_frame, corner_radius=15, fg_color="#1C1C1E")
        self.toggle_frame.pack(pady=10, fill="x", padx=20)

        self.toggle_button = ctk.CTkSwitch(
            self.toggle_frame,
            text="Activate Script",
            command=self.toggle_script,
            onvalue=True,
            offvalue=False,
            progress_color="#8A0BD2",
            button_color="#8A0BD2",
            button_hover_color="#370454",
            switch_width=60,
            switch_height=30,
            font=("Roboto", 14)
        )
        self.toggle_button.pack(pady=10)

        # Botón de salida
        self.exit_button = ctk.CTkButton(
            self.main_frame,
            text="Exit",
            font=("Roboto", 14),
            fg_color="#FF453A",
            hover_color="#370454",
            corner_radius=15,
            command=self.on_closing,
            height=40
        )
        self.exit_button.pack(pady=20, fill="x", padx=20)

    def update_clip_duration(self, value):
        self.duration = int(value)
        self.frame_buffer = deque(maxlen=FPS * self.duration)
        self.clip_duration_label.configure(text=f"{self.duration}s")

    def toggle_script(self):
        if self.toggle_button.get():
            self.toggle_button.configure(text="Deactivate Script")
            self.start_recording()
        else:
            self.toggle_button.configure(text="Activate Script")
            self.stop_recording()

    def toggle_narration(self):
        self.record_microphone = self.narration_slider.get()

    def toggle_computer_audio(self):
        self.record_audio = self.computer_audio_slider.get()

    def start_recording(self):
        self.script_active = True
        self.recording_thread = threading.Thread(target=self.record_screen, daemon=True)
        self.recording_thread.start()

    def stop_recording(self):
        self.script_active = False

    def record_screen(self):
        last_time = time.time()
        while self.is_running:
            try:
                screenshot = ImageGrab.grab()
                screenshot = screenshot.resize(SCREEN_SIZE, Image.Resampling.LANCZOS)  

                frame = np.array(screenshot)
                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                self.frame_buffer.append(frame)

                elapsed = time.time() - last_time
                sleep_time = max(1 / FPS - elapsed, 0)
                time.sleep(sleep_time)
                last_time = time.time()

            except Exception as e:
                print(f"Error during recording: {e}")
                break

    def save_video(self):
        output_filename = os.path.join(OUTPUT_DIR, f"clip_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_filename, fourcc, FPS, SCREEN_SIZE)

        for frame in self.frame_buffer:
            out.write(frame)

        out.release()
        self.root.after(0, lambda: messagebox.showinfo("Success", f"Clip saved as {output_filename}"))

    def on_closing(self):
        self.is_running = False
        if self.recording_thread:
            self.recording_thread.join()
        self.root.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = ScreenRecorderApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()