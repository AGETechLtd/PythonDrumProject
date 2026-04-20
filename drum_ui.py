import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import requests
import json
import re
import time
import sqlite3
import os
import pygame

# --- CONFIGURATION ---
N8N_URL = "https://autotuto.app.n8n.cloud/webhook-test/a44c387d-f012-49d4-86a2-c7ec43c6774a"
DB_NAME = 'drum_coach.db'
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400
LANE_HEIGHT = 60
PLAYHEAD_X = 100 # Where the sound triggers

# --- AUDIO & DB ENGINE (Same as before) ---
def init_audio():
    pygame.mixer.init()
    sounds = {}
    try:
        sounds["kick"] = pygame.mixer.Sound("kick.wav")
        sounds["snare"] = pygame.mixer.Sound("snare.wav")
        sounds["closed-hi-hat"] = pygame.mixer.Sound("Closed-Hi-Hat.wav")
        sounds["hi-hat"] = sounds["closed-hi-hat"]
        sounds["hihat"] = sounds["closed-hi-hat"]
        return sounds
    except: return None

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, bpm INTEGER, json_data TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)')
    conn.close()

def save_to_db(name, bpm, data):
    conn = sqlite3.connect(DB_NAME)
    conn.execute('INSERT INTO scores (name, bpm, json_data) VALUES (?, ?, ?)', (name, bpm, json.dumps(data)))
    conn.commit()
    conn.close()

# --- ANIMATED VISUALIZER ---
def play_with_animation(drum_data):
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("🥁 Drum Coach Visualizer")
    clock = pygame.time.Clock()
    samples = init_audio()
    
    events = drum_data.get('events', [])
    bpm = drum_data.get('metadata', {}).get('bpm', 60)
    
    # Speed of scrolling (pixels per millisecond)
    # Adjust this to make the notes spread out more or less
    pixels_per_ms = 0.3 

    # Lane Mapping
    lane_map = {"kick": 1, "snare": 2, "hi-hat": 3, "hihat": 3, "closed-hi-hat": 3}
    colors = {"kick": (255, 87, 51), "snare": (51, 255, 87), "hi-hat": (51, 153, 255)}

    running = True
    start_time = pygame.time.get_ticks()
    played_indices = set()

    while running:
        current_time = pygame.time.get_ticks() - start_time
        screen.fill((30, 30, 30)) # Dark Background

        # 1. Handle Events (Audio Triggering)
        for i, event in enumerate(events):
            if i not in played_indices and current_time >= event['timestamp_ms']:
                for part in event['parts']:
                    if samples and part in samples:
                        samples[part].play()
                played_indices.add(i)

        # 2. Draw Lanes
        for name, idx in [("KICK", 1), ("SNARE", 2), ("HI-HAT", 3)]:
            y = idx * 100
            pygame.draw.line(screen, (70, 70, 70), (0, y), (SCREEN_WIDTH, y), 2)
            # Label
            font = pygame.font.SysFont("Arial", 16)
            txt = font.render(name, True, (200, 200, 200))
            screen.blit(txt, (10, y - 25))

        # 3. Draw Playhead (The "Trigger" line)
        pygame.draw.line(screen, (255, 255, 255), (PLAYHEAD_X, 50), (PLAYHEAD_X, 350), 3)

        # 4. Draw Moving Notes
        for event in events:
            # Calculate X position based on time
            # x = Playhead + (NoteTime - CurrentTime) * Speed
            note_x = PLAYHEAD_X + (event['timestamp_ms'] - current_time) * pixels_per_ms
            
            if 0 < note_x < SCREEN_WIDTH:
                for part in event['parts']:
                    lane_idx = lane_map.get(part, 3)
                    color = colors.get(part if part in colors else "hi-hat")
                    pygame.draw.rect(screen, color, (note_x - 10, lane_idx * 100 - 15, 20, 30))

        # 5. Check for Exit
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # End of song check
        if current_time > events[-1]['timestamp_ms'] + 2000:
            running = False

        pygame.display.flip()
        clock.tick(60) # 60 FPS for smooth scrolling

    pygame.quit()

# --- MATH ENGINE ---
def grid_to_drum_json(grid_text):
    bpm_match = re.search(r"BPM:\s*(\d+)", grid_text)
    bpm = int(bpm_match.group(1)) if bpm_match else 60
    ms_per_quarter = 60000 / bpm
    ms_per_eighth = ms_per_quarter / 2
    ms_per_measure = ms_per_quarter * 4
    events = []
    lines = grid_text.strip().split('\n')
    current_measure = 1
    last_beat_multiplier = 0
    for line in lines:
        line = line.strip()
        if "Measure" in line:
            m = re.search(r"Measure\s*(\d+)", line)
            if m: current_measure = int(m.group(1))
            continue
        if "]:" in line:
            slot, insts = line.split("]:")
            parts = [i.strip().lower().replace(" ", "-") for i in insts.split("+")]
            if "[1]" in slot: m = 0
            elif "[2]" in slot: m = 1
            elif "[3]" in slot: m = 2
            elif "[4]" in slot: m = 3
            elif "[&]" in slot:
                ts = ((current_measure - 1) * ms_per_measure) + (last_beat_multiplier * ms_per_quarter) + ms_per_eighth
                events.append({"timestamp_ms": int(ts), "parts": parts, "measure": current_measure})
                continue
            else: continue
            last_beat_multiplier = m
            ts = ((current_measure - 1) * ms_per_measure) + (m * ms_per_quarter)
            events.append({"timestamp_ms": int(ts), "parts": parts, "measure": current_measure})
    return {"metadata": {"bpm": bpm}, "events": events}

# --- UI WRAPPERS ---
def select_and_upload():
    path = filedialog.askopenfilename()
    if not path: return
    name = simpledialog.askstring("Name", "Name this song:", initialvalue=os.path.basename(path).split('.')[0])
    if not name: return
    try:
        resp = requests.post(N8N_URL, files={'data': (path, open(path, 'rb'), 'image/png')})
        if resp.status_code == 200:
            data = grid_to_drum_json(resp.json().get('grid', resp.text))
            save_to_db(name, data['metadata']['bpm'], data)
            play_with_animation(data)
    except Exception as e: messagebox.showerror("Error", str(e))

def open_library():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.execute('SELECT id, name, bpm, json_data FROM scores ORDER BY created_at DESC').fetchall()
    conn.close()
    if not rows: return
    lib_win = tk.Toplevel(root)
    lb = tk.Listbox(lib_win, width=40, height=15)
    lb.pack()
    for r in rows: lb.insert(tk.END, f"{r[0]}: {r[1]} ({r[2]} BPM)")
    def play_lib():
        sel = lb.curselection()
        if sel:
            idx = sel[0]
            play_with_animation(json.loads(rows[idx][3]))
    tk.Button(lib_win, text="Play Selected", command=play_lib).pack()

# --- MAIN ---
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    root.title("Drum Coach AI")
    tk.Button(root, text="📤 Upload & Convert", command=select_and_upload, bg="green", fg="white", width=30, pady=10).pack(pady=10)
    tk.Button(root, text="📚 Open Library", command=open_library, bg="blue", fg="white", width=30, pady=10).pack(pady=10)
    root.mainloop()