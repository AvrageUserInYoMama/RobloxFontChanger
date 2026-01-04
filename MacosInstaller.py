#!/usr/bin/env python3
# ============================================================
# ROBLOX FONT & CURSOR MANAGER — macOS (HARDENED SINGLE FILE)
# ============================================================

import os
import sys
import time
import json
import shutil
import hashlib
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# ------------------------------------------------------------
# PLATFORM GUARD
# ------------------------------------------------------------
if sys.platform != "darwin":
    messagebox.showerror("Unsupported OS", "This application is for macOS only.")
    sys.exit(1)

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
INSTALL_DIR = os.path.join(os.path.expanduser("~/Library/Application Support"), "RobloxFontManager")
FONTS_DIR = os.path.join(INSTALL_DIR, "Fonts")
CURSORS_DIR = os.path.join(INSTALL_DIR, "Cursors")
CONFIG_FILE = os.path.join(INSTALL_DIR, "config.json")
VENDOR_DIR = os.path.join(BASE_DIR, "vendor")

ROBLOX_SYS_APP = "/Applications/Roblox.app"
ROBLOX_USER_APP = os.path.expanduser("~/Applications/Roblox.app")

SAFE_UI_FONTS = {
    "Gotham.ttf",
    "GothamMedium.ttf",
    "GothamBold.ttf"
}

KEYS_MAP = {
    "F9": "f9",
    "F10": "f10",
    "F11": "f11"
}

# ------------------------------------------------------------
# DEPENDENCIES (VENDORED ONLY)
# ------------------------------------------------------------
sys.path.insert(0, VENDOR_DIR)
try:
    import psutil
    from pynput import keyboard
except Exception as e:
    messagebox.showerror(
        "Missing Dependencies",
        "Required components could not be loaded.\n\n"
        "Ensure the 'vendor' folder exists next to this file.\n\n"
        f"Error:\n{e}"
    )
    sys.exit(1)

# ------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------
def get_roblox_content_path():
    if os.path.exists(ROBLOX_SYS_APP):
        return os.path.join(ROBLOX_SYS_APP, "Contents", "Resources", "content")
    if os.path.exists(ROBLOX_USER_APP):
        return os.path.join(ROBLOX_USER_APP, "Contents", "Resources", "content")
    return None

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def ensure_input_monitoring():
    try:
        l = keyboard.Listener(on_press=lambda k: None)
        l.start()
        l.stop()
        return True
    except Exception:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Permission Required",
            "Hotkeys require Input Monitoring permission.\n\n"
            "System Settings → Privacy & Security → Input Monitoring\n\n"
            "Add your Python executable, then relaunch."
        )
        root.destroy()
        return False

def restart_roblox():
    for p in psutil.process_iter(["name"]):
        try:
            if p.info["name"] and p.info["name"].lower() == "roblox":
                p.terminate()
        except:
            pass
    time.sleep(2)
    subprocess.Popen(["open", "-a", "Roblox"])

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
def load_config():
    defaults = {
        "font": None,
        "cursor": None,
        "font_hash": None,
        "hotkey": "F9",
        "show_on_start": True
    }
    if not os.path.exists(CONFIG_FILE):
        return defaults
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            defaults.update(cfg)
            return defaults
    except:
        return defaults

def save_config(cfg):
    os.makedirs(INSTALL_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

# ------------------------------------------------------------
# APPLY LOGIC
# ------------------------------------------------------------
def apply_font(font_path, cfg):
    content = get_roblox_content_path()
    if not content:
        return False

    font_dir = os.path.join(content, "fonts")
    if not os.path.exists(font_dir):
        return False

    for f in os.listdir(font_dir):
        if f in SAFE_UI_FONTS:
            try:
                shutil.copy2(font_path, os.path.join(font_dir, f))
            except:
                pass

    cfg["font_hash"] = sha256_file(font_path)
    save_config(cfg)
    return True

def apply_cursor_set(cursor_dir):
    content = get_roblox_content_path()
    if not content:
        return False

    target = os.path.join(content, "textures", "Cursors", "KeyboardMouse")
    if not os.path.exists(target):
        return False

    for f in ["ArrowCursor.png", "ArrowFarCursor.png", "IBeamCursor.png"]:
        src = os.path.join(cursor_dir, f)
        if os.path.exists(src):
            try:
                shutil.copy2(src, os.path.join(target, f))
            except:
                pass
    return True

# ------------------------------------------------------------
# MAIN UI
# ------------------------------------------------------------
class ManagerUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Roblox Font & Cursor Manager")
        self.geometry("700x600")
        self.resizable(False, False)

        self.cfg = load_config()

        self.font_var = tk.StringVar(value=self.cfg["font"])
        self.cursor_var = tk.StringVar(value=self.cfg["cursor"])
        self.hotkey_var = tk.StringVar(value=self.cfg["hotkey"])

        self.fonts = {}
        self.cursors = {}

        self._build_ui()
        self._scan_libs()

        if not ensure_input_monitoring():
            sys.exit(0)

        self.listener = keyboard.Listener(on_press=self._on_key)
        self.listener.start()

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        ftab = ttk.Frame(nb)
        nb.add(ftab, text="Fonts")
        self.font_box = ttk.Combobox(ftab, textvariable=self.font_var, state="readonly", width=50)
        self.font_box.pack(pady=20)
        ttk.Button(ftab, text="Add Font", command=self._add_font).pack()

        ctab = ttk.Frame(nb)
        nb.add(ctab, text="Cursors")
        self.cursor_box = ttk.Combobox(ctab, textvariable=self.cursor_var, state="readonly", width=50)
        self.cursor_box.pack(pady=20)
        ttk.Button(ctab, text="Add Cursor Set", command=self._add_cursor).pack()

        bot = ttk.Frame(self)
        bot.pack(fill="x", pady=20)
        ttk.Button(bot, text="Apply", command=self._apply).pack(side="right", padx=10)
        ttk.Button(bot, text="Restart Roblox", command=restart_roblox).pack(side="right")

    def _scan_libs(self):
        os.makedirs(FONTS_DIR, exist_ok=True)
        os.makedirs(CURSORS_DIR, exist_ok=True)

        self.fonts = {
            f: os.path.join(FONTS_DIR, f)
            for f in os.listdir(FONTS_DIR)
            if f.lower().endswith((".ttf", ".otf"))
        }
        self.cursors = {
            d: os.path.join(CURSORS_DIR, d)
            for d in os.listdir(CURSORS_DIR)
            if os.path.isdir(os.path.join(CURSORS_DIR, d))
        }

        self.font_box["values"] = sorted(self.fonts.keys())
        self.cursor_box["values"] = sorted(self.cursors.keys())

    def _add_font(self):
        p = filedialog.askopenfilename(filetypes=[("Font", "*.ttf *.otf")])
        if p:
            shutil.copy2(p, os.path.join(FONTS_DIR, os.path.basename(p)))
            self._scan_libs()

    def _add_cursor(self):
        d = filedialog.askdirectory()
        if d:
            dst = os.path.join(CURSORS_DIR, os.path.basename(d))
            shutil.copytree(d, dst, dirs_exist_ok=True)
            self._scan_libs()

    def _apply(self):
        if self.font_var.get() in self.fonts:
            apply_font(self.fonts[self.font_var.get()], self.cfg)
        if self.cursor_var.get() in self.cursors:
            apply_cursor_set(self.cursors[self.cursor_var.get()])

        self.cfg["font"] = self.font_var.get()
        self.cfg["cursor"] = self.cursor_var.get()
        save_config(self.cfg)

        messagebox.showinfo("Success", "Changes applied. Restart Roblox.")

    def _on_key(self, key):
        try:
            if key == getattr(keyboard.Key, KEYS_MAP[self.hotkey_var.get()]):
                self.after(0, self.deiconify)
        except:
            pass

# ------------------------------------------------------------
# ENTRY
# ------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(INSTALL_DIR, exist_ok=True)
    app = ManagerUI()
    app.mainloop()
