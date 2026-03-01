import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import ctypes
import threading
import zipfile
import time
import struct
import logging
from datetime import datetime

# --- THEME CONSTANTS (Bloxstrap Inspired) ---
BG_COLOR = "#111111"
SECONDARY_BG = "#1a1a1a"
ACCENT_COLOR = "#0078d7"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#aaaaaa"
SUCCESS_COLOR = "#28a745"
ERROR_COLOR = "#dc3545"

# --- EMBEDDED SCRIPTS (EXPANDED & ROBUST) ---
# This code is written to auto_font_manager.py and runs in the background.
AUTO_MANAGER_CODE = r'''
import os
import sys
import json
import shutil
import ctypes
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont, filedialog
from datetime import datetime
from ctypes import wintypes
import time
import hashlib

# --- Dependency Check ---
try:
    import psutil
except ImportError:
    sys.exit(1)

# ---------------- CONFIG & THEME ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
APP_NAME = "Roblox Font & Cursor Manager"
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
FONTS_LIB_DIR = os.path.join(BASE_DIR, "Fonts")
CURSORS_LIB_DIR = os.path.join(BASE_DIR, "Cursors")
LOG_FILE = os.path.join(BASE_DIR, "manager.log")

BG_COLOR = "#111111"
SECONDARY_BG = "#1a1a1a"
ACCENT_COLOR = "#0078d7"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#aaaaaa"

ROBLOX_URI = "roblox-player:"
HOTKEY_ID = 1
MOD_CONTROL = 0x0002

KEYS_MAP = {
    "F9": (0, 0x78),
    "F10": (0, 0x79),
    "F11": (0, 0x7A),
    "Ctrl + Grave (`)": (MOD_CONTROL, 0xC0)
}

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

def get_file_hash(filepath):
    """Verifies file integrity using SHA-256."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

def load_config():
    defaults = {"font": None, "cursor_set": None, "show_on_start": True, "hotkey": "F9"}
    if not os.path.exists(CONFIG_FILE):
        return defaults
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in defaults.items():
                if k not in data: data[k] = v
            return data
    except:
        return defaults

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

# ---------------- ROBLOX UTILS ---------------- #

def get_roblox_version_paths():
    paths = [
        os.path.join(os.getenv("LOCALAPPDATA"), "Roblox", "Versions"),
        os.path.join(os.getenv("ProgramFiles(x86)"), "Roblox", "Versions"),
        os.path.join(os.getenv("ProgramFiles"), "Roblox", "Versions")
    ]
    valid_versions = []
    for p in paths:
        if os.path.exists(p):
            for d in os.listdir(p):
                full = os.path.join(p, d)
                if os.path.isdir(full) and d.startswith("version-"):
                    # Check if it contains the content folder
                    if os.path.exists(os.path.join(full, "content")):
                        valid_versions.append(full)
    return valid_versions

def restart_roblox():
    log("Requesting Roblox Restart")
    found = False
    for proc in psutil.process_iter(['name']):
        try:
            pname = proc.name().lower()
            if "roblox" in pname and not any(x in pname for x in ["manager", "crash", "launcher"]):
                proc.terminate()
                found = True
        except: continue
    if found: time.sleep(2)
    subprocess.Popen(["cmd", "/c", "start", ROBLOX_URI], shell=True)

def apply_font(font_path):
    log(f"Applying Font: {font_path}")
    versions = get_roblox_version_paths()
    if not versions:
        log("No Roblox versions found to apply fonts to.")
        return False

    success = False
    for v_path in versions:
        font_dir = os.path.join(v_path, "content", "fonts")
        if os.path.exists(font_dir):
            backup_dir = os.path.join(font_dir, "Fonts.old")
            os.makedirs(backup_dir, exist_ok=True)
            for f in os.listdir(font_dir):
                if f.lower().endswith((".ttf", ".otf")) and not f.lower().startswith("twemoji"):
                    src = os.path.join(font_dir, f)
                    back = os.path.join(backup_dir, f)
                    try:
                        if not os.path.exists(back): 
                            shutil.move(src, back)
                        
                        # Added: Atomic-style Replacement (Safe Write)
                        temp_path = src + ".tmp"
                        shutil.copy2(font_path, temp_path)
                        os.replace(temp_path, src)
                        success = True
                    except PermissionError as pe:
                        log(f"Permission error (File in use?) applying font {f}: {pe}")
                    except Exception as e:
                        log(f"Failed to apply font to {f}: {e}")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
    return success

def apply_cursor_set(set_path):
    log(f"Applying Cursor Set: {set_path}")
    versions = get_roblox_version_paths()
    c_files = ["ArrowCursor.png", "ArrowFarCursor.png", "IBeamCursor.png", "MouseLockedCursor.png", "MouseLockedCursor@2x.png"]
    
    success = False
    for v_path in versions:
        cursor_dir = os.path.join(v_path, "content", "textures", "Cursors", "KeyboardMouse")
        if os.path.exists(cursor_dir):
            backup_dir = os.path.join(cursor_dir, "Cursors.old")
            os.makedirs(backup_dir, exist_ok=True)
            for cf in c_files:
                lib_file = os.path.join(set_path, cf)
                target = os.path.join(cursor_dir, cf)
                if os.path.exists(lib_file):
                    try:
                        if os.path.exists(target) and not os.path.exists(os.path.join(backup_dir, cf)):
                            shutil.move(target, os.path.join(backup_dir, cf))
                        
                        # Added: Atomic-style Replacement
                        temp_path = target + ".tmp"
                        shutil.copy2(lib_file, temp_path)
                        os.replace(temp_path, target)
                        success = True
                    except PermissionError as pe:
                        log(f"Permission error (File in use?) applying cursor {cf}: {pe}")
                    except Exception as e:
                        log(f"Failed to apply cursor {cf}: {e}")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
    return success

def restore_defaults():
    log("Restoring Defaults")
    versions = get_roblox_version_paths()
    for v_path in versions:
        # Restore Fonts
        f_old = os.path.join(v_path, "content", "fonts", "Fonts.old")
        if os.path.exists(f_old):
            f_dest = os.path.join(v_path, "content", "fonts")
            for f in os.listdir(f_old):
                try: shutil.move(os.path.join(f_old, f), os.path.join(f_dest, f))
                except: pass
            shutil.rmtree(f_old)
            
        # Restore Cursors
        c_old = os.path.join(v_path, "content", "textures", "Cursors", "KeyboardMouse", "Cursors.old")
        if os.path.exists(c_old):
            c_dest = os.path.join(v_path, "content", "textures", "Cursors", "KeyboardMouse")
            for f in os.listdir(c_old):
                try: shutil.move(os.path.join(c_old, f), os.path.join(c_dest, f))
                except: pass
            shutil.rmtree(c_old)

# ---------------- MAIN UI ---------------- #

class ManagerUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("800x650")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)

        self.cfg = load_config()
        self.trigger_show = False
        self.all_fonts = {}
        self.all_cursor_sets = {}
        self.image_cache = [] # Cache for cursor preview images
        
        # State tracking for Auto-Updates
        self.known_versions = set(get_roblox_version_paths())
        self.prompt_active = False
        self.waiting_for_close = False
        self.prev_run = False
        
        # EXPLICIT MASTER PASSED TO PREVENT NAMESPACE DETACHMENT
        self.font_var = tk.StringVar(self, value=self.cfg.get("font"))
        self.cursor_var = tk.StringVar(self, value=self.cfg.get("cursor_set"))
        self.hotkey_var = tk.StringVar(self, value=self.cfg.get("hotkey", "F9"))
        self.show_var = tk.BooleanVar(self, value=not self.cfg.get("show_on_start", True))
        self.search_var = tk.StringVar(self)
        self.cur_hotkey_val = self.cfg.get("hotkey", "F9")

        self.style_ui()
        self.create_widgets()
        self.refresh_libraries()
        self.protocol("WM_DELETE_WINDOW", self.hide)
        
        threading.Thread(target=self.hotkey_loop, daemon=True).start()
        self.check_hotkey_trigger()
        self.check_roblox_process()

    def style_ui(self):
        s = ttk.Style(self)
        s.theme_use('clam')
        s.configure("Accent.TButton", padding=10, background=ACCENT_COLOR, foreground="white", font=("Segoe UI", 10, "bold"))
        s.map("Accent.TButton", background=[('active', '#005a9e')])

    def create_widgets(self):
        sidebar = tk.Frame(self, bg=SECONDARY_BG, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="FONTS+", fg=ACCENT_COLOR, bg=SECONDARY_BG, font=("Segoe UI", 22, "bold")).pack(pady=40)

        self.container = tk.Frame(self, bg=BG_COLOR)
        self.container.pack(side="right", fill="both", expand=True)

        for name in ["Dashboard", "Settings", "Diagnostics"]:
            btn = tk.Button(sidebar, text=name, bg=SECONDARY_BG, fg=TEXT_SECONDARY, bd=0, 
                            font=("Segoe UI", 12), activebackground=BG_COLOR, activeforeground=TEXT_PRIMARY,
                            padx=30, anchor="w", command=lambda n=name: self.show_page(n))
            btn.pack(fill="x", pady=2)

        self.show_page("Dashboard")

    def show_page(self, name):
        for w in self.container.winfo_children(): w.destroy()
        tk.Label(self.container, text=name, font=("Segoe UI", 26, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack(anchor="w", padx=40, pady=(40, 20))
        
        page = tk.Frame(self.container, bg=BG_COLOR)
        page.pack(fill="both", expand=True, padx=40)

        if name == "Dashboard":
            # Search
            s_frame = tk.Frame(page, bg=BG_COLOR)
            s_frame.pack(fill="x", pady=(0, 25))
            tk.Label(s_frame, text="Search:", bg=BG_COLOR, fg=TEXT_SECONDARY).pack(side="left")
            ent = tk.Entry(s_frame, textvariable=self.search_var, bg=SECONDARY_BG, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY, bd=0)
            ent.pack(side="left", fill="x", expand=True, padx=10, ipady=4)
            ent.bind("<KeyRelease>", lambda e: self.refresh_libraries())

            tk.Label(page, text="Selected Font", bg=BG_COLOR, fg=TEXT_SECONDARY, font=("Segoe UI", 10)).pack(anchor="w")
            self.f_cb = ttk.Combobox(page, textvariable=self.font_var, state="readonly")
            self.f_cb.pack(fill="x", pady=(5, 20))

            tk.Label(page, text="Selected Cursor Set", bg=BG_COLOR, fg=TEXT_SECONDARY, font=("Segoe UI", 10)).pack(anchor="w")
            self.c_cb = ttk.Combobox(page, textvariable=self.cursor_var, state="readonly")
            self.c_cb.pack(fill="x", pady=(5, 10))
            self.c_cb.bind("<<ComboboxSelected>>", self.update_cursor_preview)
            
            # Cursor Preview Frame
            self.cursor_preview_frame = tk.Frame(page, bg=SECONDARY_BG, padx=10, pady=10)
            self.cursor_preview_frame.pack(fill="x", pady=(0, 20))

            self.st_lbl = tk.Label(page, text="Ready", bg=BG_COLOR, fg=TEXT_SECONDARY, font=("Segoe UI", 10, "italic"))
            self.st_lbl.pack(pady=10)

            btns = tk.Frame(page, bg=BG_COLOR)
            btns.pack(side="bottom", fill="x", pady=20)
            ttk.Button(btns, text="Apply Changes", style="Accent.TButton", command=self.apply).pack(side="right", padx=5)
            ttk.Button(btns, text="Restart Roblox", command=restart_roblox).pack(side="right")
            ttk.Button(btns, text="Restore Default", command=self.restore).pack(side="left")
            
            # Init preview if a cursor is already selected
            self.update_cursor_preview()
            self.refresh_libraries() # Fix for tab switching missing library

        elif name == "Settings":
            tk.Label(page, text="Activation Hotkey", bg=BG_COLOR, fg=TEXT_SECONDARY).pack(anchor="w")
            h_cb = ttk.Combobox(page, textvariable=self.hotkey_var, values=list(KEYS_MAP.keys()), state="readonly")
            h_cb.pack(fill="x", pady=(5, 20))
            h_cb.bind("<<ComboboxSelected>>", self.on_hotkey_change)

            tk.Checkbutton(page, text="Silence launch (Do not show on Roblox start)", variable=self.show_var, 
                           bg=BG_COLOR, fg=TEXT_PRIMARY, selectcolor=SECONDARY_BG, activebackground=BG_COLOR).pack(anchor="w")

        elif name == "Diagnostics":
            txt = scrolledtext.ScrolledText(page, bg=SECONDARY_BG, fg=TEXT_PRIMARY, font=("Consolas", 9), bd=0)
            txt.pack(fill="both", expand=True)
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f: txt.insert("1.0", f.read())
            txt.see("end")

    def update_cursor_preview(self, event=None):
        if not hasattr(self, 'cursor_preview_frame') or not self.cursor_preview_frame.winfo_exists():
            return
            
        for widget in self.cursor_preview_frame.winfo_children():
            widget.destroy()
        self.image_cache.clear()

        sc = self.cursor_var.get()
        if sc and sc in self.all_cursor_sets:
            set_path = self.all_cursor_sets[sc]
            c_files = ["ArrowCursor.png", "ArrowFarCursor.png", "IBeamCursor.png", "MouseLockedCursor.png", "MouseLockedCursor@2x.png"]
            
            for cf in c_files:
                img_path = os.path.join(set_path, cf)
                if os.path.exists(img_path):
                    try:
                        img = tk.PhotoImage(master=self.cursor_preview_frame, file=img_path)
                        img = img.zoom(2, 2)  # Make it big
                        self.image_cache.append(img)
                        tk.Label(self.cursor_preview_frame, image=img, bg=SECONDARY_BG).pack(side="left", padx=15)
                    except Exception:
                        pass
        else:
            tk.Label(self.cursor_preview_frame, text="No preview available.", bg=SECONDARY_BG, fg=TEXT_SECONDARY, font=("Segoe UI", 9, "italic")).pack(side="left")

    def refresh_libraries(self):
        q = self.search_var.get().lower()
        self.all_fonts = {}
        
        # Deep walk fonts to match FontChooserApp accuracy
        if os.path.exists(FONTS_LIB_DIR):
            for root, dirs, files in os.walk(FONTS_LIB_DIR):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf')):
                        rel = os.path.relpath(os.path.join(root, f), FONTS_LIB_DIR).replace("\\", "/")
                        if not q or q in rel.lower():
                            self.all_fonts[rel] = os.path.join(root, f)
        
        self.all_cursor_sets = {}
        if os.path.exists(CURSORS_LIB_DIR):
            for root, dirs, files in os.walk(CURSORS_LIB_DIR):
                if any(f.lower().endswith('.png') for f in files):
                    if root == CURSORS_LIB_DIR: continue
                    rel = os.path.relpath(root, CURSORS_LIB_DIR).replace("\\", "/")
                    if not q or q in rel.lower():
                        self.all_cursor_sets[rel] = root
        
        try:
            self.f_cb['values'] = sorted(list(self.all_fonts.keys()))
            self.c_cb['values'] = sorted(list(self.all_cursor_sets.keys()))
        except: pass
        
        self.update_cursor_preview()

    def on_hotkey_change(self, e):
        self.cfg["hotkey"] = self.hotkey_var.get()
        self.cur_hotkey_val = self.hotkey_var.get()
        save_config(self.cfg)

    def hotkey_loop(self):
        u32 = ctypes.windll.user32
        was = False
        while True:
            hk = self.cur_hotkey_val
            if hk in KEYS_MAP:
                _, vk = KEYS_MAP[hk]
                if (u32.GetAsyncKeyState(vk) & 0x8000) != 0:
                    if not was:
                        self.trigger_show = True
                        was = True
                else: was = False
            time.sleep(0.02)

    def check_hotkey_trigger(self):
        if self.trigger_show:
            self.trigger_show = False
            self.show()
        self.after(100, self.check_hotkey_trigger)

    def show_update_prompt(self):
        """Displays custom dialog when an update is detected."""
        dialog = tk.Toplevel(self)
        dialog.title("Roblox Update Detected")
        dialog.geometry("350x180")
        dialog.attributes('-topmost', True)
        dialog.configure(bg=BG_COLOR)
        dialog.grab_set()
        
        tk.Label(dialog, text="Roblox has updated and reset your fonts.", font=("Segoe UI", 12), bg=BG_COLOR, fg=TEXT_PRIMARY).pack(pady=10)
        tk.Label(dialog, text="What would you like to do?", bg=BG_COLOR, fg=TEXT_SECONDARY).pack(pady=5)

        def ask_later():
            log("User chose: Ask Later")
            self.prompt_active = False
            self.known_versions = set(get_roblox_version_paths())
            dialog.destroy()

        def update_now():
            log("User chose: Update Now (and restart)")
            self.apply_silently()
            if self.prev_run: # if roblox is currently running
                restart_roblox()
            self.prompt_active = False
            self.known_versions = set(get_roblox_version_paths())
            dialog.destroy()

        def update_on_close():
            log("User chose: Update when I close Roblox")
            self.waiting_for_close = True
            self.prompt_active = False
            dialog.destroy()

        ttk.Button(dialog, text="Update Now (and restart)", style="Accent.TButton", command=update_now).pack(fill=tk.X, padx=20, pady=2)
        ttk.Button(dialog, text="Update when I close Roblox", command=update_on_close).pack(fill=tk.X, padx=20, pady=2)
        ttk.Button(dialog, text="Ask Later", command=ask_later).pack(fill=tk.X, padx=20, pady=2)

    def apply_silently(self):
        """Applies configuration without showing message boxes."""
        sf, sc = self.cfg.get("font"), self.cfg.get("cursor_set")
        if sf and sf in self.all_fonts: apply_font(self.all_fonts[sf])
        if sc and sc in self.all_cursor_sets: apply_cursor_set(self.all_cursor_sets[sc])

    def check_roblox_process(self):
        try:
            running = False
            for p in psutil.process_iter(['name']):
                if "roblox" in p.info['name'].lower() and not any(x in p.info['name'].lower() for x in ["crash", "manager"]):
                    running = True; break
            
            # --- Feature: Update on Close ---
            if self.waiting_for_close:
                if not running:
                    log("Roblox closed. Applying scheduled patch...")
                    self.apply_silently()
                    self.waiting_for_close = False
                    self.known_versions = set(get_roblox_version_paths())
            
            # --- Feature: Detect Update ---
            elif not self.prompt_active:
                current_versions = set(get_roblox_version_paths())
                new_versions = current_versions - self.known_versions
                if new_versions:
                    log(f"Roblox update detected. New version folders: {new_versions}")
                    self.prompt_active = True
                    self.after(0, self.show_update_prompt)

            # --- Existing: Show UI on initial Roblox start ---
            if running and self.cfg.get("show_on_start", True) and not getattr(self, "prev_run", False) and not self.prompt_active:
                self.show()
                
            self.prev_run = running
        except Exception as e: 
            pass # Keep silent in background loop
        self.after(2000, self.check_roblox_process)

    def apply(self):
        sf, sc = self.font_var.get(), self.cursor_var.get()
        self.cfg.update({"font": sf, "cursor_set": sc, "show_on_start": not self.show_var.get()})
        save_config(self.cfg)
        
        f_res = apply_font(self.all_fonts[sf]) if sf in self.all_fonts else True
        c_res = apply_cursor_set(self.all_cursor_sets[sc]) if sc in self.all_cursor_sets else True
        
        if f_res and c_res:
            messagebox.showinfo("Success", "Modifications Applied. Please restart Roblox.")
        else:
            messagebox.showwarning("Incomplete", "Some modifications could not be applied. Check Diagnostics.")

    def restore(self):
        if messagebox.askyesno("Confirm", "Revert all Roblox fonts and cursors to original?"):
            restore_defaults()
            messagebox.showinfo("Restored", "Original assets restored.")

    def hide(self): self.withdraw()
    def show(self):
        self.deiconify(); self.attributes("-topmost", True); self.lift(); self.focus_force()
        self.attributes("-topmost", False)

if __name__ == "__main__":
    app = ManagerUI()
    app.withdraw()
    app.mainloop()
'''

MANAGER_HUB_CODE = r'''
import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess

def run_uninstall(parent_window):
    install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    if not messagebox.askyesno("Confirm Uninstall", "Uninstall and remove all files?"): return
    try:
        hub_pid = os.getpid()
        bat = os.path.join(os.getenv('TEMP'), 'rfm_uninstaller.bat')
        with open(bat, 'w', encoding='utf-8') as f:
            f.write(f'@echo off\n')
            f.write(f'echo Uninstalling Roblox Font Manager...\n')
            f.write(f'taskkill /F /PID {hub_pid} >nul 2>&1\n')
            f.write('taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq Roblox Font & Cursor Manager" >nul 2>&1\n')
            f.write(f'del "{os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "launch_roblox_font_manager.vbs")}" 2>nul\n')
            f.write(f'del "{os.path.join(os.path.expanduser("~"), "Desktop", "Roblox Font Manager Hub.lnk")}" 2>nul\n')
            f.write('ping 127.0.0.1 -n 5 > nul\n')
            f.write(f'rd /s /q "{install_dir}"\n')
            f.write(f'del "%~f0"\n')
        subprocess.Popen(f'"{bat}"', shell=True, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
        parent_window.destroy()
    except: pass

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Roblox Font Manager Hub")
    root.geometry("400x200")
    ttk.Label(root, text="Manager Hub & Uninstaller", font=("Segoe UI", 14, "bold")).pack(pady=20)
    ttk.Button(root, text="Uninstall Application", command=lambda: run_uninstall(root)).pack(fill='x', pady=10, padx=50)
    ttk.Button(root, text="Close", command=root.destroy).pack(pady=10)
    root.mainloop()
'''

# --- SHARED UI HELPERS ---

def style_ttk(root):
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure("Custom.Horizontal.TProgressbar", thickness=8, troughcolor=SECONDARY_BG, background=ACCENT_COLOR, borderwidth=0)
    style.configure("Accent.TButton", padding=10, background=ACCENT_COLOR, foreground="white", font=("Segoe UI", 10, "bold"))
    style.map("Accent.TButton", background=[('active', '#005a9e')])

# --- STEP 2: LIBRARY SETUP ---

class FontChooserApp:
    def __init__(self, parent, install_dir):
        self.win = tk.Toplevel(parent)
        self.win.title("Step 2: Setup Your Library")
        self.win.geometry("850x650")
        self.win.configure(bg=BG_COLOR)
        
        self.install_dir = install_dir
        self.fonts_dir = os.path.join(install_dir, "Fonts")
        self.cursors_dir = os.path.join(install_dir, "Cursors")
        self.font_vars = {} 
        self.cursor_vars = {} 
        self.loaded_fonts = [] 
        self.font_meta_cache = {}
        self.current_tab = "Fonts"
        self.image_cache = [] # Prevents Tkinter garbage collection of preview images
        
        # Explicitly assign self.win master to eliminate cross-window Tkinter tracking bugs
        self.font_search_var = tk.StringVar(self.win)
        self.cursor_search_var = tk.StringVar(self.win)

        self._init_checkbox_states()
        self._setup_ui()
        self.win.protocol("WM_DELETE_WINDOW", self.finish_setup)

    def _init_checkbox_states(self):
        # Pre-populate dictionaries so unchecked status isn't forgotten during search
        if os.path.exists(self.fonts_dir):
            for root, dirs, files in os.walk(self.fonts_dir):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf')):
                        rel = os.path.relpath(os.path.join(root, f), self.fonts_dir).replace("\\", "/")
                        self.font_vars[rel] = tk.BooleanVar(self.win, value=False)
                        
        if os.path.exists(self.cursors_dir):
            for d in os.listdir(self.cursors_dir):
                is_m = (d == "Normal")
                self.cursor_vars[d] = tk.BooleanVar(self.win, value=is_m)

    def _setup_ui(self):
        sidebar = tk.Frame(self.win, bg=SECONDARY_BG, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="FONTS+", fg=ACCENT_COLOR, bg=SECONDARY_BG, font=("Segoe UI", 20, "bold")).pack(pady=30)

        self.main_area = tk.Frame(self.win, bg=BG_COLOR)
        self.main_area.pack(side="right", fill="both", expand=True)

        for name in ["Import Fonts", "Import Cursors"]:
            btn = tk.Button(sidebar, text=name, bg=SECONDARY_BG, fg=TEXT_SECONDARY, bd=0, 
                            font=("Segoe UI", 11), activebackground=BG_COLOR, activeforeground=TEXT_PRIMARY,
                            padx=20, anchor="w", command=lambda n=name: self.switch_tab(n))
            btn.pack(fill="x", pady=5)

        self.switch_tab("Import Fonts")

    def switch_tab(self, name):
        self.current_tab = name
        for widget in self.main_area.winfo_children(): widget.destroy()
        tk.Label(self.main_area, text=name, font=("Segoe UI", 24, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack(anchor="w", padx=40, pady=(40, 10))
        
        search_container = tk.Frame(self.main_area, bg=BG_COLOR)
        search_container.pack(fill="x", padx=40, pady=(0, 10))
        tk.Label(search_container, text="Search:", bg=BG_COLOR, fg=TEXT_SECONDARY).pack(side="left")
        
        is_font = "Fonts" in name
        cur_search_var = self.font_search_var if is_font else self.cursor_search_var
        
        search_ent = tk.Entry(search_container, textvariable=cur_search_var, bg=SECONDARY_BG, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY, bd=0)
        search_ent.pack(side="left", fill="x", expand=True, padx=10, ipady=3)
        # Event triggers on the general instance so it avoids closure tracking errors
        search_ent.bind("<KeyRelease>", lambda e: self.refresh_view())

        container = tk.Frame(self.main_area, bg=BG_COLOR)
        container.pack(fill="both", expand=True, padx=40, pady=10)
        
        canvas = tk.Canvas(container, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        
        self.scroll_frame = tk.Frame(canvas, bg=BG_COLOR)
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.refresh_view()

        footer = tk.Frame(self.main_area, bg=BG_COLOR)
        footer.pack(fill="x", side="bottom", padx=40, pady=30)
        if is_font: 
            ttk.Button(footer, text="+ Add Custom Font", style="Accent.TButton", command=self.add_custom_font).pack(side="left")
        else: 
            ttk.Button(footer, text="+ Import Cursor Set", style="Accent.TButton", command=self.add_custom_cursor_set).pack(side="left")
        ttk.Button(footer, text="Finish Setup", command=self.finish_setup).pack(side="right")

    def refresh_view(self):
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        self.image_cache.clear()
        
        if "Fonts" in self.current_tab:
            q = self.font_search_var.get().lower()
            self._render_fonts(self.scroll_frame, q)
        else:
            q = self.cursor_search_var.get().lower()
            self._render_cursors(self.scroll_frame, q)
            
        # Optional: Reset scrollbar to top whenever search input updates list
        self.scroll_frame.update_idletasks()
        try:
            self.scroll_frame.master.yview_moveto(0)
        except: pass

    def _render_fonts(self, frame, search_query=""):
        if not os.path.exists(self.fonts_dir): return
        font_data = []
        for root, dirs, files in os.walk(self.fonts_dir):
            for f in files:
                if f.lower().endswith(('.ttf', '.otf')):
                    rel = os.path.relpath(os.path.join(root, f), self.fonts_dir).replace("\\", "/")
                    if not search_query or search_query in rel.lower():
                        font_data.append((rel, os.path.join(root, f)))
        
        for rel, path in sorted(font_data):
            card = tk.Frame(frame, bg=SECONDARY_BG, padx=15, pady=10)
            card.pack(fill="x", pady=5)
            if rel not in self.font_vars: self.font_vars[rel] = tk.BooleanVar(self.win, value=False)
            tk.Checkbutton(card, text=rel, variable=self.font_vars[rel], bg=SECONDARY_BG, fg=TEXT_PRIMARY, selectcolor=BG_COLOR, font=("Segoe UI", 10)).pack(side="left")
            
            if path not in self.font_meta_cache:
                self.load_font_memory(path)
                self.font_meta_cache[path] = self.get_font_family_from_file(path) or "Segoe UI"
            
            fam = self.font_meta_cache[path]
            tk.Label(card, text="AaBb 123", font=(fam, 14), bg=SECONDARY_BG, fg=TEXT_PRIMARY).pack(side="right", padx=10)

    def _render_cursors(self, frame, search_query=""):
        if not os.path.exists(self.cursors_dir): return
        sets = [d for d in os.listdir(self.cursors_dir) if os.path.isdir(os.path.join(self.cursors_dir, d))]
        for d in sorted(sets):
            if search_query and search_query not in d.lower(): continue
            card = tk.Frame(frame, bg=SECONDARY_BG, padx=15, pady=10)
            card.pack(fill="x", pady=5)
            is_m = (d == "Normal")
            if d not in self.cursor_vars: self.cursor_vars[d] = tk.BooleanVar(self.win, value=is_m)
            tk.Checkbutton(card, text=f"Set: {d}", variable=self.cursor_vars[d], bg=SECONDARY_BG, fg=TEXT_PRIMARY, selectcolor=BG_COLOR, state='disabled' if is_m else 'normal').pack(side="left")

            # Cursor Previews
            preview_frame = tk.Frame(card, bg=SECONDARY_BG)
            preview_frame.pack(side="right", padx=10)
            
            set_path = os.path.join(self.cursors_dir, d)
            c_files = ["ArrowCursor.png", "ArrowFarCursor.png", "IBeamCursor.png", "MouseLockedCursor.png", "MouseLockedCursor@2x.png"]
            
            for cf in c_files:
                img_path = os.path.join(set_path, cf)
                if os.path.exists(img_path):
                    try:
                        img = tk.PhotoImage(master=self.win, file=img_path)
                        img = img.zoom(2, 2)  # Zooms the icon to make it quite big
                        self.image_cache.append(img)
                        tk.Label(preview_frame, image=img, bg=SECONDARY_BG).pack(side="left", padx=5)
                    except Exception:
                        pass

    def get_font_family_from_file(self, filepath):
        try:
            with open(filepath, 'rb') as f: d = f.read()
            if d[:4] not in [b'\x00\x01\x00\x00', b'OTTO', b'true']: return None
            u2 = lambda i: struct.unpack('>H', d[i:i+2])[0]
            u4 = lambda i: struct.unpack('>L', d[i:i+4])[0]
            off = 0
            for i in range(u2(4)):
                if d[12+i*16:16+i*16] == b'name': off = u4(20+i*16); break
            if off == 0: return None
            count = u2(off+2); s_off = u2(off+4) + off
            for i in range(count):
                rec = off + 6 + i*12
                if u2(rec+6) == 1:
                    nm = d[s_off+u2(rec+10):s_off+u2(rec+10)+u2(rec+8)]
                    try: return nm.decode('utf-16-be') if u2(rec)==3 else nm.decode('mac_roman')
                    except: pass
        except: pass
        return None

    def load_font_memory(self, path):
        try:
            if ctypes.windll.gdi32.AddFontResourceExW(path, 0x10, 0) > 0:
                self.loaded_fonts.append(path); return True
        except: pass
        return False

    def add_custom_font(self):
        p = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if p:
            fn = os.path.basename(p); shutil.copy2(p, os.path.join(self.fonts_dir, fn))
            self.font_vars[fn] = tk.BooleanVar(self.win, value=False); self.switch_tab("Import Fonts")

    def add_custom_cursor_set(self):
        d = filedialog.askdirectory(title="Select Cursor Set Folder")
        if d:
            n = os.path.basename(d); shutil.copytree(d, os.path.join(self.cursors_dir, n), dirs_exist_ok=True)
            self.cursor_vars[n] = tk.BooleanVar(self.win, value=False); self.switch_tab("Import Cursors")

    def finish_setup(self):
        rem = 0
        for rel, v in self.font_vars.items():
            if not v.get():
                p = os.path.join(self.fonts_dir, rel)
                if os.path.exists(p): os.remove(p); rem += 1
        for rel, v in self.cursor_vars.items():
            if not v.get():
                p = os.path.join(self.cursors_dir, rel)
                if os.path.exists(p): shutil.rmtree(p); rem += 1
        self.win.destroy()

# --- STEP 1: THE INSTALLER ---

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Font Manager Installer")
        self.root.geometry("500x420")
        self.root.configure(bg=BG_COLOR)
        self.install_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'RobloxFontManager')
        style_ttk(self.root)
        self.image_cache = [] # Prevents Tkinter garbage collection of preview images
        self._setup_ui()

    def _setup_ui(self):
        c = tk.Frame(self.root, bg=BG_COLOR, padx=40, pady=40)
        c.pack(fill="both", expand=True)
        tk.Label(c, text="Roblox Font Manager", font=("Segoe UI", 24, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack(pady=(0, 10))
        tk.Label(c, text="Step 1: System Installation", font=("Segoe UI", 11), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()
        
        self.status_lbl = tk.Label(c, text="System Ready", font=("Segoe UI", 10), bg=BG_COLOR, fg=ACCENT_COLOR)
        self.status_lbl.pack(pady=(40, 5))
        self.pb = ttk.Progressbar(c, length=400, mode='determinate', style="Custom.Horizontal.TProgressbar")
        self.pb.pack(pady=10)
        self.install_btn = ttk.Button(c, text="Install Now", style="Accent.TButton", command=self.run_install)
        self.install_btn.pack(pady=30, ipady=5, fill="x")

    def run_install(self):
        self.install_btn.config(state='disabled')
        threading.Thread(target=self._install_thread).start()

    def _get_python_path(self):
        try:
            return sys.executable
        except:
            return "pythonw.exe"

    def _install_thread(self):
        try:
            # Shutdown previous instances
            subprocess.call('taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq Roblox Font & Cursor Manager" >nul 2>&1', shell=True)
            
            self._update(15, "Initializing environment...")
            py = self._get_python_path()
            pyw = py.replace('python.exe', 'pythonw.exe')
            
            os.makedirs(self.install_dir, exist_ok=True)
            os.makedirs(os.path.join(self.install_dir, "Fonts"), exist_ok=True)
            os.makedirs(os.path.join(self.install_dir, "Cursors"), exist_ok=True)
            
            self._update(40, "Extracting libraries (Fonts.zip)...")
            bd = os.path.dirname(os.path.abspath(__file__))
            
            # Nested Zip Extraction Logic
            zp_fonts = os.path.join(bd, "Fonts.zip")
            if os.path.exists(zp_fonts):
                fonts_dest = os.path.join(self.install_dir, "Fonts")
                with zipfile.ZipFile(zp_fonts, 'r') as z:
                    for member in z.infolist():
                        if not member.is_dir() and member.filename.lower().endswith(('.ttf', '.otf')):
                            with z.open(member) as source:
                                with open(os.path.join(fonts_dest, os.path.basename(member.filename)), "wb") as dest:
                                    shutil.copyfileobj(source, dest)
                        elif not member.is_dir() and member.filename.lower().endswith('.zip'):
                            temp_zip = os.path.join(self.install_dir, f"tmp_{os.path.basename(member.filename)}")
                            with z.open(member) as source, open(temp_zip, "wb") as f: shutil.copyfileobj(source, f)
                            try:
                                with zipfile.ZipFile(temp_zip, 'r') as nested_z:
                                    for nm in nested_z.infolist():
                                        if not nm.is_dir() and nm.filename.lower().endswith(('.ttf', '.otf')):
                                            with nested_z.open(nm) as ns, open(os.path.join(fonts_dest, os.path.basename(nm.filename)), "wb") as nd:
                                                shutil.copyfileobj(ns, nd)
                            except: pass
                            finally: 
                                if os.path.exists(temp_zip): os.remove(temp_zip)

            self._update(60, "Extracting cursors...")
            zc = os.path.join(bd, "Cursors.zip")
            if os.path.exists(zc):
                with zipfile.ZipFile(zc, 'r') as z: z.extractall(os.path.join(self.install_dir, "Cursors"))
            
            self._update(75, "Installing dependencies (psutil)...")
            subprocess.check_call([py, "-m", "pip", "install", "psutil"], creationflags=subprocess.CREATE_NO_WINDOW)
            
            self._update(90, "Deploying system files...")
            with open(os.path.join(self.install_dir, 'auto_font_manager.py'), 'w', encoding='utf-8') as f: f.write(AUTO_MANAGER_CODE)
            with open(os.path.join(self.install_dir, 'manager.py'), 'w', encoding='utf-8') as f: f.write(MANAGER_HUB_CODE)
            
            self.create_shortcut(pyw, os.path.join(self.install_dir, 'manager.py'))
            vbs = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup', 'launch_roblox_font_manager.vbs')
            with open(vbs, 'w') as f:
                f.write(f'Set oWS = CreateObject("WScript.Shell")\noWS.Run """{pyw}"" ""{os.path.join(self.install_dir, "auto_font_manager.py")}""", 0, false')
            
            self._update(100, "Stage 1 Finished!")
            self.root.after(0, self.start_step_2, vbs)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.install_btn.config(state='normal'))

    def _update(self, val, msg):
        self.root.after(0, lambda: self.pb.configure(value=val))
        self.root.after(0, lambda: self.status_lbl.configure(text=msg))

    def start_step_2(self, vbs):
        self.root.withdraw(); nr = tk.Tk(); nr.withdraw(); style_ttk(nr); FontChooserApp(nr, self.install_dir); nr.mainloop()
        if os.path.exists(vbs): subprocess.Popen(f'cscript //Nologo "{vbs}"', shell=True, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
        self.root.destroy()

    def create_shortcut(self, pyw, script):
        target = os.path.join(os.path.expanduser("~"), "Desktop", "Roblox Font Manager Hub.lnk")
        vbs = os.path.join(os.getenv('TEMP'), 'create_lnk.vbs')
        with open(vbs, 'w') as f:
            f.write(f'Set oWS = WScript.CreateObject("WScript.Shell")\nsLinkFile = "{target}"\nSet oLink = oWS.CreateShortcut(sLinkFile)\noLink.TargetPath = "{pyw}"\noLink.Arguments = """{script}"""\noLink.WorkingDirectory = "{self.install_dir}"\noLink.Save')
        subprocess.call(['cscript', vbs], creationflags=subprocess.CREATE_NO_WINDOW)

if __name__ == "__main__":
    root = tk.Tk(); app = InstallerApp(root); root.mainloop()