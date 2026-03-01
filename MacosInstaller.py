import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import threading
import zipfile
import time
import struct
import logging
import traceback
import webbrowser
from datetime import datetime

# --- THEME CONSTANTS (Bloxstrap Inspired) ---
BG_COLOR = "#111111"
SECONDARY_BG = "#1a1a1a"
ACCENT_COLOR = "#0078d7"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#aaaaaa"
SUCCESS_COLOR = "#28a745"
ERROR_COLOR = "#dc3545"

# --- GLOBAL ERROR HANDLER & LOGGER FOR INSTALLER ---
INSTALL_LOG_FILE = os.path.expanduser('~/Library/Application Support/RobloxFontManager/manager.log')

def install_log(msg):
    os.makedirs(os.path.dirname(INSTALL_LOG_FILE), exist_ok=True)
    with open(INSTALL_LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] [INSTALLER] {msg}\n")
    print(f"[INSTALLER LOG]: {msg}")

def installer_handle_error(error_msg, tb_info=""):
    install_log(f"CRITICAL ERROR: {error_msg}\n{tb_info}")
    safe_msg = str(error_msg).replace('"', "'").replace("\n", " ")
    try:
        ascript = f'''
        set dialogResult to display dialog "We Encountered An error, Please report this on the issue Page\\n\\nDetails: {safe_msg}" with title "Hey!" buttons {{"Issues page", "Copy Logs", "Ignore"}} default button "Ignore" with icon stop
        return button returned of dialogResult
        '''
        result = subprocess.run(['osascript', '-e', ascript], capture_output=True, text=True)
        choice = result.stdout.strip()
        
        if choice == "Issues page":
            install_log("User clicked 'Issues page'")
            webbrowser.open("https://github.com/AvrageUserInYoMama/RobloxFontChanger/issues")
        elif choice == "Copy Logs":
            install_log("User clicked 'Copy Logs'")
            log_data = "No logs found."
            if os.path.exists(INSTALL_LOG_FILE):
                with open(INSTALL_LOG_FILE, 'r') as f:
                    log_data = f.read()
            p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            p.communicate(input=log_data.encode('utf-8'))
            install_log("Logs successfully copied to macOS clipboard.")
    except Exception as fallback_e:
        install_log(f"Error handler itself failed: {fallback_e}")

# --- EMBEDDED SCRIPTS (EXPANDED & ROBUST) ---
AUTO_MANAGER_CODE = r'''
import os
import sys
import json
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont, filedialog
from datetime import datetime
import time
import hashlib
import traceback
import webbrowser

# --- Dependency Check ---
try:
    import psutil
    from pynput import keyboard
except ImportError as ie:
    sys.exit(1)

# ---------------- CONFIG & THEME ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
APP_NAME = "Roblox Font & Cursor Manager (macOS)"
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
FONTS_LIB_DIR = os.path.join(BASE_DIR, "Fonts")
CURSORS_LIB_DIR = os.path.join(BASE_DIR, "Cursors")
LOG_FILE = os.path.join(BASE_DIR, "manager.log")

BG_COLOR = "#111111"
SECONDARY_BG = "#1a1a1a"
ACCENT_COLOR = "#0078d7"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#aaaaaa"

ROBLOX_APP_BUNDLE = "/Applications/Roblox.app"
ROBLOX_PLIST = os.path.join(ROBLOX_APP_BUNDLE, "Contents", "Info.plist")

KEYS_MAP = {
    "F9": "<f9>",
    "F10": "<f10>",
    "F11": "<f11>",
    "Ctrl + Grave (`)": "<ctrl>+`"
}

def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now()}] [DAEMON] {msg}\n")
        print(f"[DAEMON LOG]: {msg}")
    except:
        pass

def handle_global_error(error_msg, tb_info=""):
    """macOS Native AppleScript Error Dialog"""
    log(f"CRITICAL ERROR ENCOUNTERED: {error_msg}\n{tb_info}")
    safe_msg = str(error_msg).replace('"', "'").replace("\n", " ")
    try:
        ascript = f"""
        set dialogResult to display dialog "We Encountered An error, Please report this on the issue Page\\n\\nDetails: {safe_msg}" with title "Hey!" buttons {{"Issues page", "Copy Logs", "Ignore"}} default button "Ignore" with icon stop
        return button returned of dialogResult
        """
        result = subprocess.run(['osascript', '-e', ascript], capture_output=True, text=True)
        choice = result.stdout.strip()
        
        if choice == "Issues page":
            log("User clicked 'Issues page'")
            webbrowser.open("https://github.com/AvrageUserInYoMama/RobloxFontChanger/issues")
        elif choice == "Copy Logs":
            log("User clicked 'Copy Logs'")
            log_data = "No logs found."
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r') as f:
                    log_data = f.read()
            p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            p.communicate(input=log_data.encode('utf-8'))
            log("Logs successfully copied to macOS clipboard.")
    except Exception as fallback_e:
        log(f"Error handler itself failed: {fallback_e}")

def get_file_hash(filepath):
    log(f"Hashing file: {filepath}")
    try:
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        h = hasher.hexdigest()
        log(f"Hash for {filepath} is {h}")
        return h
    except Exception as e:
        log(f"Hashing failed for {filepath}: {e}")
        return None

def check_permissions(directory):
    log(f"Checking write permissions for directory: {directory}")
    try:
        if not os.access(directory, os.W_OK):
            log(f"Missing write permissions for {directory}. Check SIP or Full Disk Access.")
            return False
        log(f"Permissions OK for {directory}")
        return True
    except Exception as e:
        handle_global_error(f"Permission check crashed: {e}", traceback.format_exc())
        return False

def load_config():
    log("Executing load_config()")
    defaults = {"font": None, "cursor_set": None, "show_on_start": True, "hotkey": "F9"}
    try:
        if not os.path.exists(CONFIG_FILE):
            log("Config file does not exist, using defaults.")
            return defaults
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            log(f"Loaded config data: {data}")
            for k, v in defaults.items():
                if k not in data: 
                    data[k] = v
                    log(f"Added missing default key: {k} = {v}")
            return data
    except Exception as e:
        handle_global_error(f"load_config failed: {e}", traceback.format_exc())
        return defaults

def save_config(cfg):
    log(f"Executing save_config() with data: {cfg}")
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        log("Config saved successfully.")
    except Exception as e:
        handle_global_error(f"save_config failed: {e}", traceback.format_exc())

# ---------------- ROBLOX UTILS ---------------- #

def get_roblox_version_paths():
    log("Executing get_roblox_version_paths()")
    try:
        if os.path.exists(ROBLOX_APP_BUNDLE):
            p = os.path.join(ROBLOX_APP_BUNDLE, "Contents", "Resources")
            log(f"Found Roblox path: {p}")
            return [p]
        log("Roblox App Bundle not found.")
        return []
    except Exception as e:
        handle_global_error(f"get_roblox_version_paths failed: {e}", traceback.format_exc())
        return []

def get_roblox_mtime():
    log("Executing get_roblox_mtime()")
    try:
        if os.path.exists(ROBLOX_PLIST):
            mtime = os.path.getmtime(ROBLOX_PLIST)
            log(f"Roblox plist mtime: {mtime}")
            return mtime
        log("Roblox plist not found, mtime 0.")
        return 0
    except Exception as e:
        handle_global_error(f"get_roblox_mtime failed: {e}", traceback.format_exc())
        return 0

def restart_roblox():
    log("Executing restart_roblox()")
    try:
        subprocess.run(['killall', 'Roblox'], stderr=subprocess.PIPE)
        log("killall Roblox executed. Sleeping 2s.")
        time.sleep(2)
        subprocess.run(['open', '-a', 'Roblox'], stderr=subprocess.PIPE)
        log("open -a Roblox executed.")
    except Exception as e:
        handle_global_error(f"restart_roblox failed: {e}", traceback.format_exc())

def apply_font(font_path):
    log(f"Executing apply_font() for: {font_path}")
    try:
        versions = get_roblox_version_paths()
        if not versions:
            log("No Roblox installation found to apply fonts to.")
            return False

        success = False
        for v_path in versions:
            font_dir = os.path.join(v_path, "content", "fonts")
            log(f"Target font directory: {font_dir}")
            if os.path.exists(font_dir):
                if not check_permissions(font_dir):
                    log("Permission Denied: Cannot write to Roblox fonts folder.")
                    continue
                    
                backup_dir = os.path.join(font_dir, "Fonts.old")
                os.makedirs(backup_dir, exist_ok=True)
                log(f"Backup directory verified: {backup_dir}")
                
                for f in os.listdir(font_dir):
                    if f.lower().endswith((".ttf", ".otf")) and not f.lower().startswith("twemoji"):
                        src = os.path.join(font_dir, f)
                        back = os.path.join(backup_dir, f)
                        try:
                            if not os.path.exists(back): 
                                log(f"Backing up original font: {f}")
                                shutil.move(src, back)
                            
                            temp_path = src + ".tmp"
                            log(f"Copying to temp path: {temp_path}")
                            shutil.copy2(font_path, temp_path)
                            log(f"Atomic replacing temp path to: {src}")
                            os.replace(temp_path, src)
                            success = True
                        except PermissionError as pe:
                            log(f"Permission error applying font {f}: {pe}")
                        except Exception as e:
                            log(f"Failed to apply font to {f}: {e}")
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
        log(f"apply_font finished. Success: {success}")
        return success
    except Exception as e:
        handle_global_error(f"apply_font failed catastrophically: {e}", traceback.format_exc())
        return False

def apply_cursor_set(set_path):
    log(f"Executing apply_cursor_set() for: {set_path}")
    try:
        versions = get_roblox_version_paths()
        c_files = ["ArrowCursor.png", "ArrowFarCursor.png", "IBeamCursor.png", "MouseLockedCursor.png", "MouseLockedCursor@2x.png"]
        
        success = False
        for v_path in versions:
            cursor_dir = os.path.join(v_path, "content", "textures", "Cursors", "KeyboardMouse")
            texture_dir = os.path.join(v_path, "content", "textures")
            log(f"Target cursor directory: {cursor_dir}")
            
            if os.path.exists(cursor_dir):
                if not check_permissions(cursor_dir):
                    log("Permission Denied: Cannot write to Roblox cursor folder.")
                    continue
                    
                backup_dir = os.path.join(cursor_dir, "Cursors.old")
                os.makedirs(backup_dir, exist_ok=True)
                log(f"Backup directory verified: {backup_dir}")
                
                for cf in c_files:
                    lib_file = os.path.join(set_path, cf)
                    if "MouseLocked" in cf:
                        target = os.path.join(texture_dir, cf)
                    else:
                        target = os.path.join(cursor_dir, cf)
                        
                    log(f"Processing cursor file: {cf}, Target: {target}")
                    if os.path.exists(lib_file):
                        try:
                            if os.path.exists(target) and not os.path.exists(os.path.join(backup_dir, cf)):
                                log(f"Backing up cursor: {cf}")
                                shutil.move(target, os.path.join(backup_dir, cf))
                            
                            temp_path = target + ".tmp"
                            log(f"Copying to temp path: {temp_path}")
                            shutil.copy2(lib_file, temp_path)
                            log(f"Atomic replacing temp path to: {target}")
                            os.replace(temp_path, target)
                            success = True
                        except PermissionError as pe:
                            log(f"Permission error applying cursor {cf}: {pe}")
                        except Exception as e:
                            log(f"Failed to apply cursor {cf}: {e}")
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
        log(f"apply_cursor_set finished. Success: {success}")
        return success
    except Exception as e:
        handle_global_error(f"apply_cursor_set failed catastrophically: {e}", traceback.format_exc())
        return False

def restore_defaults():
    log("Executing restore_defaults()")
    try:
        versions = get_roblox_version_paths()
        for v_path in versions:
            f_old = os.path.join(v_path, "content", "fonts", "Fonts.old")
            log(f"Checking for font backup: {f_old}")
            if os.path.exists(f_old):
                f_dest = os.path.join(v_path, "content", "fonts")
                if check_permissions(f_dest):
                    log("Restoring fonts from backup...")
                    for f in os.listdir(f_old):
                        try: shutil.move(os.path.join(f_old, f), os.path.join(f_dest, f))
                        except Exception as move_e: log(f"Failed to restore {f}: {move_e}")
                    shutil.rmtree(f_old)
                    log("Fonts restored.")
                
            c_old = os.path.join(v_path, "content", "textures", "Cursors", "KeyboardMouse", "Cursors.old")
            log(f"Checking for cursor backup: {c_old}")
            if os.path.exists(c_old):
                c_dest_km = os.path.join(v_path, "content", "textures", "Cursors", "KeyboardMouse")
                t_dest = os.path.join(v_path, "content", "textures")
                if check_permissions(c_dest_km) and check_permissions(t_dest):
                    log("Restoring cursors from backup...")
                    for f in os.listdir(c_old):
                        dest = t_dest if "MouseLocked" in f else c_dest_km
                        try: shutil.move(os.path.join(c_old, f), os.path.join(dest, f))
                        except Exception as move_e: log(f"Failed to restore {f}: {move_e}")
                    shutil.rmtree(c_old)
                    log("Cursors restored.")
    except Exception as e:
        handle_global_error(f"restore_defaults failed: {e}", traceback.format_exc())

# ---------------- MAIN UI ---------------- #

class ManagerUI(tk.Tk):
    def __init__(self):
        log("Initializing ManagerUI...")
        try:
            super().__init__()
            self.title(APP_NAME)
            self.geometry("1000x700")
            self.configure(bg=BG_COLOR)
            self.resizable(True, True)

            self.cfg = load_config()
            self.trigger_show = False
            self.all_fonts = {}
            self.all_cursor_sets = {}
            self.image_cache = []
            
            self.known_mtime = get_roblox_mtime()
            log(f"Initial known Roblox mtime: {self.known_mtime}")
            self.prompt_active = False
            self.waiting_for_close = False
            self.prev_run = False
            
            self.font_var = tk.StringVar(self, value=self.cfg.get("font"))
            self.cursor_var = tk.StringVar(self, value=self.cfg.get("cursor_set"))
            self.hotkey_var = tk.StringVar(self, value=self.cfg.get("hotkey", "F9"))
            self.show_var = tk.BooleanVar(self, value=not self.cfg.get("show_on_start", True))
            self.search_var = tk.StringVar(self)
            self.cur_hotkey_val = self.cfg.get("hotkey", "F9")

            log("Building UI Widgets...")
            self.style_ui()
            self.create_widgets()
            self.refresh_libraries()
            self.protocol("WM_DELETE_WINDOW", self.hide)
            
            log("Starting hotkey background thread...")
            threading.Thread(target=self.hotkey_loop, daemon=True).start()
            self.check_hotkey_trigger()
            self.check_roblox_process()
            log("ManagerUI Initialization Complete.")
        except Exception as e:
            handle_global_error(f"ManagerUI init failed: {e}", traceback.format_exc())

    def style_ui(self):
        log("Styling UI...")
        try:
            s = ttk.Style(self)
            s.theme_use('clam')
            s.configure("Accent.TButton", padding=10, background=ACCENT_COLOR, foreground="white", font=("Segoe UI", 10, "bold"))
            s.map("Accent.TButton", background=[('active', '#005a9e')])
        except Exception as e:
            handle_global_error(f"UI Styling failed: {e}", traceback.format_exc())

    def create_widgets(self):
        log("Creating Widgets...")
        try:
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
        except Exception as e:
            handle_global_error(f"Widget creation failed: {e}", traceback.format_exc())

    def show_page(self, name):
        log(f"Switching UI Page to: {name}")
        try:
            for w in self.container.winfo_children(): w.destroy()
            tk.Label(self.container, text=name, font=("Segoe UI", 26, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack(anchor="w", padx=40, pady=(40, 20))
            
            page = tk.Frame(self.container, bg=BG_COLOR)
            page.pack(fill="both", expand=True, padx=40)

            if name == "Dashboard":
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
                
                self.cursor_preview_frame = tk.Frame(page, bg=SECONDARY_BG, padx=10, pady=10)
                self.cursor_preview_frame.pack(fill="x", pady=(0, 20))

                self.st_lbl = tk.Label(page, text="Ready", bg=BG_COLOR, fg=TEXT_SECONDARY, font=("Segoe UI", 10, "italic"))
                self.st_lbl.pack(pady=10)

                btns = tk.Frame(page, bg=BG_COLOR)
                btns.pack(side="bottom", fill="x", pady=20)
                ttk.Button(btns, text="Apply Changes", style="Accent.TButton", command=self.apply).pack(side="right", padx=5)
                ttk.Button(btns, text="Restart Roblox", command=restart_roblox).pack(side="right")
                ttk.Button(btns, text="Restore Default", command=self.restore).pack(side="left")
                
                self.update_cursor_preview()
                self.refresh_libraries()

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
        except Exception as e:
            handle_global_error(f"show_page({name}) failed: {e}", traceback.format_exc())

    def update_cursor_preview(self, event=None):
        log(f"Executing update_cursor_preview, set: {self.cursor_var.get()}")
        try:
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
                            img = img.zoom(2, 2)
                            self.image_cache.append(img)
                            tk.Label(self.cursor_preview_frame, image=img, bg=SECONDARY_BG).pack(side="left", padx=15)
                        except Exception as img_e:
                            log(f"Preview load failed for {cf}: {img_e}")
            else:
                tk.Label(self.cursor_preview_frame, text="No preview available.", bg=SECONDARY_BG, fg=TEXT_SECONDARY, font=("Segoe UI", 9, "italic")).pack(side="left")
        except Exception as e:
            handle_global_error(f"update_cursor_preview failed: {e}", traceback.format_exc())

    def refresh_libraries(self):
        log("Executing refresh_libraries()")
        try:
            q = self.search_var.get().lower()
            self.all_fonts = {}
            
            if os.path.exists(FONTS_LIB_DIR):
                log(f"Scanning Fonts Directory: {FONTS_LIB_DIR}")
                for root, dirs, files in os.walk(FONTS_LIB_DIR):
                    for f in files:
                        if f.lower().endswith(('.ttf', '.otf')):
                            rel = os.path.relpath(os.path.join(root, f), FONTS_LIB_DIR).replace("\\", "/")
                            if not q or q in rel.lower():
                                self.all_fonts[rel] = os.path.join(root, f)
            
            self.all_cursor_sets = {}
            if os.path.exists(CURSORS_LIB_DIR):
                log(f"Scanning Cursors Directory: {CURSORS_LIB_DIR}")
                for root, dirs, files in os.walk(CURSORS_LIB_DIR):
                    if any(f.lower().endswith('.png') for f in files):
                        if root == CURSORS_LIB_DIR: continue
                        rel = os.path.relpath(root, CURSORS_LIB_DIR).replace("\\", "/")
                        if not q or q in rel.lower():
                            self.all_cursor_sets[rel] = root
            
            log(f"Found {len(self.all_fonts)} fonts and {len(self.all_cursor_sets)} cursor sets.")
            try:
                self.f_cb['values'] = sorted(list(self.all_fonts.keys()))
                self.c_cb['values'] = sorted(list(self.all_cursor_sets.keys()))
            except: pass
            
            self.update_cursor_preview()
        except Exception as e:
            handle_global_error(f"refresh_libraries failed: {e}", traceback.format_exc())

    def on_hotkey_change(self, e):
        log(f"Hotkey changed to: {self.hotkey_var.get()}")
        try:
            self.cfg["hotkey"] = self.hotkey_var.get()
            self.cur_hotkey_val = self.hotkey_var.get()
            save_config(self.cfg)
        except Exception as ex:
            handle_global_error(f"on_hotkey_change failed: {ex}", traceback.format_exc())

    def on_activate(self):
        log("Hotkey Activation Triggered!")
        self.trigger_show = True

    def hotkey_loop(self):
        log("Executing macOS hotkey_loop using pynput...")
        try:
            with keyboard.GlobalHotKeys({
                KEYS_MAP.get(self.cur_hotkey_val, '<f9>'): self.on_activate
            }) as h:
                h.join()
        except Exception as e:
            log(f"Hotkey Error: macOS Accessibility Permissions missing or thread crash. {e}")
            handle_global_error(f"Hotkey loop failed. Needs Accessibility Permissions. {e}", traceback.format_exc())
            while True: time.sleep(10)

    def check_hotkey_trigger(self):
        try:
            if self.trigger_show:
                log("Processing hotkey show trigger...")
                self.trigger_show = False
                self.show()
            self.after(100, self.check_hotkey_trigger)
        except Exception as e:
            handle_global_error(f"check_hotkey_trigger failed: {e}", traceback.format_exc())

    def show_update_prompt(self):
        log("Executing show_update_prompt() UI dialog...")
        try:
            dialog = tk.Toplevel(self)
            dialog.title("Roblox Update Detected")
            dialog.geometry("350x180")
            dialog.attributes('-topmost', True)
            dialog.configure(bg=BG_COLOR)
            dialog.grab_set()
            
            tk.Label(dialog, text="Roblox has updated and reset your fonts.", font=("Segoe UI", 12), bg=BG_COLOR, fg=TEXT_PRIMARY).pack(pady=10)
            tk.Label(dialog, text="What would you like to do?", bg=BG_COLOR, fg=TEXT_SECONDARY).pack(pady=5)

            def ask_later():
                log("Update Prompt: User chose 'Ask Later'")
                self.prompt_active = False
                self.known_mtime = get_roblox_mtime()
                dialog.destroy()

            def update_now():
                log("Update Prompt: User chose 'Update Now (and restart)'")
                self.apply_silently()
                if self.prev_run: 
                    log("Roblox is running, restarting it now.")
                    restart_roblox()
                self.prompt_active = False
                self.known_mtime = get_roblox_mtime()
                dialog.destroy()

            def update_on_close():
                log("Update Prompt: User chose 'Update when I close Roblox'")
                self.waiting_for_close = True
                self.prompt_active = False
                dialog.destroy()

            ttk.Button(dialog, text="Update Now (and restart)", style="Accent.TButton", command=update_now).pack(fill=tk.X, padx=20, pady=2)
            ttk.Button(dialog, text="Update when I close Roblox", command=update_on_close).pack(fill=tk.X, padx=20, pady=2)
            ttk.Button(dialog, text="Ask Later", command=ask_later).pack(fill=tk.X, padx=20, pady=2)
        except Exception as e:
            handle_global_error(f"show_update_prompt failed: {e}", traceback.format_exc())

    def apply_silently(self):
        log("Executing apply_silently()...")
        try:
            sf, sc = self.cfg.get("font"), self.cfg.get("cursor_set")
            if sf and sf in self.all_fonts: apply_font(self.all_fonts[sf])
            if sc and sc in self.all_cursor_sets: apply_cursor_set(self.all_cursor_sets[sc])
            log("apply_silently complete.")
        except Exception as e:
            handle_global_error(f"apply_silently failed: {e}", traceback.format_exc())

    def check_roblox_process(self):
        try:
            running = False
            for p in psutil.process_iter(['name']):
                if "roblox" in p.info['name'].lower() and not any(x in p.info['name'].lower() for x in ["crash", "manager"]):
                    running = True; break
            
            if self.waiting_for_close:
                if not running:
                    log("Roblox closed. Applying scheduled patch...")
                    self.apply_silently()
                    self.waiting_for_close = False
                    self.known_mtime = get_roblox_mtime()
            
            elif not self.prompt_active:
                current_mtime = get_roblox_mtime()
                if current_mtime > self.known_mtime:
                    log(f"Roblox update detected! mtime changed from {self.known_mtime} to {current_mtime}")
                    self.prompt_active = True
                    self.after(0, self.show_update_prompt)

            if running and self.cfg.get("show_on_start", True) and not getattr(self, "prev_run", False) and not self.prompt_active:
                log("Roblox launch detected. Showing UI.")
                self.show()
                
            self.prev_run = running
        except Exception as e: 
            # Silence log spam in the loop unless it's a catastrophic issue
            pass
        self.after(2000, self.check_roblox_process)

    def apply(self):
        log("User clicked 'Apply Changes' button.")
        try:
            sf, sc = self.font_var.get(), self.cursor_var.get()
            log(f"UI Selection -> Font: {sf}, Cursor: {sc}")
            
            self.cfg.update({"font": sf, "cursor_set": sc, "show_on_start": not self.show_var.get()})
            save_config(self.cfg)
            
            f_res = apply_font(self.all_fonts[sf]) if sf in self.all_fonts else True
            c_res = apply_cursor_set(self.all_cursor_sets[sc]) if sc in self.all_cursor_sets else True
            
            if f_res and c_res:
                log("Apply successful. Showing info box.")
                messagebox.showinfo("Success", "Modifications Applied. Please restart Roblox.")
            else:
                log("Apply incomplete. Showing warning.")
                messagebox.showwarning("Incomplete", "Some modifications could not be applied or permission denied. Check Diagnostics.")
        except Exception as e:
            handle_global_error(f"UI Apply button crashed: {e}", traceback.format_exc())

    def restore(self):
        log("User clicked 'Restore Default' button.")
        try:
            if messagebox.askyesno("Confirm", "Revert all Roblox fonts and cursors to original?"):
                log("User confirmed restore.")
                restore_defaults()
                messagebox.showinfo("Restored", "Original assets restored.")
            else:
                log("User cancelled restore.")
        except Exception as e:
            handle_global_error(f"UI Restore button crashed: {e}", traceback.format_exc())

    def hide(self): 
        log("Hiding ManagerUI window.")
        self.withdraw()
        
    def show(self):
        log("Showing ManagerUI window.")
        self.deiconify(); self.lift(); self.focus_force()

if __name__ == "__main__":
    log("=== STARTING ROBLOX FONT MANAGER DAEMON ===")
    app = ManagerUI()
    app.withdraw()
    app.mainloop()
'''

MANAGER_HUB_CODE = r'''
import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import traceback

def run_uninstall(parent_window):
    install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    if not messagebox.askyesno("Confirm Uninstall", "Uninstall and remove all files?"): return
    try:
        hub_pid = os.getpid()
        sh_script = os.path.join(os.getenv('TMPDIR', '/tmp'), 'rfm_uninstaller.sh')
        
        plist_path = os.path.expanduser('~/Library/LaunchAgents/com.robloxfontmanager.plist')
        desktop_sc = os.path.expanduser('~/Desktop/Roblox Font Manager Hub.command')
        
        with open(sh_script, 'w', encoding='utf-8') as f:
            f.write(f'#!/bin/bash\n')
            f.write(f'echo "Uninstalling Roblox Font Manager..."\n')
            f.write(f'kill -9 {hub_pid} 2>/dev/null\n')
            f.write(f'pkill -f "auto_font_manager.py" 2>/dev/null\n')
            f.write(f'launchctl unload "{plist_path}" 2>/dev/null\n')
            f.write(f'rm -f "{plist_path}"\n')
            f.write(f'rm -f "{desktop_sc}"\n')
            f.write(f'sleep 2\n')
            f.write(f'rm -rf "{install_dir}"\n')
            f.write(f'rm -f "$0"\n')
        
        os.chmod(sh_script, 0o755)
        subprocess.Popen(['nohup', sh_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)
        parent_window.destroy()
    except Exception as e:
        messagebox.showerror("Uninstall Error", f"Failed to run uninstall: {e}")

if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.title("Roblox Font Manager Hub")
        root.geometry("400x200")
        ttk.Label(root, text="Manager Hub & Uninstaller", font=("Segoe UI", 14, "bold")).pack(pady=20)
        ttk.Button(root, text="Uninstall Application", command=lambda: run_uninstall(root)).pack(fill='x', pady=10, padx=50)
        ttk.Button(root, text="Close", command=root.destroy).pack(pady=10)
        root.mainloop()
    except Exception as e:
        print(f"Hub Fatal Error: {e}")
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
        install_log("Initializing FontChooserApp (Step 2)...")
        try:
            self.win = tk.Toplevel(parent)
            self.win.title("Step 2: Setup Your Library")
            self.win.geometry("1000x700")
            self.win.configure(bg=BG_COLOR)
            self.win.resizable(True, True)
            
            self.install_dir = install_dir
            self.fonts_dir = os.path.join(install_dir, "Fonts")
            self.cursors_dir = os.path.join(install_dir, "Cursors")
            self.font_vars = {} 
            self.cursor_vars = {} 
            self.loaded_fonts = [] 
            self.font_meta_cache = {}
            self.current_tab = "Fonts"
            self.image_cache = [] 
            
            self.font_search_var = tk.StringVar(self.win)
            self.cursor_search_var = tk.StringVar(self.win)

            self._init_checkbox_states()
            self._setup_ui()
            self.win.protocol("WM_DELETE_WINDOW", self.finish_setup)
            install_log("FontChooserApp Initialization complete.")
        except Exception as e:
            installer_handle_error(f"FontChooserApp init crashed: {e}", traceback.format_exc())

    def _init_checkbox_states(self):
        install_log("Scanning extracted assets to initialize checkboxes...")
        try:
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
        except Exception as e:
            installer_handle_error(f"Checkbox state initialization crashed: {e}", traceback.format_exc())

    def _setup_ui(self):
        install_log("Setting up FontChooserApp UI...")
        try:
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
        except Exception as e:
            installer_handle_error(f"FontChooserApp _setup_ui crashed: {e}", traceback.format_exc())

    def switch_tab(self, name):
        install_log(f"FontChooserApp switched tab to: {name}")
        try:
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
        except Exception as e:
            installer_handle_error(f"switch_tab crashed: {e}", traceback.format_exc())

    def refresh_view(self):
        try:
            for widget in self.scroll_frame.winfo_children(): widget.destroy()
            self.image_cache.clear()
            
            if "Fonts" in self.current_tab:
                q = self.font_search_var.get().lower()
                self._render_fonts(self.scroll_frame, q)
            else:
                q = self.cursor_search_var.get().lower()
                self._render_cursors(self.scroll_frame, q)
                
            self.scroll_frame.update_idletasks()
            try:
                self.scroll_frame.master.yview_moveto(0)
            except: pass
        except Exception as e:
            installer_handle_error(f"refresh_view crashed: {e}", traceback.format_exc())

    def _render_fonts(self, frame, search_query=""):
        try:
            if not os.path.exists(self.fonts_dir): return
            font_data = []
            for root, dirs, files in os.walk(self.fonts_dir):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf')):
                        rel = os.path.relpath(os.path.join(root, f), self.fonts_dir).replace("\\", "/")
                        if not search_query or search_query in rel.lower():
                            font_data.append((rel, os.path.join(root, f)))
            
            max_items = 250
            for rel, path in sorted(font_data)[:max_items]:
                card = tk.Frame(frame, bg=SECONDARY_BG, padx=15, pady=10)
                card.pack(fill="x", pady=5)
                if rel not in self.font_vars: self.font_vars[rel] = tk.BooleanVar(self.win, value=False)
                tk.Checkbutton(card, text=rel, variable=self.font_vars[rel], bg=SECONDARY_BG, fg=TEXT_PRIMARY, selectcolor=BG_COLOR, font=("Segoe UI", 10)).pack(side="left")
                
                if path not in self.font_meta_cache:
                    self.font_meta_cache[path] = self.get_font_family_from_file(path) or "Arial"
                
                fam = self.font_meta_cache[path]
                tk.Label(card, text="AaBb 123", font=(fam, 14), bg=SECONDARY_BG, fg=TEXT_PRIMARY).pack(side="right", padx=10)
            
            if len(font_data) > max_items:
                tk.Label(frame, text=f"...and {len(font_data) - max_items} more fonts. Use the search bar to find them!", bg=BG_COLOR, fg=TEXT_SECONDARY, font=("Segoe UI", 10, "italic")).pack(pady=20)
        except Exception as e:
            installer_handle_error(f"_render_fonts crashed: {e}", traceback.format_exc())

    def _render_cursors(self, frame, search_query=""):
        try:
            if not os.path.exists(self.cursors_dir): return
            sets = [d for d in os.listdir(self.cursors_dir) if os.path.isdir(os.path.join(self.cursors_dir, d))]
            for d in sorted(sets):
                if search_query and search_query not in d.lower(): continue
                card = tk.Frame(frame, bg=SECONDARY_BG, padx=15, pady=10)
                card.pack(fill="x", pady=5)
                is_m = (d == "Normal")
                if d not in self.cursor_vars: self.cursor_vars[d] = tk.BooleanVar(self.win, value=is_m)
                tk.Checkbutton(card, text=f"Set: {d}", variable=self.cursor_vars[d], bg=SECONDARY_BG, fg=TEXT_PRIMARY, selectcolor=BG_COLOR, state='disabled' if is_m else 'normal').pack(side="left")

                preview_frame = tk.Frame(card, bg=SECONDARY_BG)
                preview_frame.pack(side="right", padx=10)
                
                set_path = os.path.join(self.cursors_dir, d)
                c_files = ["ArrowCursor.png", "ArrowFarCursor.png", "IBeamCursor.png", "MouseLockedCursor.png", "MouseLockedCursor@2x.png"]
                
                for cf in c_files:
                    img_path = os.path.join(set_path, cf)
                    if os.path.exists(img_path):
                        try:
                            img = tk.PhotoImage(master=self.win, file=img_path)
                            img = img.zoom(2, 2) 
                            self.image_cache.append(img)
                            tk.Label(preview_frame, image=img, bg=SECONDARY_BG).pack(side="left", padx=5)
                        except Exception:
                            pass
        except Exception as e:
            installer_handle_error(f"_render_cursors crashed: {e}", traceback.format_exc())

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

    def add_custom_font(self):
        install_log("User clicked '+ Add Custom Font'")
        try:
            p = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
            if p:
                fn = os.path.basename(p); shutil.copy2(p, os.path.join(self.fonts_dir, fn))
                self.font_vars[fn] = tk.BooleanVar(self.win, value=False); self.switch_tab("Import Fonts")
                install_log(f"Custom font imported: {fn}")
        except Exception as e:
            installer_handle_error(f"add_custom_font crashed: {e}", traceback.format_exc())

    def add_custom_cursor_set(self):
        install_log("User clicked '+ Import Cursor Set'")
        try:
            d = filedialog.askdirectory(title="Select Cursor Set Folder")
            if d:
                n = os.path.basename(d); shutil.copytree(d, os.path.join(self.cursors_dir, n), dirs_exist_ok=True)
                self.cursor_vars[n] = tk.BooleanVar(self.win, value=False); self.switch_tab("Import Cursors")
                install_log(f"Custom cursor set imported: {n}")
        except Exception as e:
            installer_handle_error(f"add_custom_cursor_set crashed: {e}", traceback.format_exc())

    def finish_setup(self):
        install_log("User clicked 'Finish Setup'. Cleaning up unselected assets...")
        try:
            rem = 0
            for rel, v in self.font_vars.items():
                if not v.get():
                    p = os.path.join(self.fonts_dir, rel)
                    if os.path.exists(p): 
                        os.remove(p)
                        rem += 1
                        install_log(f"Deleted unselected font: {rel}")
            for rel, v in self.cursor_vars.items():
                if not v.get():
                    p = os.path.join(self.cursors_dir, rel)
                    if os.path.exists(p): 
                        shutil.rmtree(p)
                        rem += 1
                        install_log(f"Deleted unselected cursor set: {rel}")
            install_log(f"Cleanup complete. Removed {rem} unselected items.")
            self.win.destroy()
        except Exception as e:
            installer_handle_error(f"finish_setup crashed: {e}", traceback.format_exc())

# --- STEP 1: THE INSTALLER (macOS Adapted) ---
class InstallerApp:
    def __init__(self, root):
        install_log("=== STARTING MACOS INSTALLER ===")
        try:
            self.root = root
            self.root.title("Roblox Font Manager Installer (macOS)")
            self.root.geometry("500x420")
            self.root.configure(bg=BG_COLOR)
            
            self.install_dir = os.path.expanduser('~/Library/Application Support/RobloxFontManager')
            install_log(f"Target Install Directory: {self.install_dir}")
            
            style_ttk(self.root)
            self.image_cache = [] 
            self._setup_ui()
            install_log("Installer UI built successfully.")
        except Exception as e:
            installer_handle_error(f"Installer init crashed: {e}", traceback.format_exc())

    def _setup_ui(self):
        try:
            c = tk.Frame(self.root, bg=BG_COLOR, padx=40, pady=40)
            c.pack(fill="both", expand=True)
            tk.Label(c, text="Roblox Font Manager", font=("Segoe UI", 24, "bold"), bg=BG_COLOR, fg=TEXT_PRIMARY).pack(pady=(0, 10))
            tk.Label(c, text="Step 1: System Installation (macOS)", font=("Segoe UI", 11), bg=BG_COLOR, fg=TEXT_SECONDARY).pack()
            
            self.status_lbl = tk.Label(c, text="System Ready", font=("Segoe UI", 10), bg=BG_COLOR, fg=ACCENT_COLOR)
            self.status_lbl.pack(pady=(40, 5))
            self.pb = ttk.Progressbar(c, length=400, mode='determinate', style="Custom.Horizontal.TProgressbar")
            self.pb.pack(pady=10)
            self.install_btn = ttk.Button(c, text="Install Now", style="Accent.TButton", command=self.run_install)
            self.install_btn.pack(pady=30, ipady=5, fill="x")
        except Exception as e:
            installer_handle_error(f"Installer _setup_ui crashed: {e}", traceback.format_exc())

    def run_install(self):
        install_log("User clicked 'Install Now'. Starting installation thread...")
        try:
            self.install_btn.config(state='disabled')
            threading.Thread(target=self._install_thread).start()
        except Exception as e:
            installer_handle_error(f"Failed to start installation thread: {e}", traceback.format_exc())

    def _get_python_path(self):
        return sys.executable

    def _install_thread(self):
        try:
            install_log("Killing any previous auto_font_manager processes...")
            subprocess.call('pkill -f "auto_font_manager.py"', shell=True)
            
            self._update(15, "Initializing environment...")
            py = self._get_python_path()
            install_log(f"Using Python executable: {py}")
            
            os.makedirs(self.install_dir, exist_ok=True)
            os.makedirs(os.path.join(self.install_dir, "Fonts"), exist_ok=True)
            os.makedirs(os.path.join(self.install_dir, "Cursors"), exist_ok=True)
            
            self._update(40, "Extracting libraries (Fonts.zip)...")
            bd = os.path.dirname(os.path.abspath(__file__))
            
            zp_fonts = os.path.join(bd, "Fonts.zip")
            install_log(f"Looking for Fonts.zip at: {zp_fonts}")
            if os.path.exists(zp_fonts):
                install_log("Fonts.zip found, extracting...")
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
            else:
                install_log("Warning: Fonts.zip not found in working directory.")

            self._update(60, "Extracting cursors...")
            zc = os.path.join(bd, "Cursors.zip")
            install_log(f"Looking for Cursors.zip at: {zc}")
            if os.path.exists(zc):
                install_log("Cursors.zip found, extracting...")
                with zipfile.ZipFile(zc, 'r') as z: z.extractall(os.path.join(self.install_dir, "Cursors"))
            else:
                install_log("Warning: Cursors.zip not found in working directory.")
            
            self._update(75, "Installing macOS dependencies (psutil, pynput)...")
            install_log("Running pip install psutil pynput...")
            subprocess.check_call([py, "-m", "pip", "install", "psutil", "pynput"], stdout=subprocess.DEVNULL)
            install_log("Dependencies installed successfully.")
            
            self._update(90, "Deploying macOS system files & LaunchAgent...")
            auto_mgr_path = os.path.join(self.install_dir, 'auto_font_manager.py')
            hub_mgr_path = os.path.join(self.install_dir, 'manager.py')
            
            install_log(f"Writing {auto_mgr_path}...")
            with open(auto_mgr_path, 'w', encoding='utf-8') as f: f.write(AUTO_MANAGER_CODE)
            install_log(f"Writing {hub_mgr_path}...")
            with open(hub_mgr_path, 'w', encoding='utf-8') as f: f.write(MANAGER_HUB_CODE)
            
            install_log("Creating desktop shortcut (.command script)...")
            self.create_shortcut(py, hub_mgr_path)
            
            plist_path = os.path.expanduser('~/Library/LaunchAgents/com.robloxfontmanager.plist')
            os.makedirs(os.path.dirname(plist_path), exist_ok=True)
            
            install_log(f"Writing macOS LaunchAgent plist to: {plist_path}")
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.robloxfontmanager</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py}</string>
        <string>{auto_mgr_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>"""
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            self._update(100, "Stage 1 Finished!")
            install_log("Stage 1 installation complete. Handing over to Step 2 (FontChooserApp).")
            self.root.after(0, self.start_step_2, plist_path)
        except Exception as e:
            installer_handle_error(f"Installation Thread Failed: {e}", traceback.format_exc())
            self.root.after(0, lambda: self.install_btn.config(state='normal'))

    def _update(self, val, msg):
        self.root.after(0, lambda: self.pb.configure(value=val))
        self.root.after(0, lambda: self.status_lbl.configure(text=msg))

    def start_step_2(self, plist_path):
        try:
            self.root.withdraw()
            nr = tk.Tk()
            nr.withdraw()
            style_ttk(nr)
            FontChooserApp(nr, self.install_dir)
            nr.mainloop()
            
            install_log("Loading macOS LaunchAgent (Starting Daemon)...")
            if os.path.exists(plist_path): 
                subprocess.Popen(['launchctl', 'load', plist_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                install_log("LaunchAgent loaded successfully.")
                
            self.root.destroy()
        except Exception as e:
            installer_handle_error(f"start_step_2 crashed: {e}", traceback.format_exc())

    def create_shortcut(self, py, script):
        try:
            target = os.path.expanduser("~/Desktop/Roblox Font Manager Hub.command")
            install_log(f"Creating .command script at: {target}")
            with open(target, 'w') as f:
                f.write(f'#!/bin/bash\n"{py}" "{script}"\n')
            os.chmod(target, 0o755)
            install_log("Shortcut created and made executable.")
        except Exception as e:
            installer_handle_error(f"Shortcut creation failed: {e}", traceback.format_exc())

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = InstallerApp(root)
        root.mainloop()
    except Exception as e:
        installer_handle_error(f"Fatal Installer Launch Error: {e}", traceback.format_exc())