import customtkinter as ctk
import mido
import threading
import time
import pygame
import os
from tkinter import filedialog

# --- CONFIG v1.3 ---
DRUM_MAP = {36: "KICK", 38: "SNARE", 42: "HI-HAT", 46: "OPEN-H", 48: "TOM 1", 45: "TOM 2", 43: "LOW TOM", 49: "CRASH 1", 57: "CRASH 2", 51: "RIDE"}

class DrumApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Drum Coach v1.3 - Stable Edition")
        self.geometry("900x750")
        pygame.mixer.init()

        self.music_file = None
        self.goal_midi = []
        self.song_start_time = 0
        self.is_playing = False
        self.score = 0
        self.drum_labels = {}

        # UI
        self.header = ctk.CTkLabel(self, text="AI DRUM COACH v1.3", font=("Arial", 28, "bold"))
        self.header.pack(pady=20)

        self.score_label = ctk.CTkLabel(self, text="SCORE: 0", font=("Arial", 48, "bold"), text_color="#2ecc71")
        self.score_label.pack(pady=10)

        self.feedback_label = ctk.CTkLabel(self, text="Load your Drumless MP3 and MIDI Goal", font=("Arial", 18))
        self.feedback_label.pack(pady=5)

        # Drum Grid
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(pady=20)
        cols = 5
        for i, (note, name) in enumerate(DRUM_MAP.items()):
            lbl = ctk.CTkLabel(self.grid_frame, text=name, font=("Arial", 14, "bold"), width=150, height=100, fg_color="#333333", corner_radius=15)
            lbl.grid(row=i//cols, column=i%cols, padx=8, pady=8)
            self.drum_labels[note] = lbl

        # Controls
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=30)
        
        # We focus on loading the TWO files needed for the coach to work
        ctk.CTkButton(self.btn_frame, text="🎵 Load Drumless MP3", command=self.load_music, fg_color="#3498db").grid(row=0, column=0, padx=10)
        ctk.CTkButton(self.btn_frame, text="🎯 Load MIDI Goal", command=self.load_goal, fg_color="#9b59b6").grid(row=0, column=1, padx=10)
        
        self.play_btn = ctk.CTkButton(self.btn_frame, text="▶ START SESSION", command=self.play_music, state="disabled", fg_color="#27ae60", height=40)
        self.play_btn.grid(row=0, column=2, padx=10)
        
        ctk.CTkButton(self.btn_frame, text="⏹ STOP", command=self.stop_music, fg_color="#c0392b").grid(row=0, column=3, padx=10)

        threading.Thread(target=self.listen_to_midi, daemon=True).start()

    def load_music(self):
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav")])
        if path:
            self.music_file = path
            self.feedback_label.configure(text=f"Audio: {os.path.basename(path)}")
            self.check_ready()

    def load_goal(self):
        path = filedialog.askopenfilename(filetypes=[("MIDI", "*.mid")])
        if path:
            mid = mido.MidiFile(path)
            self.goal_midi = []
            current_ms = 0
            for msg in mid:
                current_ms += msg.time * 1000 
                if msg.type == 'note_on' and msg.velocity > 0:
                    self.goal_midi.append({'time': current_ms, 'note': msg.note})
            self.feedback_label.configure(text=f"MIDI Loaded: {len(self.goal_midi)} notes")
            self.check_ready()

    def check_ready(self):
        if self.music_file and self.goal_midi:
            self.play_btn.configure(state="normal")

    def play_music(self):
        pygame.mixer.music.load(self.music_file)
        pygame.mixer.music.play()
        self.song_start_time = time.time()
        self.is_playing = True
        self.score = 0
        self.score_label.configure(text="SCORE: 0")

    def stop_music(self):
        pygame.mixer.music.stop()
        self.is_playing = False

    def listen_to_midi(self):
        with mido.open_input() as inport:
            for msg in inport:
                if msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note in DRUM_MAP:
                        self.process_hit(msg.note)

    def process_hit(self, note):
        now_ms = (time.time() - self.song_start_time) * 1000 if self.is_playing else 0
        
        if self.is_playing and self.goal_midi:
            same_notes = [n for n in self.goal_midi if n['note'] == note]
            if same_notes:
                closest = min(same_notes, key=lambda x: abs(x['time'] - now_ms))
                diff = abs(closest['time'] - now_ms)

                if diff < 40: 
                    self.score += 100
                    self.feedback_label.configure(text="🔥 PERFECT 🔥", text_color="#2ecc71")
                elif diff < 100:
                    self.score += 50
                    self.feedback_label.configure(text="👍 GOOD", text_color="#f1c40f")
                
                self.score_label.configure(text=f"SCORE: {self.score}")

        # Visual Flash
        lbl = self.drum_labels[note]
        color = "#3498db" if note in [42, 46, 49, 57, 51] else "#f39c12"
        lbl.configure(fg_color=color)
        self.after(100, lambda: lbl.configure(fg_color="#333333"))

if __name__ == "__main__":
    app = DrumApp()
    app.mainloop()