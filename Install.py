import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.font import Font
import ctypes
import traceback
import zipfile
import tempfile
import time

# --- EMBEDDED SCRIPTS ---
# The code for the other python files is stored here as strings
# to be written to files during installation.

AUTO_MANAGER_CODE = r'''
import os
import shutil
import sys
import time
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, Toplevel, Button, Label

# User requested token for scripts
# mvy9amhku0l3b2kq0cemzduy6czqm8

# --- Dependency Check ---
try:
    import psutil
except ImportError:
    sys.exit("Error: psutil library not found.")

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
SOURCE_FOLDER_NAME = "PLACE YOUR CUSTOM FONT HERE"
SOURCE_FOLDER_PATH = os.path.join(SCRIPT_DIR, SOURCE_FOLDER_NAME)
LOG_FILE_PATH = os.path.join(SCRIPT_DIR, "font_manager.log")
ROBLOX_VERSIONS_PATH = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Roblox', 'Versions')
CHECK_INTERVAL_SECONDS = 15

# --- Global State ---
pending_updates = set()
session_ignored_versions = set() # Prevents asking for the same version repeatedly in one session

# --- Logging Setup ---
def log(message):
    """Appends a timestamped message to the log file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}\n"
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(log_message)
    print(log_message.strip())

# --- GUI Dialog ---
def ask_update_preference(version_name):
    """Shows a custom dialog box asking the user what to do."""
    root = tk.Tk()
    root.title("Roblox Update Detected")
    
    window_height = 150
    window_width = 440
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_cordinate = int((screen_width/2) - (window_width/2))
    y_cordinate = int((screen_height/2) - (window_height/2))
    root.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

    root.resizable(False, False)
    root.attributes("-topmost", True)

    result = {"choice": "cancel"}

    def on_choice(choice):
        result["choice"] = choice
        root.destroy()

    Label(root, text=f"Roblox update detected for version:\n{version_name[:25]}...", font=("Segoe UI", 12)).pack(pady=10)
    Label(root, text="Apply custom font now, or wait until after you close Roblox?", wraplength=420).pack(pady=5)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=15)

    Button(button_frame, text="Update Now", width=12, command=lambda: on_choice("now")).pack(side="left", padx=5)
    Button(button_frame, text="Update Later", width=12, command=lambda: on_choice("later")).pack(side="left", padx=5)
    Button(button_frame, text="Skip This Version", width=15, command=lambda: on_choice("cancel")).pack(side="left", padx=5)

    root.protocol("WM_DELETE_WINDOW", lambda: on_choice("cancel"))
    root.mainloop()

    return result["choice"]

# --- Core Functions ---
def get_source_font():
    if not os.path.isdir(SOURCE_FOLDER_PATH):
        try:
            os.makedirs(SOURCE_FOLDER_PATH)
            log(f"Source folder created at: {SOURCE_FOLDER_PATH}")
        except OSError: return None
    
    try:
        files = [f for f in os.listdir(SOURCE_FOLDER_PATH) if os.path.isfile(os.path.join(SOURCE_FOLDER_PATH, f))]
        if len(files) == 1: return os.path.join(SOURCE_FOLDER_PATH, files[0])
    except Exception as e: log(f"ERROR: Could not access source folder: {e}")
    return None

def get_roblox_versions():
    if not os.path.isdir(ROBLOX_VERSIONS_PATH): return set()
    return {d for d in os.listdir(ROBLOX_VERSIONS_PATH) if os.path.isdir(os.path.join(ROBLOX_VERSIONS_PATH, d))}

def restart_roblox(new_version_folder_path):
    log("Attempting to restart Roblox...")
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == "RobloxPlayerBeta.exe":
            try:
                psutil.Process(proc.info['pid']).terminate()
                log(f"Closed Roblox process (PID: {proc.info['pid']}).")
            except psutil.NoSuchProcess: pass
    
    time.sleep(3)
    roblox_exe_path = os.path.join(new_version_folder_path, "RobloxPlayerBeta.exe")
    if os.path.exists(roblox_exe_path):
        try:
            subprocess.Popen([roblox_exe_path])
            log("Relaunching Roblox from the new version folder.")
        except Exception as e: log(f"Failed to relaunch Roblox: {e}")
    else: log(f"Error: RobloxPlayerBeta.exe not found in '{new_version_folder_path}'")

def replace_fonts(target_fonts_folder, source_font):
    log(f"--- Starting replacement for '{os.path.basename(os.path.dirname(os.path.dirname(target_fonts_folder)))}' ---")
    try:
        backup_folder_path = os.path.join(target_fonts_folder, "Fonts.old", datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        os.makedirs(backup_folder_path, exist_ok=True)
        
        font_ext = ('.ttf', '.otf')
        
        original_fonts = [f for f in os.listdir(target_fonts_folder) if os.path.isfile(os.path.join(target_fonts_folder, f)) and f.lower().endswith(font_ext)]
        
        if not original_fonts:
            log("No font files found in the target directory to replace.")
            return True

        for filename in original_fonts:
            shutil.move(os.path.join(target_fonts_folder, filename), os.path.join(backup_folder_path, filename))
        log(f"Backed up {len(original_fonts)} original font file(s).")

        replaced_count = 0
        for filename in original_fonts:
            original_backup_path = os.path.join(backup_folder_path, filename)
            new_file_path = os.path.join(target_fonts_folder, filename)

            if filename.lower().startswith('twemoji'):
                shutil.copy2(original_backup_path, new_file_path)
                log(f"Restored original emoji font: {filename}")
            else:
                shutil.copy2(source_font, new_file_path)
                replaced_count += 1
        
        log(f"Successfully replaced {replaced_count} file(s).")
        return True
    except Exception as e:
        log(f"CRITICAL: Replacement failed. Error: {e}")
        return False

# --- Main Monitoring Loop ---
def main():
    log("--- Automatic Font Manager Started ---")
    log("Monitoring for Roblox process and new versions...")
    
    is_roblox_running_previously = False

    while True:
        try:
            is_roblox_running_now = any(p.name() == "RobloxPlayerBeta.exe" for p in psutil.process_iter(['name']))

            if is_roblox_running_now:
                if not is_roblox_running_previously:
                    log("RobloxPlayerBeta.exe detected. Actively monitoring for updates.")
                is_roblox_running_previously = True

                updatable_versions = []
                current_versions = get_roblox_versions()

                for version in current_versions:
                    if version in session_ignored_versions:
                        continue 

                    fonts_folder = os.path.join(ROBLOX_VERSIONS_PATH, version, 'content', 'fonts')
                    backup_folder = os.path.join(fonts_folder, 'Fonts.old')

                    if os.path.isdir(fonts_folder) and not os.path.isdir(backup_folder):
                        updatable_versions.append(version)
                
                if updatable_versions:
                    log(f"Detected {len(updatable_versions)} version(s) needing font update.")
                    source_font = get_source_font()

                    if not source_font:
                        log("Found updatable version(s), but no source font is ready. Skipping.")
                        for v in updatable_versions: session_ignored_versions.add(v)
                    else:
                        log(f"Source font is ready: {os.path.basename(source_font)}")
                        
                        latest_version_to_update = sorted(updatable_versions, reverse=True)[0]
                        
                        user_choice = ask_update_preference(latest_version_to_update)
                        log(f"User selected: '{user_choice.upper()}' for version '{latest_version_to_update}'")
                        
                        target_fonts_folder = os.path.join(ROBLOX_VERSIONS_PATH, latest_version_to_update, 'content', 'fonts')
                        
                        if user_choice == "now":
                            if replace_fonts(target_fonts_folder, source_font):
                                version_folder = os.path.dirname(os.path.dirname(target_fonts_folder))
                                restart_roblox(version_folder)
                            session_ignored_versions.add(latest_version_to_update)
                        
                        elif user_choice == "later":
                            pending_updates.add(latest_version_to_update)
                            session_ignored_versions.add(latest_version_to_update)
                            log(f"'{latest_version_to_update}' added to the queue for later.")
                        
                        elif user_choice == "cancel":
                            session_ignored_versions.add(latest_version_to_update)

            else: # Roblox not running
                if is_roblox_running_previously:
                    log("Roblox process no longer running. Checking for pending updates...")
                    if pending_updates:
                        source_font = get_source_font()
                        if not source_font:
                             log("Cannot process pending updates: no source font is ready.")
                        else:
                            log(f"Processing {len(pending_updates)} pending update(s).")
                            for version in list(pending_updates):
                                target_fonts_folder = os.path.join(ROBLOX_VERSIONS_PATH, version, 'content', 'fonts')
                                if os.path.isdir(target_fonts_folder):
                                    replace_fonts(target_fonts_folder, source_font)
                                pending_updates.remove(version)
                            log("All pending updates completed.")
                is_roblox_running_previously = False
            
            time.sleep(CHECK_INTERVAL_SECONDS)
        except Exception as e:
            log(f"An unexpected error occurred in the main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
'''

MANAGER_HUB_CODE = r'''
import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
import subprocess

# User requested token for scripts
# mvy9amhku0l3b2kq0cemzduy6czqm8

# --- UNINSTALLER LOGIC ---
def run_uninstall(parent_window):
    """Contains all logic for uninstalling the application."""
    try:
        import psutil
    except ImportError:
        psutil = None

    def remove_startup_file():
        startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        vbs_path = os.path.join(startup_folder, 'launch_roblox_font_manager.vbs')
        try:
            if os.path.exists(vbs_path):
                os.remove(vbs_path)
        except Exception:
            pass # Fail silently

    def terminate_running_script():
        if not psutil: return
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                if proc.info['cmdline'] and 'auto_font_manager' in ' '.join(proc.info['cmdline']):
                    psutil.Process(proc.info['pid']).terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    install_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    if not messagebox.askyesno("Confirm Uninstall", f"Are you sure you want to uninstall from:\n\n{install_dir}?", parent=parent_window):
        return

    try:
        terminate_running_script()
        remove_startup_file()
        
        # Self-deletion logic using a batch file
        deleter_bat_path = os.path.join(os.getenv('TEMP'), 'rfm_deleter.bat')
        with open(deleter_bat_path, 'w', encoding='utf-8') as f:
            f.write(f'@echo off\n')
            f.write(f'echo Uninstalling Roblox Font Manager...\n')
            f.write(f'ping 127.0.0.1 -n 4 > nul\n') # Wait for this script to close
            f.write(f'rd /s /q "{install_dir}"\n')
            f.write(f'echo Uninstallation complete.\n')
            f.write(f'ping 127.0.0.1 -n 2 > nul\n')
            f.write(f'del "%~f0"\n') # Delete the batch file itself
        
        subprocess.Popen(f'"{deleter_bat_path}"', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        parent_window.destroy()
        sys.exit()

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during uninstallation:\n{e}", parent=parent_window)

# --- MANUAL FONT MANAGER APP ---
class FontManagerApp:
    def __init__(self, parent_window):
        self.win = tk.Toplevel(parent_window)
        self.win.title("Font Manager (Manual)")
        self.win.geometry("600x500")
        self.win.resizable(False, True)

        self.source_file_path_var = tk.StringVar()
        self.target_folder_path_var = tk.StringVar()
        self.selected_backup_var = tk.StringVar()
        
        self.source_folder_name = "PLACE YOUR CUSTOM FONT HERE"
        self.script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        
        self.source_folder_path = os.path.join(self.script_dir, self.source_folder_name)
        self.history_filename = "font_manager_history.txt"
        self.history_filepath = os.path.join(self.script_dir, self.history_filename)
        
        self.last_source_status = None
        self.current_source_file = None
        self.directory_history = self._load_history()

        self._setup_gui()
        
        self.monitor_source_folder()
        self.show_frame(self.main_menu_frame)
        self.win.transient(parent_window)
        self.win.grab_set()

    def _setup_gui(self):
        container = ttk.Frame(self.win, padding=15)
        container.pack(fill=tk.BOTH, expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.main_menu_frame = ttk.Frame(container)
        self.replace_frame = ttk.Frame(container)
        self.undo_frame = ttk.Frame(container)

        for frame in (self.main_menu_frame, self.replace_frame, self.undo_frame):
            frame.grid(row=0, column=0, sticky='nsew')

        self._create_main_menu_frame()
        self._create_replace_frame()
        self._create_undo_frame()

        log_frame = ttk.LabelFrame(self.win, text="Log", padding=(10, 5))
        log_frame.pack(side="bottom", fill="x", expand=False, padx=15, pady=(0, 15))
        self.log_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state='disabled', height=8)
        self.log_widget.pack(fill="x", expand=True)

    def show_frame(self, frame_to_show):
        frame_to_show.tkraise()

    def _create_main_menu_frame(self):
        frame = self.main_menu_frame
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="Manual Tools", font=("Helvetica", 14)).pack(pady=20)
        
        replace_btn = ttk.Button(frame, text="Replace Fonts", command=lambda: self.show_frame(self.replace_frame))
        replace_btn.pack(fill='x', ipady=10, pady=5, padx=50)

        undo_btn = ttk.Button(frame, text="Undo / Restore from Backup", command=lambda: self.show_frame(self.undo_frame))
        undo_btn.pack(fill='x', ipady=10, pady=5, padx=50)

        ttk.Button(frame, text="Close", command=self.win.destroy).pack(pady=10)

    def _create_replace_frame(self):
        frame = self.replace_frame
        ttk.Label(frame, text="Replace Fonts", font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
        
        source_frame = ttk.LabelFrame(frame, text="1. Source Font File (Live Status)", padding=10)
        source_frame.pack(fill='x', pady=5)
        ttk.Entry(source_frame, textvariable=self.source_file_path_var, state='readonly').pack(fill='x')

        target_frame = ttk.LabelFrame(frame, text="2. Select Target Folder", padding=10)
        target_frame.pack(fill='x', pady=5)
        target_entry = ttk.Entry(target_frame, textvariable=self.target_folder_path_var, state='readonly')
        target_entry.pack(side='left', fill='x', expand=True)
        ttk.Button(target_frame, text="Browse...", command=self.select_target_folder).pack(side='right', padx=(5,0))

        ttk.Button(frame, text="Perform Replacement", command=self.run_replacement_process).pack(fill='x', ipady=8, pady=10)
        ttk.Button(frame, text="« Back to Menu", command=lambda: self.show_frame(self.main_menu_frame)).pack(fill='x', ipady=2)

    def _create_undo_frame(self):
        frame = self.undo_frame
        ttk.Label(frame, text="Undo / Restore", font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
        
        target_frame = ttk.LabelFrame(frame, text="1. Select Target Folder", padding=10)
        target_frame.pack(fill='x', pady=5)
        
        self.history_combobox = ttk.Combobox(target_frame, textvariable=self.target_folder_path_var, values=self.directory_history)
        self.history_combobox.pack(side='left', fill='x', expand=True)
        self.history_combobox.bind("<<ComboboxSelected>>", self._on_history_select)
        
        ttk.Button(target_frame, text="Browse...", command=self.select_target_folder).pack(side='right', padx=(5,0))

        backup_frame = ttk.LabelFrame(frame, text="2. Choose Backup to Restore", padding=10)
        backup_frame.pack(fill='x', pady=5)
        self.backup_menu = ttk.OptionMenu(backup_frame, self.selected_backup_var, "No Target Selected")
        self.backup_menu.pack(fill='x')
        self.backup_menu.config(state='disabled')

        self.undo_button = ttk.Button(frame, text="Restore This Backup", command=self.run_undo_process)
        self.undo_button.pack(fill='x', ipady=8, pady=10)
        self.undo_button.config(state='disabled')
        ttk.Button(frame, text="« Back to Menu", command=lambda: self.show_frame(self.main_menu_frame)).pack(fill='x', ipady=2)

    def _load_history(self):
        if not os.path.exists(self.history_filepath): return []
        try:
            with open(self.history_filepath, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.log(f"Warning: Could not load history file. {e}")
            return []
    
    def _save_to_history(self, directory_path):
        if directory_path not in self.directory_history:
            self.directory_history.insert(0, directory_path)
            try:
                with open(self.history_filepath, 'w', encoding='utf-8') as f: f.write("\n".join(self.directory_history))
                self.history_combobox['values'] = self.directory_history
            except Exception as e: self.log(f"Warning: Could not save to history file. {e}")
    
    def _on_history_select(self, event):
        self.scan_for_backups()
    
    def log(self, message):
        self.log_widget.config(state='normal')
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.see(tk.END)
        self.log_widget.config(state='disabled')
        self.win.update_idletasks()

    def monitor_source_folder(self):
        if not os.path.isdir(self.source_folder_path):
            try:
                os.makedirs(self.source_folder_path)
                self.log(f"Source folder created at: {self.source_folder_path}")
            except Exception: pass
        try:
            source_files = [f for f in os.listdir(self.source_folder_path) if os.path.isfile(os.path.join(self.source_folder_path, f))]
        except Exception:
            self.source_file_path_var.set("CRITICAL: Cannot access source folder.")
            return

        status, msg = "", ""
        if len(source_files) == 0: status, self.current_source_file, msg = "waiting", None, "Waiting for a font file..."
        elif len(source_files) > 1: status, self.current_source_file, msg = "multiple_files", None, "ERROR: Too many files found."
        else:
            self.current_source_file = os.path.join(self.source_folder_path, source_files[0])
            status, msg = f"ok:{self.current_source_file}", self.current_source_file
        
        self.source_file_path_var.set(os.path.basename(msg))

        if status != self.last_source_status:
            if status == "waiting": self.log("Source folder is empty. Waiting...")
            elif status == "multiple_files": self.log("ERROR: Multiple files detected in source folder.")
            elif status.startswith("ok:"): self.log(f"Source font detected: {os.path.basename(self.current_source_file)}")
            self.last_source_status = status
        
        if self.win.winfo_exists():
            self.win.after(5000, self.monitor_source_folder)
    
    def select_target_folder(self):
        folder_selected = filedialog.askdirectory(title="Select the folder", parent=self.win)
        if folder_selected:
            if os.path.basename(folder_selected) == "Fonts.old":
                self.log("💡 'Fonts.old' was selected. Auto-correcting to the parent folder.")
                folder_selected = os.path.dirname(folder_selected)
            self.target_folder_path_var.set(folder_selected)
            self.log(f"Target folder set to: {folder_selected}")
            self.scan_for_backups()
    
    def scan_for_backups(self):
        self.backup_menu.config(state='disabled')
        self.undo_button.config(state='disabled')
        self.selected_backup_var.set("No backups found")
        
        base_backup_dir = os.path.join(self.target_folder_path_var.get(), "Fonts.old")
        if os.path.isdir(base_backup_dir):
            try:
                backups = sorted([d for d in os.listdir(base_backup_dir) if os.path.isdir(os.path.join(base_backup_dir, d))], reverse=True)
                if backups:
                    menu = self.backup_menu["menu"]
                    menu.delete(0, "end")
                    for backup in backups:
                        menu.add_command(label=backup, command=lambda v=backup: self.selected_backup_var.set(v))
                    self.selected_backup_var.set(backups[0])
                    self.backup_menu.config(state='normal')
                    self.undo_button.config(state='normal')
                    self.log(f"Found {len(backups)} backup session(s).")
                    return
            except Exception as e: self.log(f"Error scanning backups: {e}")
        self.log("No valid backups found in 'Fonts.old' folder.")

    def run_replacement_process(self):
        if not self.current_source_file: messagebox.showerror("Error", "Source font is not ready.", parent=self.win); return
        target_folder = self.target_folder_path_var.get()
        if not target_folder or not os.path.isdir(target_folder): messagebox.showerror("Error", "Please select a valid target folder first.", parent=self.win); return
        if not messagebox.askyesno("Confirmation", f"This will replace all fonts in:\n'{target_folder}'\n\nwith:\n'{os.path.basename(self.current_source_file)}'\n\nA new backup will be created. Proceed?", parent=self.win): self.log("Replacement cancelled."); return
        
        self.log("\n--- Starting manual replacement ---")
        try:
            backup_folder_path = os.path.join(target_folder, "Fonts.old", datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
            os.makedirs(backup_folder_path, exist_ok=True)
            self.log(f"Creating backup: {os.path.basename(backup_folder_path)}")
            
            font_ext = ('.ttf', '.otf')
            replaced_count = 0
            for filename in os.listdir(target_folder):
                file_path = os.path.join(target_folder, filename)
                if os.path.isfile(file_path) and filename.lower().endswith(font_ext):
                    if not filename.lower().startswith('twemoji'):
                        shutil.move(file_path, os.path.join(backup_folder_path, filename))
                        shutil.copy2(self.current_source_file, file_path)
                        replaced_count += 1
            
            self.log(f"Successfully replaced {replaced_count} file(s).")
            messagebox.showinfo("Success", f"Process finished! Replaced {replaced_count} file(s).", parent=self.win)
            self._save_to_history(target_folder)
            self.scan_for_backups()
        except Exception as e: messagebox.showerror("Error", f"Replacement failed: {e}", parent=self.win); self.log(f"ERROR: {e}")

    def run_undo_process(self):
        target_folder, selected_backup = self.target_folder_path_var.get(), self.selected_backup_var.get()
        if not target_folder or selected_backup in ["No Target Selected", "No backups found"]: messagebox.showerror("Error", "Select a valid target and backup session.", parent=self.win); return
        backup_path = os.path.join(target_folder, "Fonts.old", selected_backup)
        if not os.path.isdir(backup_path): messagebox.showerror("Error", f"Backup folder not found:\n{backup_path}", parent=self.win); return
        if not messagebox.askyesno("Confirmation", f"This will restore all files from:\n'{selected_backup}'\n\nThis will overwrite current fonts in the target folder. Proceed?", parent=self.win): self.log("Undo cancelled."); return
        
        self.log(f"\n--- Starting Undo from '{selected_backup}' ---")
        try:
            files_to_restore = [f for f in os.listdir(backup_path) if os.path.isfile(os.path.join(backup_path, f))]
            if not files_to_restore: messagebox.showinfo("Information", "Backup folder is empty.", parent=self.win); self.log("Backup is empty."); return
            
            for filename in files_to_restore: shutil.move(os.path.join(backup_path, filename), os.path.join(target_folder, filename))
            self.log(f"Restored {len(files_to_restore)} file(s).")
            messagebox.showinfo("Success", f"Successfully restored {len(files_to_restore)} file(s).", parent=self.win)
            
            if messagebox.askyesno("Cleanup", f"Remove the now-empty backup folder '{selected_backup}'?", parent=self.win):
                os.rmdir(backup_path); self.log(f"Removed empty backup: {selected_backup}")
            self.scan_for_backups()
        except Exception as e: messagebox.showerror("Error", f"Undo failed: {e}", parent=self.win); self.log(f"ERROR: {e}")

# --- MAIN HUB APPLICATION ---
class ManagerHubApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Font Manager")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Management Hub", font=("Segoe UI", 16, "bold")).pack(pady=10)

        ttk.Button(frame, text="Manual Font Tools", command=self.open_manual_tool).pack(fill='x', ipady=8, pady=5)
        ttk.Button(frame, text="Uninstall", command=lambda: run_uninstall(self.root)).pack(fill='x', ipady=8, pady=5)

    def open_manual_tool(self):
        self.root.withdraw()
        app = FontManagerApp(self.root)
        app.win.wait_window()
        self.root.deiconify()

if __name__ == "__main__":
    root = tk.Tk()
    app = ManagerHubApp(root)
    root.mainloop()
'''

# --- INSTALLER APP ---

class FontChooserApp:
    def __init__(self, parent, install_dir):
        self.win = tk.Toplevel(parent)
        self.win.title("Step 2: Choose Your Font")
        self.win.geometry("600x650")
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self.install_dir = install_dir
        self.fonts_dir = os.path.join(install_dir, "Fonts")
        self.target_dir = os.path.join(install_dir, "PLACE YOUR CUSTOM FONT HERE")
        self.loaded_fonts = []

        self._setup_ui()
        self.win.after(100, self._load_and_display_fonts) # Load after window is shown

    def _setup_ui(self):
        header_frame = ttk.Frame(self.win, padding=10)
        header_frame.pack(fill='x')
        ttk.Label(header_frame, text="Select a Font", font=("Segoe UI", 16, "bold")).pack()
        info_text = "Preset fonts are listed below. To add more, place them in the 'Fonts' folder\n" \
                    "inside the installation directory, then click 'Refresh List'."
        ttk.Label(header_frame, text=info_text, wraplength=580, justify='center').pack(pady=5)
        
        ttk.Separator(self.win, orient='horizontal').pack(fill='x', padx=10, pady=5)

        main_frame = ttk.Frame(self.win)
        main_frame.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, padding=10)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        footer_frame = ttk.Frame(self.win, padding=10)
        footer_frame.pack(fill='x', side='bottom')

        self.status_label = ttk.Label(footer_frame, text="Ready.")
        self.status_label.pack(side='left', anchor='w')

        button_container = ttk.Frame(footer_frame)
        button_container.pack(side='right')
        ttk.Button(button_container, text="I have my own font...", command=self.select_custom_font).pack(side='left')
        ttk.Button(button_container, text="Refresh List", command=self._load_and_display_fonts).pack(side='left', padx=10)
        ttk.Button(button_container, text="Finish", command=self._on_close).pack(side='right')

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _load_and_display_fonts(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self._unload_fonts()

        if not os.path.exists(self.fonts_dir):
            os.makedirs(self.fonts_dir)

        font_files = [f for f in os.listdir(self.fonts_dir) if f.lower().endswith(('.ttf', '.otf'))]
        total_fonts = len(font_files)

        if not font_files:
            ttk.Label(self.scrollable_frame, text="No fonts found. Add .ttf or .otf files to the 'Fonts' folder.", font=("Segoe UI", 12, "italic")).pack(pady=20)
            self.status_label.config(text="No fonts found.")
            return

        gdi32 = ctypes.WinDLL('gdi32')
        add_font_resource = gdi32.AddFontResourceW
        
        for i, font_file in enumerate(sorted(font_files)):
            self.status_label.config(text=f"Loading {i+1}/{total_fonts}: {font_file}")
            self.win.update_idletasks() # Force UI update

            font_path = os.path.join(self.fonts_dir, font_file)
            font_name_no_ext = os.path.splitext(font_file)[0]

            if add_font_resource(font_path):
                self.loaded_fonts.append(font_path)
            
            font_frame = ttk.Frame(self.scrollable_frame, padding=(0, 10))
            font_frame.pack(fill='x', pady=5)
            
            try:
                ttk.Label(font_frame, text=font_name_no_ext, font=("Segoe UI", 11, "bold")).pack(anchor='w')
                preview_font = Font(family=font_name_no_ext, size=14)
                ttk.Label(font_frame, text="AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz", font=preview_font, wraplength=450).pack(anchor='w', pady=2)
                ttk.Button(font_frame, text="Select", command=lambda p=font_path: self.set_font(p)).pack(anchor='e', pady=5)
            except tk.TclError:
                ttk.Label(font_frame, text=f"Could not preview: {font_name_no_ext}", font=("Segoe UI", 10, "italic")).pack(anchor='w')
            
            if i < total_fonts - 1:
                ttk.Separator(font_frame, orient='horizontal').pack(fill='x', pady=10)
        
        self.status_label.config(text=f"Loaded {total_fonts} fonts.")
    
    def set_font(self, font_path):
        try:
            for item in os.listdir(self.target_dir):
                os.remove(os.path.join(self.target_dir, item))
            
            shutil.copy(font_path, self.target_dir)
            font_name = os.path.basename(font_path)
            messagebox.showinfo("Font Set", f"'{font_name}' has been set as the active custom font.", parent=self.win)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set font: {e}", parent=self.win)

    def select_custom_font(self):
        font_path = filedialog.askopenfilename(
            title="Select a font file",
            filetypes=[("Font Files", "*.ttf *.otf")],
            parent=self.win
        )
        if font_path:
            self.set_font(font_path)

    def _unload_fonts(self):
        gdi32 = ctypes.WinDLL('gdi32')
        remove_font_resource = gdi32.RemoveFontResourceW
        for font_path in self.loaded_fonts:
            try:
                remove_font_resource(font_path)
            except Exception:
                pass # Fail silently if font can't be unloaded
        self.loaded_fonts = []

    def _on_close(self):
        self._unload_fonts()
        self.win.destroy()


class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Font Manager Installer")
        self.root.geometry("500x300")
        self.root.resizable(False, False)

        self.install_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'RobloxFontManager')

        self.main_frame = ttk.Frame(root, padding=20)
        self.main_frame.pack(fill="both", expand=True)

        ttk.Label(self.main_frame, text="Roblox Font Manager", font=("Segoe UI", 20, "bold")).pack(pady=10)
        ttk.Label(self.main_frame, text="This will install the automatic font manager on your computer.", wraplength=460, justify='center').pack(pady=5)
        ttk.Label(self.main_frame, text=f"Install Location: {self.install_dir}", wraplength=480, font=("Segoe UI", 8)).pack(pady=15)
        
        self.install_button = ttk.Button(self.main_frame, text="Install Now", command=self.run_installation)
        self.install_button.pack(pady=20, ipady=10, ipadx=20)

        self.progress_frame = ttk.Frame(root, padding=20)
        ttk.Label(self.progress_frame, text="Installing...", font=("Segoe UI", 16, "bold")).pack(pady=10)
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient='horizontal', length=300, mode='determinate')
        self.progress_bar.pack(pady=10)
        self.status_label = ttk.Label(self.progress_frame, text="Starting...")
        self.status_label.pack(pady=5)

    def find_python_executable(self):
        self.update_status("Finding Python installation...")
        
        common_paths = [
            os.path.join(os.getenv('LOCALAPPDATA'), 'Programs', 'Python'),
            os.path.join(os.getenv('ProgramFiles'), 'Python')
        ]
        
        for path in common_paths:
            if not os.path.isdir(path):
                continue
            for folder in os.listdir(path):
                if folder.lower().startswith('python'):
                    py_exe = os.path.join(path, folder, 'python.exe')
                    if os.path.exists(py_exe):
                        print(f"Found Python at: {py_exe}")
                        return py_exe

        try:
            output = subprocess.check_output('where python', shell=True, text=True, stderr=subprocess.PIPE)
            paths = output.strip().split('\n')
            for path in paths:
                if 'WindowsApps' not in path:
                    py_exe = path.strip()
                    print(f"Found Python in PATH: {py_exe}")
                    return py_exe
        except subprocess.CalledProcessError:
            pass

        self.update_status("Automatic search failed. Please locate python.exe manually.")
        messagebox.showinfo("Python Not Found", "Could not automatically find your Python installation. Please locate your python.exe file in the next window.", parent=self.root)
        
        python_exe_path = filedialog.askopenfilename(
            title="Select python.exe",
            filetypes=[("Python Executable", "python.exe")],
            initialdir=os.getenv('LOCALAPPDATA')
        )
        
        if python_exe_path and os.path.basename(python_exe_path).lower() == 'python.exe':
            print(f"User selected Python at: {python_exe_path}")
            return python_exe_path
        
        return None

    def create_desktop_shortcut(self, pythonw_exe):
        self.update_status("Creating desktop shortcut...")
        script_path = os.path.join(self.install_dir, 'manager.py')
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        shortcut_path = os.path.join(desktop_path, 'Roblox Font Manager.lnk')
        
        vbs_content = f'''
        Set oWS = WScript.CreateObject("WScript.Shell")
        sLinkFile = "{shortcut_path}"
        Set oLink = oWS.CreateShortcut(sLinkFile)
        oLink.TargetPath = "{pythonw_exe}"
        oLink.Arguments = Chr(34) & "{script_path}" & Chr(34)
        oLink.WorkingDirectory = "{self.install_dir}"
        oLink.Save
        '''
        vbs_path = os.path.join(os.getenv('TEMP'), 'create_shortcut.vbs')
        with open(vbs_path, 'w', encoding='utf-8') as f:
            f.write(vbs_content)
        
        subprocess.call(['cscript', vbs_path], creationflags=subprocess.CREATE_NO_WINDOW)
        os.remove(vbs_path)

    def run_installation(self):
        self.main_frame.pack_forget()
        self.progress_frame.pack(fill="both", expand=True)
        self.root.update_idletasks()
        
        try:
            print("--- Starting Roblox Font Manager Installation ---")
            self.progress_bar['value'] = 0

            if getattr(sys, 'frozen', False):
                installer_dir = os.path.dirname(sys.executable)
            else:
                installer_dir = os.path.dirname(os.path.abspath(__file__))

            source_fonts_dir = os.path.join(installer_dir, 'Fonts')
            
            print(f"Installer is running from: {installer_dir}")
            print(f"Checking for preset fonts folder at: {source_fonts_dir}")
            
            has_fonts_folder = os.path.isdir(source_fonts_dir)

            if not has_fonts_folder:
                messagebox.showwarning("No Fonts Found", "A 'Fonts' folder was not found next to the installer.\n\nThe program will be installed, but you will need to add fonts manually later.")
            
            # Step 1: Find Python (10%)
            python_exe = self.find_python_executable()
            if not python_exe: raise Exception("Could not find a valid Python installation. Installation cancelled.")
            pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
            if not os.path.exists(pythonw_exe): raise Exception(f"pythonw.exe not found alongside {python_exe}")
            self.progress_bar['value'] = 10; self.root.update_idletasks(); time.sleep(0.2)

            # Step 2: Create Directories (20%)
            self.update_status("Creating directories...")
            os.makedirs(os.path.join(self.install_dir, "PLACE YOUR CUSTOM FONT HERE"), exist_ok=True)
            destination_fonts_dir = os.path.join(self.install_dir, "Fonts")
            os.makedirs(destination_fonts_dir, exist_ok=True)
            self.progress_bar['value'] = 20; self.root.update_idletasks(); time.sleep(0.2)

            # Step 3: Extract and Copy Preset Fonts (40%)
            self.update_status("Copying preset fonts...")
            
            source_fonts_dir = os.path.join(installer_dir, 'Fonts')
            source_fonts_zip = os.path.join(installer_dir, 'Fonts.zip')

            has_fonts_folder = os.path.isdir(source_fonts_dir)
            has_fonts_zip = os.path.isfile(source_fonts_zip)

            if not has_fonts_folder and not has_fonts_zip:
                 print("-> No 'Fonts' folder or 'Fonts.zip' found. Skipping preset font copy.")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Scenario 1: A 'Fonts' folder exists
                if has_fonts_folder:
                    print("Searching for preset font ZIP files inside 'Fonts' folder...")
                    for item in os.listdir(source_fonts_dir):
                        if item.lower().endswith('.zip'):
                            zip_path = os.path.join(source_fonts_dir, item)
                            self.update_status(f"Extracting {item}...")
                            print(f"-> Found and extracting: {item}")
                            try:
                                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                    zip_ref.extractall(temp_dir)
                            except zipfile.BadZipFile:
                                print(f"   [WARNING] Skipping corrupted zip file: {item}")
                                continue
                
                # Scenario 2: Only a 'Fonts.zip' file exists
                elif has_fonts_zip:
                    self.update_status(f"Extracting Fonts.zip...")
                    print(f"-> Found and extracting: Fonts.zip")
                    try:
                        with zipfile.ZipFile(source_fonts_zip, 'r') as zip_ref:
                            zip_ref.extractall(temp_dir)
                    except zipfile.BadZipFile:
                        print(f"   [WARNING] Skipping corrupted zip file: Fonts.zip")

                def copy_fonts_from_dir(source_dir, dest_dir):
                    copied_count = 0
                    for root, _, files in os.walk(source_dir):
                        for file in files:
                            if file.lower().endswith(('.ttf', '.otf')):
                                try:
                                    shutil.copy(os.path.join(root, file), dest_dir)
                                    copied_count += 1
                                except shutil.SameFileError:
                                    pass
                    return copied_count
                
                # Copy everything from the temp directory where zips were extracted
                print("Copying fonts from temporary extraction directory...")
                count_from_zip = copy_fonts_from_dir(temp_dir, destination_fonts_dir)
                print(f"-> Copied {count_from_zip} fonts from ZIP archives.")
                
                # If a folder exists, also copy any loose fonts from it
                if has_fonts_folder:
                    print("Copying loose fonts from 'Fonts' folder...")
                    count_from_folder = 0
                    for item in os.listdir(source_fonts_dir):
                        if item.lower().endswith(('.ttf', '.otf')):
                             try:
                                shutil.copy(os.path.join(source_fonts_dir, item), destination_fonts_dir)
                                count_from_folder += 1
                             except shutil.SameFileError:
                                 pass
                    print(f"-> Copied {count_from_folder} loose fonts.")

            self.progress_bar['value'] = 40; self.root.update_idletasks(); time.sleep(0.2)
            
            # Step 4: Write Scripts (55%)
            self.update_status("Writing script files...")
            with open(os.path.join(self.install_dir, 'auto_font_manager.py'), 'w', encoding='utf-8') as f: f.write(AUTO_MANAGER_CODE)
            with open(os.path.join(self.install_dir, 'manager.py'), 'w', encoding='utf-8') as f: f.write(MANAGER_HUB_CODE)
            self.progress_bar['value'] = 55; self.root.update_idletasks(); time.sleep(0.2)
            
            # Step 5: Install Dependency (75%)
            self.update_status("Installing required libraries (psutil)...")
            subprocess.check_call([python_exe, "-m", "pip", "install", "psutil"], creationflags=subprocess.CREATE_NO_WINDOW)
            self.progress_bar['value'] = 75; self.root.update_idletasks(); time.sleep(0.2)

            # Step 6: Create Startup VBS (85%)
            self.update_status("Setting up auto-start...")
            vbs_path = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup', 'launch_roblox_font_manager.vbs')
            script_to_run = os.path.join(self.install_dir, 'auto_font_manager.py')
            vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run """{pythonw_exe}"" ""{script_to_run}""", 0, false'
            with open(vbs_path, 'w', encoding='utf-8') as f: f.write(vbs_content)
            self.progress_bar['value'] = 85; self.root.update_idletasks(); time.sleep(0.2)
            
            # Step 7: Create Desktop Shortcut (95%)
            self.create_desktop_shortcut(pythonw_exe)
            self.progress_bar['value'] = 95; self.root.update_idletasks(); time.sleep(0.2)

            # Step 8: Finalize (100%)
            self.update_status("Installation complete!")
            self.progress_bar['value'] = 100
            print("--- Installation Successful ---")
            
            messagebox.showinfo("Success", "Installation successful! The font selector will now open.")
            
            self.root.destroy()
            root = tk.Tk()
            root.withdraw()
            FontChooserApp(root, self.install_dir)
            root.mainloop()

        except Exception as e:
            print(f"\n--- INSTALLATION FAILED ---\n{traceback.format_exc()}")
            messagebox.showerror("Installation Failed", f"An error occurred:\n\n{e}\n\nPlease check the console window for more details.")
            self.progress_frame.pack_forget()
            self.main_frame.pack(fill="both", expand=True)

    def update_status(self, text):
        self.status_label['text'] = text
        print(text)
        self.root.update_idletasks()


def handle_exception(exc_type, exc_value, exc_traceback):
    """A global exception handler to catch crashes."""
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    messagebox.showerror("Critical Error", f"An unexpected error occurred:\n\n{error_msg}")
    if sys.__excepthook__:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


if __name__ == "__main__":
    sys.excepthook = handle_exception
    
    try:
        root = tk.Tk()
        app = InstallerApp(root)
        root.mainloop()
    except Exception:
        handle_exception(*sys.exc_info())

