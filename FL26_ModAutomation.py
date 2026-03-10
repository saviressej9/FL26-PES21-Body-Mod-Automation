import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
import subprocess
import threading
import csv
import re
import shutil

# ── app setup ─────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PACKAGE_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = os.path.join(PACKAGE_DIR, "FL26_ModAutomation.config.json")
PLAYERID_CSV = os.path.join(PACKAGE_DIR, "PlayerIds.csv")

MOD_LABELS = {
    "gripSoxDualColor" : "Grip Sock - Dual Color All Teams",
    "gripSoxLong"      : "Grip Sock - Long",
    "gripSoxShort"     : "Grip Sock - Short",
    "gripSoxBrands"    : "Grip Sock - Brands",
    "sockHoles"        : "Sock - Holes",
    "sockMiddleHigh"   : "Sock - Middle High",
    "sockShortGroup"   : "Sock - Short Group",
    "pantsBaggy"       : "Pants - Baggy",
    "pantsExtraBaggy"  : "Pants - Extra Baggy",
    "pantsShorter"     : "Pants - Shorter",
    "glovesBrands"     : "Gloves - Brands",
}

# ── config helpers ────────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

# ── DB file parser ────────────────────────────────────────────────────────────

def parse_db_file(path):
    ext = os.path.splitext(path)[1].lower()
    ids = []
    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r'^\s*(\d+)\s*[-–]', line)
                if m:
                    ids.append(m.group(1))
                else:
                    m2 = re.match(r'^\s*(\d+)\s*$', line.strip())
                    if m2:
                        ids.append(m2.group(1))
    elif ext == ".csv":
        for delim in [';', ',']:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f, delimiter=delim)
                    rows = list(reader)
                    if not rows:
                        continue
                    col = None
                    for c in ['Id','ID','PlayerId','PlayerID']:
                        if c in rows[0]:
                            col = c
                            break
                    if col:
                        ids = [r[col].strip() for r in rows if r[col].strip().isdigit()]
                        break
            except Exception:
                continue
    seen = set(); out = []
    for i in ids:
        if i not in seen:
            seen.add(i); out.append(i)
    return out

def parse_db_file_with_names(path):
    """Returns (ids_list, id_to_name_dict)"""
    ext = os.path.splitext(path)[1].lower()
    id_to_name = {}
    ids = []
    if ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r'^\s*(\d+)\s*[-\u2013]\s*(.+)', line)
                if m:
                    pid, name = m.group(1), m.group(2).strip()
                    id_to_name[pid] = name
                    ids.append(pid)
                else:
                    m2 = re.match(r'^\s*(\d+)\s*$', line.strip())
                    if m2:
                        ids.append(m2.group(1))
    elif ext == ".csv":
        for delim in [';', ',']:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f, delimiter=delim)
                    rows = list(reader)
                    if not rows:
                        continue
                    col = None
                    for c in ['Id','ID','PlayerId','PlayerID']:
                        if c in rows[0]:
                            col = c
                            break
                    name_col = None
                    for c in ['Name','PlayerName','name']:
                        if c in rows[0]:
                            name_col = c
                            break
                    if col:
                        for r in rows:
                            pid = r[col].strip()
                            if pid.isdigit():
                                ids.append(pid)
                                if name_col:
                                    id_to_name[pid] = r[name_col].strip()
                        break
            except Exception:
                continue
    seen = set(); out = []
    for i in ids:
        if i not in seen:
            seen.add(i); out.append(i)
    return out, id_to_name

def write_player_ids_csv(ids):
    with open(PLAYERID_CSV, "w", newline='', encoding="utf-8") as f:
        f.write("Id\n")
        for i in ids:
            f.write(i + "\n")

# ── main app ──────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FL26 Mod Automation")
        self.geometry("1100x820")
        self.minsize(900, 700)

        self.cfg = load_config()
        self.mod_widgets = {}   # key -> { enabled, mode_var, pct_var, manual_ids, btn_sec_dry, btn_sec_apply }
        self.player_ids  = []
        self._db_path    = ""
        self.id_to_name = {}   # id -> player name from DB

        self._build_ui()
        self._load_ui_from_config()

    # ── UI builder ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, height=50)
        top.pack(fill="x", padx=10, pady=(10,0))

        ctk.CTkLabel(top, text="Mod Root Folder:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(10,5))
        self.lbl_root = ctk.CTkLabel(top, text="Not selected", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_root.pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(top, text="Browse", width=100, command=self._choose_mod_root).pack(side="right", padx=10)

        # DB file bar
        db_bar = ctk.CTkFrame(self, height=50)
        db_bar.pack(fill="x", padx=10, pady=(5,0))

        ctk.CTkLabel(db_bar, text="Player DB File:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(10,5))
        self.lbl_db = ctk.CTkLabel(db_bar, text="Not selected", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_db.pack(side="left", padx=5, fill="x", expand=True)
        self.lbl_db_count = ctk.CTkLabel(db_bar, text="", font=ctk.CTkFont(size=12), text_color="lightgreen")
        self.lbl_db_count.pack(side="right", padx=(0,5))
        ctk.CTkButton(db_bar, text="Browse", width=100, command=self._choose_db_file).pack(side="right", padx=10)

        # Main area: scrollable mod list + log
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # Left: mod list
        left_scroll = ctk.CTkScrollableFrame(main, label_text="Mod Settings", width=520)
        left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0,5))

        for key, label in MOD_LABELS.items():
            self._build_mod_row(left_scroll, key, label)

        # Handtape section (separate)
        self._build_handtape_section(left_scroll)

        # Right: log
        right = ctk.CTkFrame(main)
        right.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="Log Output", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, pady=(5,0))
        self.txt_log = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Bottom buttons (global run all)
        btn_bar = ctk.CTkFrame(self, height=60)
        btn_bar.pack(fill="x", padx=10, pady=(0,10))

        self.lbl_status = ctk.CTkLabel(btn_bar, text="Status: idle", font=ctk.CTkFont(size=12))
        self.lbl_status.pack(side="left", padx=15)

        ctk.CTkButton(btn_bar, text="Clear Log",      width=110, fg_color="gray40",  command=self._clear_log).pack(side="right", padx=5)
        self.btn_run  = ctk.CTkButton(btn_bar, text="RUN ALL",    width=130, fg_color="#1a7a1a", command=self._run_real)
        self.btn_run.pack(side="right", padx=5)
        self.btn_dry  = ctk.CTkButton(btn_bar, text="DRY RUN ALL", width=140, fg_color="#1a4a7a", command=self._run_dry)
        self.btn_dry.pack(side="right", padx=5)
        ctk.CTkButton(btn_bar, text="Save Settings",  width=130, command=self._save_settings).pack(side="right", padx=5)

    def _build_mod_row(self, parent, key, label):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=5, pady=4)

        # Row 1: enable toggle + label
        row1 = ctk.CTkFrame(frame, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(6,2))

        enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row1, text=label, variable=enabled_var,
                        font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        # Row 2: mode selector + percent or manual
        row2 = ctk.CTkFrame(frame, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(0,4))

        mode_var = ctk.StringVar(value="percent")
        ctk.CTkRadioButton(row2, text="Percentage", variable=mode_var, value="percent",
                           command=lambda k=key: self._toggle_mode(k)).pack(side="left", padx=(0,10))
        ctk.CTkRadioButton(row2, text="Manual", variable=mode_var, value="manual",
                           command=lambda k=key: self._toggle_mode(k)).pack(side="left", padx=(0,15))

        # Percent controls
        pct_frame = ctk.CTkFrame(row2, fg_color="transparent")
        pct_frame.pack(side="left")
        ctk.CTkLabel(pct_frame, text="% :").pack(side="left")
        pct_var = ctk.IntVar(value=0)
        pct_entry = ctk.CTkEntry(pct_frame, textvariable=pct_var, width=55)
        pct_entry.pack(side="left", padx=4)

        # Manual controls
        manual_frame = ctk.CTkFrame(row2, fg_color="transparent")
        manual_ids = []

        def add_manual(k=key):
            self._add_manual_player(k)

        ctk.CTkButton(manual_frame, text="+ Add Player", width=110, command=add_manual).pack(side="left", padx=(0,5))

        def del_manual(k=key):
            self._delete_player_dialog(
                player_list=self.mod_widgets[k]["manual_ids"],
                on_done=lambda: self.mod_widgets[k]["manual_lbl"].configure(
                    text=f"{len(self.mod_widgets[k]['manual_ids'])} player(s)"
                ),
                title=f"Remove Player from {MOD_LABELS[k]}"
            )

        ctk.CTkButton(manual_frame, text="- Remove", width=90, fg_color="#7a1a1a",
                      command=del_manual).pack(side="left", padx=(0,5))
        manual_lbl = ctk.CTkLabel(manual_frame, text="0 players", font=ctk.CTkFont(size=11), text_color="gray")
        manual_lbl.pack(side="left")

        manual_frame.pack_forget()  # hidden by default

        # Row 3: per-section Dry Run / Apply buttons
        row3 = ctk.CTkFrame(frame, fg_color="transparent")
        row3.pack(fill="x", padx=8, pady=(2,6))

        btn_sec_dry = ctk.CTkButton(row3, text="Dry Run", width=90, height=26,
                                    fg_color="#1a4a7a", font=ctk.CTkFont(size=11),
                                    command=lambda k=key: self._run_section(k, dry_run=True))
        btn_sec_dry.pack(side="left", padx=(0,5))

        btn_sec_apply = ctk.CTkButton(row3, text="Apply", width=90, height=26,
                                      fg_color="#1a7a1a", font=ctk.CTkFont(size=11),
                                      command=lambda k=key: self._run_section(k, dry_run=False))
        btn_sec_apply.pack(side="left")

        self.mod_widgets[key] = {
            "enabled_var"   : enabled_var,
            "mode_var"      : mode_var,
            "pct_var"       : pct_var,
            "pct_frame"     : pct_frame,
            "manual_frame"  : manual_frame,
            "manual_ids"    : manual_ids,
            "manual_lbl"    : manual_lbl,
            "btn_sec_dry"   : btn_sec_dry,
            "btn_sec_apply" : btn_sec_apply,
        }

    def _build_handtape_section(self, parent):
        frame = ctk.CTkFrame(parent, border_width=2, border_color="#8B4513")
        frame.pack(fill="x", padx=5, pady=(10,4))

        ctk.CTkLabel(frame, text="Handtape (Manual Only)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=8, pady=(6,2))

        warn = ctk.CTkLabel(frame,
            text="⚠  WARNING: Do not use for players with in-game arm tattoos — it will overwrite them.",
            text_color="#FF6B35", font=ctk.CTkFont(size=11), wraplength=480, justify="left")
        warn.pack(anchor="w", padx=8, pady=(0,6))

        app_row = ctk.CTkFrame(frame, fg_color="transparent")
        app_row.pack(fill="x", padx=8, pady=(0,4))
        ctk.CTkLabel(app_row, text="PESEditor CSV:").pack(side="left")
        self.lbl_appearance = ctk.CTkLabel(app_row, text="Not selected", text_color="gray",
                                            font=ctk.CTkFont(size=11))
        self.lbl_appearance.pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(app_row, text="Browse", width=80,
                      command=self._choose_appearance_csv).pack(side="right")

        pid_row = ctk.CTkFrame(frame, fg_color="transparent")
        pid_row.pack(fill="x", padx=8, pady=(0,4))
        ctk.CTkButton(pid_row, text="+ Add Player", width=120, command=self._ht_add_player).pack(side="left", padx=(0,8))
        self.ht_players_lbl = ctk.CTkLabel(pid_row, text="No players added",
                                            font=ctk.CTkFont(size=11), text_color="gray")
        self.ht_players_lbl.pack(side="left", padx=8, fill="x", expand=True)
        ctk.CTkButton(pid_row, text="Clear", width=60, fg_color="gray40",
                      command=self._ht_clear_players).pack(side="right", padx=(4,0))
        ctk.CTkButton(pid_row, text="- Remove", width=90, fg_color="#7a1a1a",
                      command=self._ht_delete_player).pack(side="right")

        hand_row = ctk.CTkFrame(frame, fg_color="transparent")
        hand_row.pack(fill="x", padx=8, pady=(0,8))
        ctk.CTkLabel(hand_row, text="Hand:").pack(side="left")
        self.ht_left_var  = ctk.BooleanVar(value=True)
        self.ht_right_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(hand_row, text="Left Hand",  variable=self.ht_left_var).pack(side="left", padx=10)
        ctk.CTkCheckBox(hand_row, text="Right Hand", variable=self.ht_right_var).pack(side="left", padx=5)

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(anchor="e", padx=8, pady=(0,8))
        ctk.CTkButton(btn_row, text="Dry Run Handtape", fg_color="#1a4a7a",
                      command=lambda: self._run_handtape(dry_run=True)).pack(side="left", padx=(0,5))
        ctk.CTkButton(btn_row, text="Apply Handtape", fg_color="#8B4513",
                      command=lambda: self._run_handtape(dry_run=False)).pack(side="left")

        self.ht_players = []
        self.appearance_csv_path = ""

    # ── mode toggle ───────────────────────────────────────────────────────────

    def _toggle_mode(self, key):
        w = self.mod_widgets[key]
        if w["mode_var"].get() == "percent":
            w["manual_frame"].pack_forget()
            w["pct_frame"].pack(side="left")
        else:
            w["pct_frame"].pack_forget()
            w["manual_frame"].pack(side="left")

    # ── manual player management ──────────────────────────────────────────────

    def _add_manual_player(self, key):
        self._player_search_dialog(
            on_confirm=lambda pid, name: self._confirm_add_to_mod(key, pid, name)
        )

    def _confirm_add_to_mod(self, key, pid, name):
        w = self.mod_widgets[key]
        if pid not in w["manual_ids"]:
            w["manual_ids"].append(pid)
        w["manual_lbl"].configure(text=f"{len(w['manual_ids'])} player(s)")

    # ── handtape helpers ──────────────────────────────────────────────────────

    def _choose_appearance_csv(self):
        path = filedialog.askopenfilename(
            title="Select PESEditor Appearance CSV",
            filetypes=[("CSV files","*.csv"),("All files","*.*")]
        )
        if path:
            self.appearance_csv_path = path
            self.lbl_appearance.configure(text=os.path.basename(path), text_color="lightgreen")

    def _ht_add_player(self):
        self._player_search_dialog(
            on_confirm=lambda pid, name: self._confirm_add_ht(pid, name)
        )

    def _confirm_add_ht(self, pid, name):
        if pid not in self.ht_players:
            self.ht_players.append(pid)
        self._refresh_ht_label()

    def _delete_player_dialog(self, player_list, on_done, title="Remove Player"):
        """Show a list of added players and let the user remove one."""
        if not player_list:
            messagebox.showinfo("No Players", "No players to remove.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("420x360")
        dialog.grab_set()
        dialog.focus()

        ctk.CTkLabel(dialog, text="Select a player to remove:",
                     font=ctk.CTkFont(size=13)).pack(pady=(14,8))

        scroll = ctk.CTkScrollableFrame(dialog, height=220)
        scroll.pack(fill="x", padx=16, pady=(0,8))

        selected = {"pid": None, "btn": None}
        confirm_btn_ref = {}

        def select(pid, btn):
            if selected["btn"]:
                selected["btn"].configure(fg_color="transparent")
            selected["pid"] = pid
            selected["btn"] = btn
            btn.configure(fg_color="#7a1a1a")
            confirm_btn_ref["btn"].configure(state="normal")

        for pid in list(player_list):
            name = self.id_to_name.get(pid, "")
            label = f"{pid}  —  {name}" if name else pid
            btn = ctk.CTkButton(scroll, text=label, anchor="w",
                                fg_color="transparent", hover_color="#5a1a1a",
                                font=ctk.CTkFont(size=12))
            btn.configure(command=lambda p=pid, b=btn: select(p, b))
            btn.pack(fill="x", pady=1)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=(4,12))

        def do_remove():
            pid = selected["pid"]
            if pid and pid in player_list:
                player_list.remove(pid)
            on_done()
            dialog.destroy()

        confirm_btn = ctk.CTkButton(btn_row, text="Remove Player", width=140,
                                    fg_color="#7a1a1a", state="disabled",
                                    command=do_remove)
        confirm_btn.pack(side="left", padx=(0,10))
        confirm_btn_ref["btn"] = confirm_btn
        ctk.CTkButton(btn_row, text="Cancel", width=100, fg_color="gray40",
                      command=dialog.destroy).pack(side="left")

    def _player_search_dialog(self, on_confirm):
        """Modal search dialog: type name or ID, see results, confirm to add."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Player Search")
        dialog.geometry("480x400")
        dialog.grab_set()
        dialog.focus()

        ctk.CTkLabel(dialog, text="Search by name or ID:", font=ctk.CTkFont(size=13)).pack(pady=(14,4))

        search_var = ctk.StringVar()
        entry = ctk.CTkEntry(dialog, textvariable=search_var, width=340, placeholder_text="e.g. Messi or 158023")
        entry.pack(pady=(0,8))
        entry.focus()

        result_box = ctk.CTkScrollableFrame(dialog, height=220)
        result_box.pack(fill="x", padx=16, pady=(0,8))

        status_lbl = ctk.CTkLabel(dialog, text="", font=ctk.CTkFont(size=11), text_color="gray")
        status_lbl.pack()

        selected = {"pid": None, "name": None}
        btn_refs = []

        def do_search(*_):
            # Clear old results
            for w in result_box.winfo_children():
                w.destroy()
            btn_refs.clear()
            selected["pid"] = None
            selected["name"] = None
            confirm_btn.configure(state="disabled")

            query = search_var.get().strip()
            if not query:
                return

            results = []
            if query.isdigit():
                # ID lookup
                pid = query
                name = self.id_to_name.get(pid, "")
                if name:
                    results = [(pid, name)]
                elif pid in self.id_to_name or any(pid == i for i in (self.id_to_name or {})):
                    results = [(pid, "")]
                else:
                    status_lbl.configure(text="No player found with that ID.")
            else:
                # Name search (case-insensitive partial)
                q = query.lower()
                results = [(pid, name) for pid, name in self.id_to_name.items()
                           if q in name.lower()]
                results = sorted(results, key=lambda x: x[1])[:50]
                if not results:
                    status_lbl.configure(text="No players found matching that name.")
                else:
                    status_lbl.configure(text=f"{len(results)} result(s) — click to select")

            for pid, name in results:
                label = f"{pid}  —  {name}" if name else pid
                btn = ctk.CTkButton(result_box, text=label, anchor="w",
                                    fg_color="transparent", hover_color="#2a4a6a",
                                    font=ctk.CTkFont(size=12),
                                    command=lambda p=pid, n=name: select_player(p, n))
                btn.pack(fill="x", pady=1)
                btn_refs.append(btn)

        def select_player(pid, name):
            selected["pid"] = pid
            selected["name"] = name
            display = f"{name}  (ID: {pid})" if name else f"ID: {pid}"
            status_lbl.configure(
                text=f"Selected: {display}",
                text_color="lightgreen"
            )
            confirm_btn.configure(state="normal")

        search_var.trace_add("write", do_search)
        entry.bind("<Return>", do_search)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=(4,12))

        confirm_btn = ctk.CTkButton(btn_row, text="Add Player", width=130, state="disabled",
                                    fg_color="#1a7a1a",
                                    command=lambda: [
                                        on_confirm(selected["pid"], selected["name"]),
                                        dialog.destroy()
                                    ])
        confirm_btn.pack(side="left", padx=(0,10))
        ctk.CTkButton(btn_row, text="Cancel", width=100, fg_color="gray40",
                      command=dialog.destroy).pack(side="left")

    def _refresh_ht_label(self):
        count = len(self.ht_players)
        if count == 0:
            self.ht_players_lbl.configure(text="No players added", text_color="gray")
        else:
            names = []
            for pid in self.ht_players[-3:]:
                n = self.id_to_name.get(pid, pid)
                names.append(n)
            self.ht_players_lbl.configure(
                text=f"{count} player(s): {', '.join(names)}",
                text_color="lightgreen"
            )

    def _ht_clear_players(self):
        self.ht_players.clear()
        self._refresh_ht_label()

    def _ht_delete_player(self):
        """Show a dialog to remove a player from the handtape list."""
        self._delete_player_dialog(
            player_list=self.ht_players,
            on_done=self._refresh_ht_label,
            title="Remove Handtape Player"
        )

    # ── file choosers ─────────────────────────────────────────────────────────

    def _choose_mod_root(self):
        path = filedialog.askdirectory(title="Select Mod Root Folder")
        if path:
            self.lbl_root.configure(text=path, text_color="lightgreen")
            self.cfg["modRootPath"] = path
            save_config(self.cfg)
            self._log(f"Mod root set: {path}")

    def _choose_db_file(self):
        path = filedialog.askopenfilename(
            title="Select Player DB File",
            filetypes=[("Supported DB files","*.txt *.csv"),("Text","*.txt"),("CSV","*.csv"),("All","*.*")]
        )
        if path:
            try:
                ids, names = parse_db_file_with_names(path)
                self.id_to_name = names
                if not ids:
                    messagebox.showerror("Parse Error", "No player IDs found in selected file.")
                    return
                write_player_ids_csv(ids)
                self.player_ids = ids
                self._db_path   = path
                ext = os.path.splitext(path)[1].lower()
                fmt = "FL26 TXT" if ext == ".txt" else "CSV"
                self.lbl_db.configure(text=os.path.basename(path), text_color="lightgreen")
                self.lbl_db_count.configure(text=f"{fmt} | {len(ids):,} players")
                self._log(f"DB loaded: {path} ({len(ids):,} IDs)")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ── settings ──────────────────────────────────────────────────────────────

    def _load_ui_from_config(self):
        root = self.cfg.get("modRootPath","")
        if root:
            self.lbl_root.configure(text=root, text_color="lightgreen")

        mods = self.cfg.get("mods", {})
        for key, w in self.mod_widgets.items():
            mod = mods.get(key, {})
            if "enabled" in mod:
                w["enabled_var"].set(mod["enabled"])
            # percentages always start at 0 on launch
            w["pct_var"].set(0)
            manual = mod.get("manualPlayerIds", [])
            if manual:
                w["manual_ids"].extend(manual)
                w["manual_lbl"].configure(text=f"{len(w['manual_ids'])} player(s)")

    def _save_settings(self):
        mods = self.cfg.setdefault("mods", {})
        for key, w in self.mod_widgets.items():
            mod = mods.setdefault(key, {})
            mod["enabled"]         = w["enabled_var"].get()
            mod["percent"]         = w["pct_var"].get()
            mod["manualPlayerIds"] = w["manual_ids"]
        save_config(self.cfg)
        self._log("Settings saved.")

        # Copy DB and Appearance files to "DB and Appearances" folder
        dest_folder = os.path.join(PACKAGE_DIR, "DB and Appearances")
        os.makedirs(dest_folder, exist_ok=True)
        copied = []
        if self._db_path and os.path.isfile(self._db_path):
            shutil.copy2(self._db_path, dest_folder)
            copied.append(os.path.basename(self._db_path))
        if self.appearance_csv_path and os.path.isfile(self.appearance_csv_path):
            shutil.copy2(self.appearance_csv_path, dest_folder)
            copied.append(os.path.basename(self.appearance_csv_path))
        if copied:
            self._log(f"Saved to 'DB and Appearances': {', '.join(copied)}")

    # ── helpers: disable/enable ALL run buttons at once ───────────────────────

    def _set_all_buttons(self, state):
        self.btn_dry.configure(state=state)
        self.btn_run.configure(state=state)
        for w in self.mod_widgets.values():
            w["btn_sec_dry"].configure(state=state)
            w["btn_sec_apply"].configure(state=state)

    # ── run: per-section ──────────────────────────────────────────────────────

    def _run_section(self, key, dry_run=False):
        self._save_settings()
        root = self.cfg.get("modRootPath","")
        if not root or not os.path.isdir(root):
            messagebox.showwarning("Missing Folder", "Please select a Mod Root Folder first.")
            return
        if not os.path.exists(PLAYERID_CSV):
            messagebox.showwarning("Missing DB", "Please select a Player DB file first.")
            return
        if not dry_run:
            if not messagebox.askyesno("Confirm Apply",
                f"This will COPY folders for {MOD_LABELS[key]} into your mod directory.\n\nContinue?"):
                return

        mode = "DryRun" if dry_run else "Run"
        label = MOD_LABELS[key]
        mode_label = f"{'Dry Run' if dry_run else 'Apply'}: {label}"

        self._set_all_buttons("disabled")
        self.lbl_status.configure(text=f"Status: {mode_label}...")

        def run():
            script = os.path.join(PACKAGE_DIR, "Run-FL26-ModAutomation.ps1")
            cmd = [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", script,
                "-Mode", mode,
                "-ConfigPath", CONFIG_PATH,
                "-SingleMod", key
            ]
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                for line in proc.stdout:
                    self.after(0, self._log, line.rstrip())
                proc.wait()
                exit_code = proc.returncode
                self.after(0, self._set_all_buttons, "normal")
                if exit_code == 0:
                    self.after(0, self.lbl_status.configure, {"text": f"Status: {mode_label} done", "text_color": "lightgreen"})
                    self.after(0, messagebox.showinfo, "Done", f"{mode_label} completed successfully.")
                else:
                    self.after(0, self.lbl_status.configure, {"text": f"Status: {mode_label} errors", "text_color": "#FF6B35"})
                    self.after(0, messagebox.showwarning, "Errors", "Finished with errors. Check the log.")
            except Exception as e:
                self.after(0, self._log, f"[ERROR] {e}")
                self.after(0, self.lbl_status.configure, {"text": "Status: Error", "text_color": "red"})
                self.after(0, self._set_all_buttons, "normal")

        threading.Thread(target=run, daemon=True).start()

    # ── run: global ───────────────────────────────────────────────────────────

    def _run_dry(self):
        self._save_settings()
        self._execute("DryRun")

    def _run_real(self):
        self._save_settings()
        if not messagebox.askyesno("Confirm RUN ALL",
            "This will COPY folders for ALL enabled mods into your mod directories.\n\nContinue?"):
            return
        self._execute("Run")

    def _execute(self, mode):
        root = self.cfg.get("modRootPath","")
        if not root or not os.path.isdir(root):
            messagebox.showwarning("Missing Folder", "Please select a Mod Root Folder first.")
            return
        if not os.path.exists(PLAYERID_CSV):
            messagebox.showwarning("Missing DB", "Please select a Player DB file first.")
            return

        self._set_all_buttons("disabled")
        self.lbl_status.configure(text=f"Status: Running {mode}...")

        def run():
            script = os.path.join(PACKAGE_DIR, "Run-FL26-ModAutomation.ps1")
            cmd = [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", script,
                "-Mode", mode,
                "-ConfigPath", CONFIG_PATH
            ]
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                for line in proc.stdout:
                    self.after(0, self._log, line.rstrip())
                proc.wait()
                exit_code = proc.returncode
                self.after(0, self._set_all_buttons, "normal")
                if exit_code == 0:
                    self.after(0, self.lbl_status.configure, {"text": "Status: Completed successfully", "text_color": "lightgreen"})
                    self.after(0, messagebox.showinfo, "Done", f"{mode} completed successfully.")
                else:
                    self.after(0, self.lbl_status.configure, {"text": "Status: Finished with errors", "text_color": "#FF6B35"})
                    self.after(0, messagebox.showwarning, "Errors", "Finished with errors. Check the log.")
            except Exception as e:
                self.after(0, self._log, f"[ERROR] {e}")
                self.after(0, self.lbl_status.configure, {"text": "Status: Error", "text_color": "red"})
                self.after(0, self._set_all_buttons, "normal")

        threading.Thread(target=run, daemon=True).start()

    def _run_handtape(self, dry_run=False):
        if not self.appearance_csv_path:
            messagebox.showwarning("Missing CSV", "Please select your PESEditor Appearance CSV first.")
            return
        if not self.ht_players:
            messagebox.showwarning("No Players", "Please add at least one Player ID.")
            return
        hands = []
        if self.ht_left_var.get():  hands.append("left hand")
        if self.ht_right_var.get(): hands.append("right hand")
        if not hands:
            messagebox.showwarning("No Hand", "Please select at least one hand.")
            return

        root    = self.cfg.get("modRootPath","")
        ht_root = os.path.join(root, "xTexture_Hand Tape")
        if not os.path.isdir(ht_root):
            messagebox.showerror("Folder Not Found", f"Handtape folder not found:\n{ht_root}")
            return

        mode_label = "Dry Run Handtape" if dry_run else "Handtape"
        self._set_all_buttons("disabled")
        self.lbl_status.configure(text=f"Status: Running {mode_label}...")

        def run():
            script     = os.path.join(PACKAGE_DIR, "Assign-Handtape.ps1")
            ids_pipe   = "|".join(self.ht_players)
            hands_pipe = "|".join(hands)
            cmd = [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", script,
                "-AppearanceCsvPath", self.appearance_csv_path,
                "-RootPath",          ht_root,
                "-PlayerIdsPipe",     ids_pipe,
                "-HandsPipe",         hands_pipe
            ]
            if dry_run:
                cmd.append("-DryRun")
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                for line in proc.stdout:
                    self.after(0, self._log, line.rstrip())
                proc.wait()
                self.after(0, self._set_all_buttons, "normal")
                if proc.returncode == 0:
                    done_msg = "Dry run complete. No files copied." if dry_run else "Handtape assignment complete."
                    self.after(0, self.lbl_status.configure, {"text": f"Status: {mode_label} done", "text_color": "lightgreen"})
                    self.after(0, messagebox.showinfo, "Done", done_msg)
                else:
                    self.after(0, self.lbl_status.configure, {"text": f"Status: {mode_label} errors", "text_color": "#FF6B35"})
            except Exception as e:
                self.after(0, self._log, f"[ERROR] {e}")
                self.after(0, self._set_all_buttons, "normal")

        threading.Thread(target=run, daemon=True).start()

    # ── log ───────────────────────────────────────────────────────────────────

    def _log(self, msg):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _clear_log(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
