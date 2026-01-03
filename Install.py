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

# --- EMBEDDED SCRIPTS ---

# This script runs silently and pops up the menu when Roblox is launched or hotkey is pressed.
AUTO_MANAGER_CODE = r'''
import os
import sys
import json
import shutil
import ctypes
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont
from datetime import datetime
from ctypes import wintypes
import time

# --- Dependency Check ---
try:
    import psutil
except ImportError:
    sys.exit(1)

# ---------------- CONFIG ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
APP_NAME = "Roblox Font & Cursor Manager"
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
FONTS_LIB_DIR = os.path.join(BASE_DIR, "Fonts")
CURSORS_LIB_DIR = os.path.join(BASE_DIR, "Cursors")

ROBLOX_URI = "roblox-player:"
HOTKEY_ID = 1
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000

KEYS_MAP = {
    "F9": (0, 0x78),
    "F10": (0, 0x79),
    "F11": (0, 0x7A),
    "Ctrl + Grave (`)": (MOD_CONTROL, 0xC0)
}

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

def restart_roblox():
    found = False
    for proc in psutil.process_iter(['name']):
        try:
            pname = proc.name().lower()
            if "roblox" in pname and not any(x in pname for x in ["manager", "crash", "launcher"]):
                proc.terminate()
                found = True
        except (psutil.NoSuchProcess, psutil.AccessDenied): continue
    if found: time.sleep(2)
    subprocess.Popen(["cmd", "/c", "start", ROBLOX_URI], shell=True)

def apply_font(font_path):
    roblox_path = os.path.join(os.getenv("LOCALAPPDATA"), "Roblox", "Versions")
    if not os.path.exists(roblox_path): return

    for root, dirs, files in os.walk(roblox_path):
        if "Fonts.old" in root: continue
        if os.path.basename(root).lower() == "fonts" and "content" in root.lower():
            backup_dir = os.path.join(root, "Fonts.old")
            os.makedirs(backup_dir, exist_ok=True)
            for f in files:
                if f.lower().endswith((".ttf", ".otf")) and not f.lower().startswith("twemoji"):
                    src = os.path.join(root, f)
                    back = os.path.join(backup_dir, f)
                    try:
                        if not os.path.exists(back): shutil.move(src, back)
                        shutil.copy2(font_path, src)
                    except: pass

def apply_cursor_set(set_path):
    if not set_path or not os.path.isdir(set_path): return

    roblox_path = os.path.join(os.getenv("LOCALAPPDATA"), "Roblox", "Versions")
    cursor_files = ["ArrowCursor.png", "ArrowFarCursor.png", "IBeamCursor.png"]

    for root, dirs, files in os.walk(roblox_path):
        if "Cursors.old" in root: continue
        if os.path.basename(root) == "KeyboardMouse" and "textures" in root.lower():
            backup_dir = os.path.join(root, "Cursors.old")
            os.makedirs(backup_dir, exist_ok=True)
            for c_file in cursor_files:
                src_in_lib = os.path.join(set_path, c_file)
                target_in_roblox = os.path.join(root, c_file)
                if os.path.exists(src_in_lib):
                    try:
                        if os.path.exists(target_in_roblox) and not os.path.exists(os.path.join(backup_dir, c_file)):
                            shutil.move(target_in_roblox, os.path.join(backup_dir, c_file))
                        shutil.copy2(src_in_lib, target_in_roblox)
                    except: pass

# ---------------- MAIN UI ---------------- #

class ManagerUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("700x650")
        self.resizable(False, False)

        self.cfg = load_config()
        self.roblox_running_prev = False
        self.all_fonts = {}
        self.all_cursor_sets = {}
        self.trigger_show = False
        
        # UI Variables
        self.font_var = tk.StringVar(value=self.cfg.get("font"))
        self.cursor_var = tk.StringVar(value=self.cfg.get("cursor_set"))
        self.hotkey_var = tk.StringVar(value=self.cfg.get("hotkey", "F9"))
        self.show_var = tk.BooleanVar(value=not self.cfg.get("show_on_start", True))
        
        # Thread-safe variable for hotkey (Tkinter vars are unsafe in threads)
        self.cur_hotkey_val = self.cfg.get("hotkey", "F9")

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.hide)
        self.refresh_libraries()
        
        # Start loops
        self.check_hotkey_trigger() # Runs fast (100ms)
        self.check_roblox_process() # Runs slow (2000ms)
        
        # Start hotkey thread
        threading.Thread(target=self.hotkey_thread_runner, daemon=True).start()

    def create_widgets(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # Fonts Tab
        f_tab = ttk.Frame(nb)
        nb.add(f_tab, text="Fonts")
        top_f = ttk.Frame(f_tab)
        top_f.pack(fill="x", padx=10, pady=10)
        ttk.Label(top_f, text="Select Font:").pack(side="left")
        self.f_list = ttk.Combobox(top_f, textvariable=self.font_var, state="readonly", width=40)
        self.f_list.pack(side="left", padx=5)
        ttk.Button(top_f, text="Add Font...", command=self.add_font_manually).pack(side="left", padx=5)

        # Cursors Tab
        c_tab = ttk.Frame(nb)
        nb.add(c_tab, text="Cursors")
        top_c = ttk.Frame(c_tab)
        top_c.pack(fill="x", padx=10, pady=10)
        ttk.Label(top_c, text="Select Cursor Set:").pack(side="left")
        self.c_list = ttk.Combobox(top_c, textvariable=self.cursor_var, state="readonly", width=40)
        self.c_list.pack(side="left", padx=5)
        ttk.Button(top_c, text="Import Set Folder...", command=self.add_cursor_set_manually).pack(side="left", padx=5)
        ttk.Label(c_tab, text="Required files in folder:\n- ArrowCursor.png\n- ArrowFarCursor.png\n- IBeamCursor.png", justify="left").pack(pady=10, padx=20, anchor="w")

        self.status = ttk.Label(self, text="Status: Scanning for Roblox...", font=("Segoe UI", 10, "italic"))
        self.status.pack(pady=5)

        settings_frame = ttk.LabelFrame(self, text="Settings", padding=10)
        settings_frame.pack(fill="x", padx=20, pady=5)
        h_frame = ttk.Frame(settings_frame)
        h_frame.pack(fill="x")
        ttk.Label(h_frame, text="Menu Hotkey:").pack(side="left")
        self.h_list = ttk.Combobox(h_frame, textvariable=self.hotkey_var, values=list(KEYS_MAP.keys()), state="readonly", width=20)
        self.h_list.pack(side="left", padx=10)
        self.h_list.bind("<<ComboboxSelected>>", self.on_hotkey_change)
        ttk.Checkbutton(settings_frame, text="Do not show again on Roblox start", variable=self.show_var).pack(anchor="w", pady=5)
        
        bot = ttk.Frame(self)
        bot.pack(fill="x", side="bottom", padx=20, pady=20)
        btns = ttk.Frame(bot)
        btns.pack(side="right")
        ttk.Button(btns, text="Apply Changes", command=self.apply).pack(side="left", padx=5)
        ttk.Button(btns, text="Restart Roblox", command=restart_roblox).pack(side="left", padx=5)
        ttk.Button(btns, text="Close", command=self.hide).pack(side="left", padx=5)

    def refresh_libraries(self):
        self.all_fonts = {}
        if os.path.exists(FONTS_LIB_DIR):
            for root, dirs, files in os.walk(FONTS_LIB_DIR):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf')):
                        rel = os.path.relpath(os.path.join(root, f), FONTS_LIB_DIR)
                        display_name = rel.replace("\\", "/")
                        self.all_fonts[display_name] = os.path.join(root, f)
        self.f_list['values'] = sorted(list(self.all_fonts.keys()))
        
        self.all_cursor_sets = {}
        if os.path.exists(CURSORS_LIB_DIR):
            for root, dirs, files in os.walk(CURSORS_LIB_DIR):
                if any(f.lower().endswith('.png') for f in files):
                    if root == CURSORS_LIB_DIR: continue
                    rel = os.path.relpath(root, CURSORS_LIB_DIR)
                    display_name = rel.replace("\\", "/")
                    self.all_cursor_sets[display_name] = root
        self.c_list['values'] = sorted(list(self.all_cursor_sets.keys()))

    def add_font_manually(self):
        f = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if f:
            os.makedirs(FONTS_LIB_DIR, exist_ok=True)
            name = os.path.basename(f)
            dst = os.path.join(FONTS_LIB_DIR, name)
            try:
                shutil.copy2(f, dst)
                self.refresh_libraries()
                self.font_var.set(name)
                messagebox.showinfo("Font Added", "Font added to library.")
            except Exception as e: messagebox.showerror("Error", str(e))

    def add_cursor_set_manually(self):
        d = filedialog.askdirectory(title="Select Folder containing Cursor PNGs")
        if d:
            name = os.path.basename(d)
            dst = os.path.join(CURSORS_LIB_DIR, name)
            os.makedirs(dst, exist_ok=True)
            for f in os.listdir(d):
                if f.lower().endswith(".png"): shutil.copy2(os.path.join(d, f), dst)
            self.refresh_libraries()
            self.cursor_var.set(name)
            messagebox.showinfo("Set Added", "Cursor set imported.")

    def hotkey_thread_runner(self):
        user32 = ctypes.windll.user32
        msg = wintypes.MSG()
        
        while True:
            # Use thread-safe variable instead of Tkinter var
            hk_name = self.cur_hotkey_val
            
            if hk_name in KEYS_MAP:
                mod, vk = KEYS_MAP[hk_name]
                user32.UnregisterHotKey(None, HOTKEY_ID)
                success = user32.RegisterHotKey(None, HOTKEY_ID, mod | MOD_NOREPEAT, vk)
                if not success:
                    print(f"Failed to register hotkey: {hk_name}")

            # GetMessageW is blocking, but will wake on hotkey press
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312: # WM_HOTKEY
                    self.trigger_show = True
                
                # Check if hotkey setting changed in UI
                if self.cur_hotkey_val != hk_name:
                    break
            time.sleep(1)

    def on_hotkey_change(self, event):
        self.cfg["hotkey"] = self.hotkey_var.get()
        self.cur_hotkey_val = self.hotkey_var.get() # Update thread-safe var
        save_config(self.cfg)

    def check_hotkey_trigger(self):
        """Fast loop just for hotkeys (100ms)"""
        if self.trigger_show:
            self.trigger_show = False
            self.show()
        self.after(100, self.check_hotkey_trigger)

    def check_roblox_process(self):
        """Slow loop for process scanning (2000ms)"""
        try:
            is_running = False
            detected_proc_name = ""
            for p in psutil.process_iter(['name']):
                try:
                    pname = p.info['name']
                    if pname:
                        pname_lower = pname.lower()
                        if "roblox" in pname_lower and pname_lower.endswith(".exe"):
                            if not any(x in pname_lower for x in ["crash", "manager", "launcher"]):
                                is_running = True
                                detected_proc_name = pname
                                break
                except: continue
            
            # Roblox Opened
            if is_running and not self.roblox_running_prev:
                if self.cfg.get("show_on_start", True):
                    self.show()
                
                if self.needs_upd():
                    self.status.config(text="Status: Update Detected! (Re-apply mods)", foreground="orange")
                else:
                    self.status.config(text="Status: Mods are active", foreground="green")
            
            # Roblox Closed
            if not is_running and self.roblox_running_prev:
                self.hide()
            
            self.roblox_running_prev = is_running
        except: pass

        self.after(2000, self.check_roblox_process)

    def needs_upd(self):
        rp = os.path.join(os.getenv("LOCALAPPDATA"), "Roblox", "Versions")
        if not os.path.exists(rp): return False
        
        try:
            versions = []
            for d in os.listdir(rp):
                vp = os.path.join(rp, d)
                if os.path.isdir(vp) and d.startswith("version-"):
                    files = os.listdir(vp)
                    if any(f.lower().endswith(".exe") for f in files):
                        versions.append(vp)
            
            if not versions: return False
            latest_version = max(versions, key=os.path.getmtime)
            
            font_dir = os.path.join(latest_version, "content", "fonts")
            if os.path.exists(font_dir):
                 if not os.path.exists(os.path.join(font_dir, "Fonts.old")): return True

            cursor_dir = os.path.join(latest_version, "content", "textures", "Cursors", "KeyboardMouse")
            if os.path.exists(cursor_dir):
                if not os.path.exists(os.path.join(cursor_dir, "Cursors.old")): return True
        except: pass
            
        return False

    def apply(self):
        selected_font_display = self.font_var.get()
        selected_cursor_display = self.cursor_var.get()
        
        self.cfg["font"] = selected_font_display
        self.cfg["cursor_set"] = selected_cursor_display
        self.cfg["show_on_start"] = not self.show_var.get()
        save_config(self.cfg)
        
        if selected_font_display in self.all_fonts:
            apply_font(self.all_fonts[selected_font_display])
        if selected_cursor_display in self.all_cursor_sets:
            apply_cursor_set(self.all_cursor_sets[selected_cursor_display])
            
        self.status.config(text="Status: Changes Applied!", foreground="green")
        messagebox.showinfo("Success", "Changes applied. Please restart Roblox.")

    def hide(self): 
        self.withdraw()

    def show(self):
        self.deiconify()
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except: pass
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

# --- INSTALLER CLASSES ---

class FontChooserApp:
    def __init__(self, parent, install_dir):
        self.win = tk.Toplevel(parent)
        self.win.title("Step 2: Setup Your Library")
        self.win.geometry("750x750")
        self.install_dir = install_dir
        self.fonts_dir = os.path.join(install_dir, "Fonts")
        self.cursors_dir = os.path.join(install_dir, "Cursors")
        
        # Tracking variables
        self.font_vars = {} # {rel_path: BooleanVar}
        self.cursor_vars = {} # {rel_path: BooleanVar}
        self.loaded_fonts = [] # List of font paths loaded into memory
        
        self._setup_ui()
        self.win.protocol("WM_DELETE_WINDOW", self.finish_setup)

    def _setup_ui(self):
        nb = ttk.Notebook(self.win)
        nb.pack(fill='both', expand=True, padx=10, pady=10)

        ft = ttk.Frame(nb)
        nb.add(ft, text="Import Fonts")
        self.f_can = tk.Canvas(ft)
        sb1 = ttk.Scrollbar(ft, orient="vertical", command=self.f_can.yview)
        self.f_can.configure(yscrollcommand=sb1.set) # Link scrollbar to canvas
        
        self.f_sf = ttk.Frame(self.f_can)
        self.f_sf.bind("<Configure>", lambda e: self.f_can.configure(scrollregion=self.f_can.bbox("all")))
        self.f_can.create_window((0,0), window=self.f_sf, anchor="nw")
        
        sb1.pack(side="right", fill="y") # Pack scrollbar first
        self.f_can.pack(side="left", fill="both", expand=True)
        
        ct = ttk.Frame(nb)
        nb.add(ct, text="Import Cursors")
        self.c_can = tk.Canvas(ct)
        sb2 = ttk.Scrollbar(ct, orient="vertical", command=self.c_can.yview)
        self.c_can.configure(yscrollcommand=sb2.set) # Link scrollbar to canvas
        
        self.c_sf = ttk.Frame(self.c_can)
        self.c_sf.bind("<Configure>", lambda e: self.c_can.configure(scrollregion=self.c_can.bbox("all")))
        self.c_can.create_window((0,0), window=self.c_sf, anchor="nw")
        
        sb2.pack(side="right", fill="y") # Pack scrollbar first
        self.c_can.pack(side="left", fill="both", expand=True)

        self._load_items()
        
        f = ttk.Frame(self.win, padding=20)
        f.pack(fill='x', side='bottom')
        ttk.Button(f, text="Add Custom Font...", command=self.add_custom_font).pack(side='left', padx=5)
        ttk.Button(f, text="Import Cursor Set...", command=self.add_custom_cursor_set).pack(side='left', padx=5)
        ttk.Button(f, text="Finish Setup", command=self.finish_setup).pack(side='right')

    def get_font_family_from_file(self, filepath):
        """Simple parser to extract the family name (ID 1) from the name table of a TTF/OTF"""
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
        except: return None
        
        def get_ushort(i): return struct.unpack('>H', data[i:i+2])[0]
        def get_ulong(i): return struct.unpack('>L', data[i:i+4])[0]
        
        if data[:4] not in [b'\x00\x01\x00\x00', b'OTTO', b'true']: return None # Signature check
        
        num_tables = get_ushort(4)
        name_table_offset = 0
        offset = 12
        for _ in range(num_tables):
            tag = data[offset:offset+4]
            if tag == b'name':
                name_table_offset = get_ulong(offset+8)
                break
            offset += 16
        
        if name_table_offset == 0: return None
        
        count = get_ushort(name_table_offset + 2)
        string_offset = get_ushort(name_table_offset + 4) + name_table_offset
        name_records_offset = name_table_offset + 6
        
        family_name = None
        for i in range(count):
            rec_off = name_records_offset + i * 12
            platform_id = get_ushort(rec_off)
            encoding_id = get_ushort(rec_off + 2)
            name_id = get_ushort(rec_off + 6)
            length = get_ushort(rec_off + 8)
            offset = get_ushort(rec_off + 10)
            
            if name_id == 1: # Family Name
                name_bytes = data[string_offset + offset : string_offset + offset + length]
                try:
                    # Windows Unicode (Platform 3, Enc 1)
                    if platform_id == 3 and encoding_id == 1:
                        return name_bytes.decode('utf-16-be')
                    # Mac Roman (Platform 1, Enc 0)
                    elif platform_id == 1 and encoding_id == 0:
                        decoded = name_bytes.decode('mac_roman')
                        # Save as fallback, prefer Windows if found later
                        if family_name is None: family_name = decoded
                except: pass
        return family_name

    def load_font_memory(self, path):
        """Loads font into Windows memory for the session"""
        try:
            # AddFontResourceExW flag 0x10 is FR_PRIVATE (process local)
            res = ctypes.windll.gdi32.AddFontResourceExW(path, 0x10, 0)
            if res > 0:
                self.loaded_fonts.append(path)
                return True
        except: pass
        return False

    def _load_items(self):
        for widget in self.f_sf.winfo_children(): widget.destroy()
        for widget in self.c_sf.winfo_children(): widget.destroy()

        # Load Fonts recursively
        if os.path.exists(self.fonts_dir):
            font_data = []
            for root, dirs, files in os.walk(self.fonts_dir):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf')):
                        rel = os.path.relpath(os.path.join(root, f), self.fonts_dir)
                        full_path = os.path.join(root, f)
                        font_data.append((rel.replace("\\", "/"), full_path))
            
            for rel, path in sorted(font_data, key=lambda x: x[0]):
                fr = ttk.Frame(self.f_sf); fr.pack(fill='x', pady=5, padx=5)
                
                # Checkbox for selection
                if rel not in self.font_vars:
                    self.font_vars[rel] = tk.BooleanVar(value=False) # Default to deselected
                
                chk = ttk.Checkbutton(fr, text=rel, variable=self.font_vars[rel])
                chk.pack(side='left', padx=5, anchor='w')
                
                # Preview Logic
                preview_font = ("Segoe UI", 10) # Fallback
                self.load_font_memory(path)
                fam = self.get_font_family_from_file(path)
                if fam:
                    preview_font = (fam, 14)
                    
                lbl = ttk.Label(fr, text="Preview: 123 AaBb", font=preview_font)
                lbl.pack(side='right', padx=10)

        # Load Cursors recursively
        if os.path.exists(self.cursors_dir):
            cursor_sets = []
            for root, dirs, files in os.walk(self.cursors_dir):
                if any(f.lower().endswith('.png') for f in files):
                    if root == self.cursors_dir: continue
                    rel = os.path.relpath(root, self.cursors_dir)
                    cursor_sets.append(rel.replace("\\", "/"))

            for d in sorted(cursor_sets):
                fr = ttk.Frame(self.c_sf); fr.pack(fill='x', pady=2, padx=5)
                
                if d not in self.cursor_vars:
                    self.cursor_vars[d] = tk.BooleanVar(value=True)
                    
                ttk.Checkbutton(fr, text=f"Set: {d}", variable=self.cursor_vars[d]).pack(side='left', padx=5)
                ttk.Label(fr, text="(Contains cursor PNGs)").pack(side='right', padx=5)

    def finish_setup(self):
        # 1. Cleanup Fonts
        removed_count = 0
        for rel, var in self.font_vars.items():
            if not var.get():
                path = os.path.join(self.fonts_dir, rel)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        removed_count += 1
                    except: pass
        
        # 2. Cleanup Cursors
        for rel, var in self.cursor_vars.items():
            if not var.get():
                path = os.path.join(self.cursors_dir, rel)
                if os.path.exists(path):
                    try:
                        shutil.rmtree(path)
                        removed_count += 1
                    except: pass
        
        # 3. Cleanup empty folders in Fonts dir
        for root, dirs, files in os.walk(self.fonts_dir, topdown=False):
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except: pass
                
        if removed_count > 0:
            messagebox.showinfo("Cleanup", f"Removed {removed_count} unselected items.")
            
        self.win.destroy()

    def add_custom_font(self):
        p = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf *.otf")])
        if p:
            try:
                os.makedirs(self.fonts_dir, exist_ok=True)
                shutil.copy2(p, os.path.join(self.fonts_dir, os.path.basename(p)))
                self._load_items()
                messagebox.showinfo("Success", f"Font '{os.path.basename(p)}' added!")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def add_custom_cursor_set(self):
        d = filedialog.askdirectory(title="Select Folder containing ArrowCursor.png, etc.")
        if d:
            try:
                name = os.path.basename(d)
                dst = os.path.join(self.cursors_dir, name)
                os.makedirs(dst, exist_ok=True)
                for f in os.listdir(d):
                    if f.lower().endswith(".png"):
                        shutil.copy2(os.path.join(d, f), dst)
                self._load_items()
                messagebox.showinfo("Success", f"Cursor set '{name}' imported!")
            except Exception as e:
                messagebox.showerror("Error", str(e))

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Font Manager Installer")
        self.root.geometry("500x380")
        self.install_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'RobloxFontManager')
        self._setup_ui()

    def _setup_ui(self):
        f = ttk.Frame(self.root, padding=30)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="Roblox Font Manager", font=("Segoe UI", 22, "bold")).pack(pady=10)
        self.sl = ttk.Label(f, text="System Ready for Installation")
        self.sl.pack(pady=5)
        self.pb = ttk.Progressbar(f, length=350, mode='determinate')
        self.pb.pack(pady=20)
        self.ib = ttk.Button(f, text="Install Now", command=self.run_install)
        self.ib.pack(pady=10, ipady=10)

    def run_install(self):
        self.ib.config(state='disabled')
        try:
            # 0. Kill existing instances to prevent conflicts/locks
            subprocess.call('taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq Roblox Font & Cursor Manager" >nul 2>&1', shell=True)
            
            out = subprocess.check_output('where python', shell=True, text=True)
            py = out.strip().split('\n')[0].strip()
            pyw = py.replace('python.exe', 'pythonw.exe')
            
            os.makedirs(self.install_dir, exist_ok=True)
            os.makedirs(os.path.join(self.install_dir, "Fonts"), exist_ok=True)
            os.makedirs(os.path.join(self.install_dir, "Cursors"), exist_ok=True)
            
            self.pb['value'] = 20
            self.sl.config(text="Extracting local assets...")
            bd = os.path.dirname(os.path.abspath(__file__))
            
            # 1. Handle Fonts: Flatten extraction + Nested Zip Support
            zp_fonts = os.path.join(bd, "Fonts.zip")
            if os.path.exists(zp_fonts):
                fonts_dest = os.path.join(self.install_dir, "Fonts")
                with zipfile.ZipFile(zp_fonts, 'r') as z:
                    for member in z.infolist():
                        # Check for direct font files
                        if not member.is_dir() and member.filename.lower().endswith(('.ttf', '.otf')):
                            source = z.open(member)
                            target_file = os.path.join(fonts_dest, os.path.basename(member.filename))
                            with open(target_file, "wb") as dest:
                                shutil.copyfileobj(source, dest)
                            source.close()
                        
                        # Check for nested zip files (e.g. Fonts/Font1.zip)
                        elif not member.is_dir() and member.filename.lower().endswith('.zip'):
                            # Extract the nested zip to a temp file
                            temp_zip_path = os.path.join(self.install_dir, f"temp_{os.path.basename(member.filename)}")
                            with open(temp_zip_path, "wb") as f:
                                shutil.copyfileobj(z.open(member), f)
                            
                            # Open the nested zip and extract fonts from it
                            try:
                                with zipfile.ZipFile(temp_zip_path, 'r') as nested_z:
                                    for nested_member in nested_z.infolist():
                                        if not nested_member.is_dir() and nested_member.filename.lower().endswith(('.ttf', '.otf')):
                                            source = nested_z.open(nested_member)
                                            target_file = os.path.join(fonts_dest, os.path.basename(nested_member.filename))
                                            with open(target_file, "wb") as dest:
                                                shutil.copyfileobj(source, dest)
                                            source.close()
                            except zipfile.BadZipFile:
                                pass
                            finally:
                                if os.path.exists(temp_zip_path):
                                    try: os.remove(temp_zip_path)
                                    except: pass

            # 2. Handle Cursors: Standard extract (Preserve folder structure for sets)
            zp_cursors = os.path.join(bd, "Cursors.zip")
            if os.path.exists(zp_cursors):
                cursors_dest = os.path.join(self.install_dir, "Cursors")
                with zipfile.ZipFile(zp_cursors, 'r') as z:
                    z.extractall(cursors_dest)

            self.pb['value'] = 40
            self.sl.config(text="Installing dependencies...")
            subprocess.check_call([py, "-m", "pip", "install", "psutil"], creationflags=subprocess.CREATE_NO_WINDOW)

            self.pb['value'] = 60
            self.sl.config(text="Deploying system files...")
            with open(os.path.join(self.install_dir, 'auto_font_manager.py'), 'w', encoding='utf-8') as f: f.write(AUTO_MANAGER_CODE)
            with open(os.path.join(self.install_dir, 'manager.py'), 'w', encoding='utf-8') as f: f.write(MANAGER_HUB_CODE)
            
            self.pb['value'] = 80
            self.create_shortcut(pyw, os.path.join(self.install_dir, 'manager.py'))

            vbs = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup', 'launch_roblox_font_manager.vbs')
            with open(vbs, 'w') as f:
                f.write(f'Set oWS = CreateObject("WScript.Shell")\n')
                f.write(f'oWS.Run """{pyw}"" ""{os.path.join(self.install_dir, "auto_font_manager.py")}""", 0, false')

            self.pb['value'] = 100
            messagebox.showinfo("Success", "Installation complete! Library items from local zip files have been extracted.")
            self.root.destroy()
            
            # Run the library setup window
            nr = tk.Tk(); nr.withdraw(); FontChooserApp(nr, self.install_dir); nr.mainloop()
            
            # CRITICAL FIX: Launch the background manager immediately after setup closes
            if os.path.exists(vbs):
                subprocess.Popen(f'cscript //Nologo "{vbs}"', shell=True, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
            
        except Exception as e:
            self.ib.config(state='normal')
            messagebox.showerror("Installation Failed", str(e))

    def create_shortcut(self, pyw, script):
        target = os.path.join(os.path.expanduser("~"), "Desktop", "Roblox Font Manager Hub.lnk")
        vbs = os.path.join(os.getenv('TEMP'), 'create_lnk.vbs')
        with open(vbs, 'w') as f:
            f.write(f'Set oWS = WScript.CreateObject("WScript.Shell")\nsLinkFile = "{target}"\n')
            f.write(f'Set oLink = oWS.CreateShortcut(sLinkFile)\noLink.TargetPath = "{pyw}"\n')
            f.write(f'oLink.Arguments = """{script}"""\noLink.WorkingDirectory = "{self.install_dir}"\noLink.Save')
        subprocess.call(['cscript', vbs], creationflags=subprocess.CREATE_NO_WINDOW)

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()
