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

# ── mod definitions ───────────────────────────────────────────────────────────

MOD_LABELS = {
    "gripSoxBrands"    : "Grip Sock - Brands",
    "sockHoles"        : "Sock - Holes",
    "sockMiddleHigh"   : "Sock - Middle High",
    "sockShortGroup"   : "Sock - Short Group",
    "pantsBaggy"       : "Pants - Baggy",
    "pantsExtraBaggy"  : "Pants - Extra Baggy",
    "pantsShorter"     : "Pants - Shorter",
    "shirtBaggy"       : "Shirt - Baggy",
    "glovesBrands"     : "Gloves - Brands",
}

MOD_FOLDERS = {
    "gripSoxBrands"    : "Grip Sock-Brands",
    "sockHoles"        : "Sock-Holes",
    "sockMiddleHigh"   : "Sock-Middle High",
    "sockShortGroup"   : "Sock-Short",
    "pantsBaggy"       : "Pants-Baggy",
    "pantsExtraBaggy"  : "Pants-Extra Baggy",
    "pantsShorter"     : "Pants-Shorter",
    "shirtBaggy"       : "Shirt-Baggy",
    "glovesBrands"     : "Gloves-Brands",
}

PER_VARIATION_KEYS = {
    "gripSoxBrands"  : "Grip Sock-Brands",
    "sockHoles"      : "Sock-Holes",
    "sockShortGroup" : "Sock-Short",
    "glovesBrands"   : "Gloves-Brands",
}

# Grouped sections: each variation is its own top-level folder detected by prefix
GROUPED_SECTIONS = {
    "gripSoxLength" : {
        "label"          : "Grip Sock - Length",
        "folder_prefix"  : "Grip Sock-",
        "logPrefix"      : "GripSoxLength",
        "exclude_folders": ["Grip Sock-Brands"],
    },
    "sleeveRollUp" : {
        "label"         : "Sleeve - Roll Up",
        "folder_prefix" : "Sleeve Roll Up-",
        "logPrefix"     : "SleeveRollUp",
    },
    "sleeveInner"  : {
        "label"         : "Sleeve - Inner",
        "folder_prefix" : "Sleeve Inner-",
        "logPrefix"     : "SleeveInner",
    },
    "wristtaping"  : {
        "label"         : "Wristtaping",
        "folder_prefix" : "Wristtaping ",
        "logPrefix"     : "Wristtaping",
    },
}

REL_REAL = os.path.join("Asset", "model", "character", "face", "real")

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

def parse_db_file_with_names(path):
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

# ── variation detectors ───────────────────────────────────────────────────────

def detect_variations(mod_root, folder_name):
    """For brand/template style mods — subfolders inside one root folder."""
    # sockShortGroup spans multiple top-level folders — detect by prefix
    if folder_name == "Sock-Short":
        prefixes = ("Sock-Short", "Sock-Extreme Short", "Sock-Shinpads")
        results = []
        if not os.path.isdir(mod_root):
            return []
        for d in sorted(os.listdir(mod_root)):
            if any(d.startswith(p) for p in prefixes):
                full = os.path.join(mod_root, d)
                if os.path.isdir(full) and os.path.isdir(os.path.join(full, REL_REAL)):
                    results.append(d)
        return results

    base = os.path.join(mod_root, folder_name)
    if not os.path.isdir(base):
        return []
    real_check = os.path.join(base, REL_REAL)
    if not os.path.isdir(real_check):
        variations = []
        for d in sorted(os.listdir(base)):
            full = os.path.join(base, d)
            if os.path.isdir(full) and not d.startswith('.'):
                if os.path.isdir(os.path.join(full, REL_REAL)):
                    variations.append(d)
        return variations
    else:
        templates = []
        for d in sorted(os.listdir(real_check)):
            full = os.path.join(real_check, d)
            if os.path.isdir(full) and d.startswith("ID Players"):
                templates.append(d)
        return templates if len(templates) > 1 else []

def detect_grouped_variations(mod_root, folder_prefix, exclude_folders=None):
    """For grouped sections — each variation is its own top-level folder."""
    if not os.path.isdir(mod_root):
        return []
    exclude = set(exclude_folders or [])
    results = []
    for d in sorted(os.listdir(mod_root)):
        if d.startswith(folder_prefix) and d not in exclude:
            full = os.path.join(mod_root, d)
            if os.path.isdir(full):
                label = d[len(folder_prefix):]
                results.append((label, d))
    return results

# ── main app ──────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FL26 Mod Automation")
        self.geometry("1100x900")
        self.minsize(900, 700)

        self.cfg             = load_config()
        self.mod_widgets     = {}
        self.player_ids      = []
        self._db_path        = ""
        self.appearance_csv_path = ""
        self.id_to_name      = {}
        self.variation_widgets   = {}
        self.detected_variations = {}
        self.grouped_widgets     = {}
        self.detected_grouped    = {}

        self._build_ui()
        self._load_ui_from_config()

    # ── UI builder ────────────────────────────────────────────────────────────

    def _build_ui(self):
        top = ctk.CTkFrame(self, height=50)
        top.pack(fill="x", padx=10, pady=(10,0))
        ctk.CTkLabel(top, text="Mod Root Folder:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(10,5))
        self.lbl_root = ctk.CTkLabel(top, text="Not selected", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_root.pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(top, text="Browse", width=100, command=self._choose_mod_root).pack(side="right", padx=10)

        db_bar = ctk.CTkFrame(self, height=50)
        db_bar.pack(fill="x", padx=10, pady=(5,0))
        ctk.CTkLabel(db_bar, text="Player DB File:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(10,5))
        self.lbl_db = ctk.CTkLabel(db_bar, text="Not selected", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_db.pack(side="left", padx=5, fill="x", expand=True)
        self.lbl_db_count = ctk.CTkLabel(db_bar, text="", font=ctk.CTkFont(size=12), text_color="lightgreen")
        self.lbl_db_count.pack(side="right", padx=(0,5))
        ctk.CTkButton(db_bar, text="Browse", width=100, command=self._choose_db_file).pack(side="right", padx=10)

        app_bar = ctk.CTkFrame(self, height=50)
        app_bar.pack(fill="x", padx=10, pady=(5,0))
        ctk.CTkLabel(app_bar, text="PESEditor Appearances CSV:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(10,5))
        self.lbl_appearance = ctk.CTkLabel(app_bar, text="Not selected", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_appearance.pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(app_bar, text="Browse", width=100, command=self._choose_appearance_csv).pack(side="right", padx=10)

        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        self._left_scroll = ctk.CTkScrollableFrame(main, label_text="Mod Settings", width=520)
        self._left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0,5))

        for key, label in MOD_LABELS.items():
            self._build_mod_row(self._left_scroll, key, label)

        for key, info in GROUPED_SECTIONS.items():
            self._build_grouped_section(self._left_scroll, key, info)

        self._build_handtape_section(self._left_scroll)

        right = ctk.CTkFrame(main)
        right.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ctk.CTkLabel(right, text="Log Output", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, pady=(5,0))
        self.txt_log = ctk.CTkTextbox(right, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        btn_bar = ctk.CTkFrame(self, height=60)
        btn_bar.pack(fill="x", padx=10, pady=(0,10))
        self.lbl_status = ctk.CTkLabel(btn_bar, text="Status: idle", font=ctk.CTkFont(size=12))
        self.lbl_status.pack(side="left", padx=15)
        ctk.CTkButton(btn_bar, text="Clear Log",      width=110, fg_color="gray40",  command=self._clear_log).pack(side="right", padx=5)
        self.btn_run = ctk.CTkButton(btn_bar, text="RUN ALL",    width=130, fg_color="#1a7a1a", command=self._run_real)
        self.btn_run.pack(side="right", padx=5)
        self.btn_dry = ctk.CTkButton(btn_bar, text="DRY RUN ALL", width=140, fg_color="#1a4a7a", command=self._run_dry)
        self.btn_dry.pack(side="right", padx=5)
        ctk.CTkButton(btn_bar, text="Save Settings",  width=130, command=self._save_settings).pack(side="right", padx=5)

    # ── standard mod row ──────────────────────────────────────────────────────

    def _build_mod_row(self, parent, key, label):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=5, pady=4)

        row1 = ctk.CTkFrame(frame, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(6,2))
        enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row1, text=label, variable=enabled_var,
                        font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        variation_toggle_var = None
        variation_body_frame = None

        if key in PER_VARIATION_KEYS:
            variation_toggle_var = ctk.BooleanVar(value=False)
            toggle_row = ctk.CTkFrame(frame, fg_color="transparent")
            toggle_row.pack(fill="x", padx=8, pady=(0,2))
            ctk.CTkLabel(toggle_row, text="Assignment mode:",
                         font=ctk.CTkFont(size=11), text_color="gray").pack(side="left", padx=(0,8))
            ctk.CTkRadioButton(toggle_row, text="Random Across All",
                               variable=variation_toggle_var, value=False,
                               command=lambda k=key: self._toggle_variation_mode(k),
                               font=ctk.CTkFont(size=11)).pack(side="left", padx=(0,10))
            ctk.CTkRadioButton(toggle_row, text="Per Variation",
                               variable=variation_toggle_var, value=True,
                               command=lambda k=key: self._toggle_variation_mode(k),
                               font=ctk.CTkFont(size=11)).pack(side="left")
            variation_body_frame = ctk.CTkFrame(frame, fg_color="transparent")

        row2 = ctk.CTkFrame(frame, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(0,4))
        mode_var = ctk.StringVar(value="percent")
        ctk.CTkRadioButton(row2, text="Percentage", variable=mode_var, value="percent",
                           command=lambda k=key: self._toggle_mode(k)).pack(side="left", padx=(0,10))
        ctk.CTkRadioButton(row2, text="Manual", variable=mode_var, value="manual",
                           command=lambda k=key: self._toggle_mode(k)).pack(side="left", padx=(0,15))
        pct_frame = ctk.CTkFrame(row2, fg_color="transparent")
        pct_frame.pack(side="left")
        ctk.CTkLabel(pct_frame, text="% :").pack(side="left")
        pct_var = ctk.IntVar(value=0)
        ctk.CTkEntry(pct_frame, textvariable=pct_var, width=55).pack(side="left", padx=4)
        manual_frame = ctk.CTkFrame(row2, fg_color="transparent")
        manual_ids   = []
        ctk.CTkButton(manual_frame, text="+ Add Player", width=110,
                      command=lambda k=key: self._add_manual_player(k)).pack(side="left", padx=(0,5))
        ctk.CTkButton(manual_frame, text="- Remove", width=90, fg_color="#7a1a1a",
                      command=lambda k=key: self._delete_player_dialog(
                          player_list=self.mod_widgets[k]["manual_ids"],
                          on_done=lambda: self.mod_widgets[k]["manual_lbl"].configure(
                              text=f"{len(self.mod_widgets[k]['manual_ids'])} player(s)"),
                          title=f"Remove Player from {MOD_LABELS[k]}"
                      )).pack(side="left", padx=(0,5))
        manual_lbl = ctk.CTkLabel(manual_frame, text="0 players", font=ctk.CTkFont(size=11), text_color="gray")
        manual_lbl.pack(side="left")
        manual_frame.pack_forget()

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
            "enabled_var"          : enabled_var,
            "mode_var"             : mode_var,
            "pct_var"              : pct_var,
            "pct_frame"            : pct_frame,
            "manual_frame"         : manual_frame,
            "manual_ids"           : manual_ids,
            "manual_lbl"           : manual_lbl,
            "btn_sec_dry"          : btn_sec_dry,
            "btn_sec_apply"        : btn_sec_apply,
            "variation_toggle_var" : variation_toggle_var,
            "variation_body_frame" : variation_body_frame,
            "standard_row2"        : row2,
            "standard_row3"        : row3,
        }
        self.variation_widgets[key] = {}

    # ── grouped section ───────────────────────────────────────────────────────

    def _build_grouped_section(self, parent, key, info):
        frame = ctk.CTkFrame(parent, border_width=1, border_color="#3a5a3a")
        frame.pack(fill="x", padx=5, pady=4)

        row1 = ctk.CTkFrame(frame, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(6,2))
        enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row1, text=info["label"], variable=enabled_var,
                        font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        toggle_var = ctk.BooleanVar(value=False)
        toggle_row = ctk.CTkFrame(frame, fg_color="transparent")
        toggle_row.pack(fill="x", padx=8, pady=(0,2))
        ctk.CTkLabel(toggle_row, text="Assignment mode:",
                     font=ctk.CTkFont(size=11), text_color="gray").pack(side="left", padx=(0,8))
        ctk.CTkRadioButton(toggle_row, text="Random Across All",
                           variable=toggle_var, value=False,
                           command=lambda k=key: self._toggle_grouped_mode(k),
                           font=ctk.CTkFont(size=11)).pack(side="left", padx=(0,10))
        ctk.CTkRadioButton(toggle_row, text="Per Variation",
                           variable=toggle_var, value=True,
                           command=lambda k=key: self._toggle_grouped_mode(k),
                           font=ctk.CTkFont(size=11)).pack(side="left")

        std_row = ctk.CTkFrame(frame, fg_color="transparent")
        std_row.pack(fill="x", padx=8, pady=(0,4))
        mode_var = ctk.StringVar(value="percent")
        ctk.CTkRadioButton(std_row, text="Percentage", variable=mode_var, value="percent",
                           command=lambda k=key: self._toggle_grouped_std_mode(k)).pack(side="left", padx=(0,10))
        ctk.CTkRadioButton(std_row, text="Manual", variable=mode_var, value="manual",
                           command=lambda k=key: self._toggle_grouped_std_mode(k)).pack(side="left", padx=(0,15))
        pct_frame = ctk.CTkFrame(std_row, fg_color="transparent")
        pct_frame.pack(side="left")
        ctk.CTkLabel(pct_frame, text="% :").pack(side="left")
        pct_var = ctk.IntVar(value=0)
        ctk.CTkEntry(pct_frame, textvariable=pct_var, width=55).pack(side="left", padx=4)
        manual_frame = ctk.CTkFrame(std_row, fg_color="transparent")
        manual_ids   = []
        ctk.CTkButton(manual_frame, text="+ Add Player", width=110,
                      command=lambda k=key: self._add_grouped_manual_player(k)).pack(side="left", padx=(0,5))
        ctk.CTkButton(manual_frame, text="- Remove", width=90, fg_color="#7a1a1a",
                      command=lambda k=key: self._remove_grouped_manual_player(k)).pack(side="left", padx=(0,5))
        manual_lbl = ctk.CTkLabel(manual_frame, text="0 players", font=ctk.CTkFont(size=11), text_color="gray")
        manual_lbl.pack(side="left")
        manual_frame.pack_forget()

        var_body = ctk.CTkFrame(frame, fg_color="transparent")

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=(2,6))
        btn_dry = ctk.CTkButton(btn_row, text="Dry Run", width=90, height=26,
                                fg_color="#1a4a7a", font=ctk.CTkFont(size=11),
                                command=lambda k=key: self._run_grouped(k, dry_run=True))
        btn_dry.pack(side="left", padx=(0,5))
        btn_apply = ctk.CTkButton(btn_row, text="Apply", width=90, height=26,
                                  fg_color="#1a7a1a", font=ctk.CTkFont(size=11),
                                  command=lambda k=key: self._run_grouped(k, dry_run=False))
        btn_apply.pack(side="left")

        self.grouped_widgets[key] = {
            "enabled_var"  : enabled_var,
            "toggle_var"   : toggle_var,
            "mode_var"     : mode_var,
            "pct_var"      : pct_var,
            "pct_frame"    : pct_frame,
            "manual_frame" : manual_frame,
            "manual_ids"   : manual_ids,
            "manual_lbl"   : manual_lbl,
            "std_row"      : std_row,
            "var_body"     : var_body,
            "btn_dry"      : btn_dry,
            "btn_apply"    : btn_apply,
            "variations"   : {},
        }
        self.detected_grouped[key] = []

    def _toggle_grouped_mode(self, key):
        gw = self.grouped_widgets[key]
        if gw["toggle_var"].get():
            gw["std_row"].pack_forget()
            gw["var_body"].pack(fill="x", padx=8, pady=(0,4))
            self._rebuild_grouped_rows(key)
        else:
            gw["var_body"].pack_forget()
            gw["std_row"].pack(fill="x", padx=8, pady=(0,4))

    def _toggle_grouped_std_mode(self, key):
        gw = self.grouped_widgets[key]
        if gw["mode_var"].get() == "percent":
            gw["manual_frame"].pack_forget()
            gw["pct_frame"].pack(side="left")
        else:
            gw["pct_frame"].pack_forget()
            gw["manual_frame"].pack(side="left")

    def _rebuild_grouped_rows(self, key):
        gw   = self.grouped_widgets[key]
        body = gw["var_body"]
        for child in body.winfo_children():
            child.destroy()
        gw["variations"] = {}

        variations = self.detected_grouped.get(key, [])
        if not variations:
            mod_root = self.cfg.get("modRootPath", "")
            if mod_root:
                prefix     = GROUPED_SECTIONS[key]["folder_prefix"]
                excludes   = GROUPED_SECTIONS[key].get("exclude_folders")
                variations = detect_grouped_variations(mod_root, prefix, excludes)
                self.detected_grouped[key] = variations

        if not variations:
            ctk.CTkLabel(body, text="⚠  No variations detected. Set Mod Root Folder first.",
                         text_color="#FF6B35", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=4)
            return

        hdr = ctk.CTkFrame(body, fg_color="transparent")
        hdr.pack(fill="x", pady=(2,0))
        ctk.CTkLabel(hdr, text="Variation", width=180, font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text="Mode",      width=140, font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text="%",         width=55,  font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side="left")

        for lbl, folder_name in variations:
            self._build_grouped_variation_row(body, key, lbl, folder_name)

    def _build_grouped_variation_row(self, parent, key, label, folder_name):
        row = ctk.CTkFrame(parent, fg_color="#2a2a2a", corner_radius=6)
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, width=180, font=ctk.CTkFont(size=11), anchor="w").pack(side="left", padx=(8,0))

        mode_var = ctk.StringVar(value="percent")
        rf = ctk.CTkFrame(row, fg_color="transparent", width=140)
        rf.pack(side="left")
        ctk.CTkRadioButton(rf, text="%", variable=mode_var, value="percent", width=40,
                           font=ctk.CTkFont(size=11),
                           command=lambda k=key, l=label: self._toggle_grouped_var_mode(k, l)
                           ).pack(side="left", padx=(4,2))
        ctk.CTkRadioButton(rf, text="Manual", variable=mode_var, value="manual", width=70,
                           font=ctk.CTkFont(size=11),
                           command=lambda k=key, l=label: self._toggle_grouped_var_mode(k, l)
                           ).pack(side="left", padx=(0,4))

        pct_var   = ctk.IntVar(value=0)
        pct_entry = ctk.CTkEntry(row, textvariable=pct_var, width=50, font=ctk.CTkFont(size=11))
        pct_entry.pack(side="left", padx=4)
        pct_var.trace_add("write", lambda *_, k=key, l=label: self._check_grouped_pct(k, l))

        manual_frame = ctk.CTkFrame(row, fg_color="transparent")
        manual_ids   = []
        ctk.CTkButton(manual_frame, text="+ Add", width=70, height=24, font=ctk.CTkFont(size=11),
                      command=lambda k=key, l=label: self._add_grouped_var_player(k, l)
                      ).pack(side="left", padx=(0,3))
        ctk.CTkButton(manual_frame, text="- Remove", width=80, height=24,
                      fg_color="#7a1a1a", font=ctk.CTkFont(size=11),
                      command=lambda k=key, l=label: self._remove_grouped_var_player(k, l)
                      ).pack(side="left", padx=(0,3))
        man_lbl = ctk.CTkLabel(manual_frame, text="0", font=ctk.CTkFont(size=11), text_color="gray")
        man_lbl.pack(side="left")
        manual_frame.pack_forget()

        warn_lbl = ctk.CTkLabel(row, text="⚠ 100% — ALL eligible players",
                                text_color="#FF6B35", font=ctk.CTkFont(size=10))

        self.grouped_widgets[key]["variations"][label] = {
            "folder_name"  : folder_name,
            "mode_var"     : mode_var,
            "pct_var"      : pct_var,
            "pct_entry"    : pct_entry,
            "manual_frame" : manual_frame,
            "manual_ids"   : manual_ids,
            "man_lbl"      : man_lbl,
            "warn_lbl"     : warn_lbl,
        }

    def _toggle_grouped_var_mode(self, key, label):
        vw = self.grouped_widgets[key]["variations"].get(label)
        if not vw: return
        if vw["mode_var"].get() == "percent":
            vw["manual_frame"].pack_forget()
            vw["pct_entry"].pack(side="left", padx=4)
        else:
            vw["pct_entry"].pack_forget()
            vw["manual_frame"].pack(side="left", padx=4)

    def _check_grouped_pct(self, key, label):
        try:
            vw = self.grouped_widgets[key]["variations"].get(label)
            if not vw: return
            if vw["pct_var"].get() >= 100:
                vw["warn_lbl"].pack(side="left", padx=(4,0))
            else:
                vw["warn_lbl"].pack_forget()
        except Exception:
            pass

    def _add_grouped_manual_player(self, key):
        self._player_search_dialog(on_confirm=lambda pid, name: self._confirm_grouped_manual(key, pid))

    def _confirm_grouped_manual(self, key, pid):
        gw = self.grouped_widgets[key]
        if pid not in gw["manual_ids"]: gw["manual_ids"].append(pid)
        gw["manual_lbl"].configure(text=f"{len(gw['manual_ids'])} player(s)")

    def _remove_grouped_manual_player(self, key):
        gw = self.grouped_widgets[key]
        self._delete_player_dialog(
            player_list=gw["manual_ids"],
            on_done=lambda: gw["manual_lbl"].configure(text=f"{len(gw['manual_ids'])} player(s)"),
            title=f"Remove Player from {GROUPED_SECTIONS[key]['label']}"
        )

    def _add_grouped_var_player(self, key, label):
        self._player_search_dialog(on_confirm=lambda pid, name: self._confirm_grouped_var(key, label, pid))

    def _confirm_grouped_var(self, key, label, pid):
        vw = self.grouped_widgets[key]["variations"].get(label)
        if not vw: return
        if pid not in vw["manual_ids"]: vw["manual_ids"].append(pid)
        vw["man_lbl"].configure(text=f"{len(vw['manual_ids'])}")

    def _remove_grouped_var_player(self, key, label):
        vw = self.grouped_widgets[key]["variations"].get(label)
        if not vw: return
        self._delete_player_dialog(
            player_list=vw["manual_ids"],
            on_done=lambda: vw["man_lbl"].configure(text=f"{len(vw['manual_ids'])}"),
            title=f"Remove Player from {label}"
        )

    def _has_any_100_grouped(self, key):
        hits = []
        for label, vw in self.grouped_widgets[key]["variations"].items():
            if vw["mode_var"].get() == "percent":
                try:
                    if vw["pct_var"].get() >= 100: hits.append(label)
                except Exception: pass
        return hits

    # ── standard per-variation (PER_VARIATION_KEYS mods) ─────────────────────

    def _toggle_variation_mode(self, key):
        w = self.mod_widgets[key]
        if w["variation_toggle_var"].get():
            w["standard_row2"].pack_forget()
            w["standard_row3"].pack_forget()
            w["variation_body_frame"].pack(fill="x", padx=8, pady=(0,6))
            self._rebuild_variation_rows(key)
        else:
            w["variation_body_frame"].pack_forget()
            w["standard_row2"].pack(fill="x", padx=8, pady=(0,4))
            w["standard_row3"].pack(fill="x", padx=8, pady=(2,6))

    def _rebuild_variation_rows(self, key):
        w    = self.mod_widgets[key]
        body = w["variation_body_frame"]
        for child in body.winfo_children():
            child.destroy()
        self.variation_widgets[key] = {}

        variations = self.detected_variations.get(key, [])
        if not variations:
            mod_root = self.cfg.get("modRootPath", "")
            if mod_root:
                folder     = PER_VARIATION_KEYS[key]
                variations = detect_variations(mod_root, folder)
                self.detected_variations[key] = variations

        if not variations:
            ctk.CTkLabel(body, text="⚠  No variations detected. Set Mod Root Folder first.",
                         text_color="#FF6B35", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=4)
            self._build_variation_run_buttons(body, key)
            return

        hdr = ctk.CTkFrame(body, fg_color="transparent")
        hdr.pack(fill="x", pady=(2,0))
        ctk.CTkLabel(hdr, text="Variation", width=160, font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text="Mode",      width=160, font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text="%",         width=60,  font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side="left")

        for var_name in variations:
            self._build_variation_row(body, key, var_name)
        self._build_variation_run_buttons(body, key)

    def _build_variation_row(self, parent, key, var_name):
        row = ctk.CTkFrame(parent, fg_color="#2a2a2a", corner_radius=6)
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=var_name, width=160, font=ctk.CTkFont(size=11), anchor="w").pack(side="left", padx=(8,0))

        mode_var = ctk.StringVar(value="percent")
        rf = ctk.CTkFrame(row, fg_color="transparent", width=160)
        rf.pack(side="left")
        ctk.CTkRadioButton(rf, text="%", variable=mode_var, value="percent", width=45,
                           font=ctk.CTkFont(size=11),
                           command=lambda k=key, v=var_name: self._toggle_var_mode(k, v)
                           ).pack(side="left", padx=(4,2))
        ctk.CTkRadioButton(rf, text="Manual", variable=mode_var, value="manual", width=70,
                           font=ctk.CTkFont(size=11),
                           command=lambda k=key, v=var_name: self._toggle_var_mode(k, v)
                           ).pack(side="left", padx=(0,4))

        pct_var   = ctk.IntVar(value=0)
        pct_entry = ctk.CTkEntry(row, textvariable=pct_var, width=50, font=ctk.CTkFont(size=11))
        pct_entry.pack(side="left", padx=4)
        pct_var.trace_add("write", lambda *_, k=key, v=var_name: self._check_variation_pct(k, v))

        manual_frame = ctk.CTkFrame(row, fg_color="transparent")
        manual_ids   = []
        ctk.CTkButton(manual_frame, text="+ Add", width=70, height=24, font=ctk.CTkFont(size=11),
                      command=lambda k=key, v=var_name: self._add_variation_player(k, v)
                      ).pack(side="left", padx=(0,3))
        ctk.CTkButton(manual_frame, text="- Remove", width=80, height=24,
                      fg_color="#7a1a1a", font=ctk.CTkFont(size=11),
                      command=lambda k=key, v=var_name: self._remove_variation_player(k, v)
                      ).pack(side="left", padx=(0,3))
        man_lbl = ctk.CTkLabel(manual_frame, text="0", font=ctk.CTkFont(size=11), text_color="gray")
        man_lbl.pack(side="left")
        manual_frame.pack_forget()

        warn_lbl = ctk.CTkLabel(row, text="⚠ 100% — ALL eligible players",
                                text_color="#FF6B35", font=ctk.CTkFont(size=10))

        self.variation_widgets[key][var_name] = {
            "mode_var"     : mode_var,
            "pct_var"      : pct_var,
            "pct_entry"    : pct_entry,
            "manual_frame" : manual_frame,
            "manual_ids"   : manual_ids,
            "man_lbl"      : man_lbl,
            "warn_lbl"     : warn_lbl,
        }

    def _build_variation_run_buttons(self, parent, key):
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", pady=(4,2))
        btn_dry = ctk.CTkButton(btn_row, text="Dry Run", width=90, height=26,
                                fg_color="#1a4a7a", font=ctk.CTkFont(size=11),
                                command=lambda k=key: self._run_section(k, dry_run=True))
        btn_dry.pack(side="left", padx=(0,5))
        btn_apply = ctk.CTkButton(btn_row, text="Apply", width=90, height=26,
                                  fg_color="#1a7a1a", font=ctk.CTkFont(size=11),
                                  command=lambda k=key: self._run_section(k, dry_run=False))
        btn_apply.pack(side="left")
        self.mod_widgets[key]["btn_var_dry"]   = btn_dry
        self.mod_widgets[key]["btn_var_apply"] = btn_apply

    def _toggle_var_mode(self, key, var_name):
        vw = self.variation_widgets[key].get(var_name)
        if not vw: return
        if vw["mode_var"].get() == "percent":
            vw["manual_frame"].pack_forget()
            vw["pct_entry"].pack(side="left", padx=4)
        else:
            vw["pct_entry"].pack_forget()
            vw["manual_frame"].pack(side="left", padx=4)

    def _check_variation_pct(self, key, var_name):
        try:
            vw = self.variation_widgets[key].get(var_name)
            if not vw: return
            if vw["pct_var"].get() >= 100:
                vw["warn_lbl"].pack(side="left", padx=(4,0))
            else:
                vw["warn_lbl"].pack_forget()
        except Exception:
            pass

    def _add_variation_player(self, key, var_name):
        self._player_search_dialog(on_confirm=lambda pid, name: self._confirm_add_variation(key, var_name, pid))

    def _confirm_add_variation(self, key, var_name, pid):
        vw = self.variation_widgets[key][var_name]
        if pid not in vw["manual_ids"]: vw["manual_ids"].append(pid)
        vw["man_lbl"].configure(text=f"{len(vw['manual_ids'])}")

    def _remove_variation_player(self, key, var_name):
        vw = self.variation_widgets[key][var_name]
        self._delete_player_dialog(
            player_list=vw["manual_ids"],
            on_done=lambda: vw["man_lbl"].configure(text=f"{len(vw['manual_ids'])}"),
            title=f"Remove Player from {var_name}"
        )

    def _has_any_100_variation(self, key):
        hits = []
        for var_name, vw in self.variation_widgets[key].items():
            if vw["mode_var"].get() == "percent":
                try:
                    if vw["pct_var"].get() >= 100: hits.append(var_name)
                except Exception: pass
        return hits

    # ── standard mode toggle ──────────────────────────────────────────────────

    def _toggle_mode(self, key):
        w = self.mod_widgets[key]
        if w["mode_var"].get() == "percent":
            w["manual_frame"].pack_forget()
            w["pct_frame"].pack(side="left")
        else:
            w["pct_frame"].pack_forget()
            w["manual_frame"].pack(side="left")

    def _add_manual_player(self, key):
        self._player_search_dialog(on_confirm=lambda pid, name: self._confirm_add_to_mod(key, pid, name))

    def _confirm_add_to_mod(self, key, pid, name):
        w = self.mod_widgets[key]
        if pid not in w["manual_ids"]: w["manual_ids"].append(pid)
        w["manual_lbl"].configure(text=f"{len(w['manual_ids'])} player(s)")

    # ── handtape section ──────────────────────────────────────────────────────

    def _build_handtape_section(self, parent):
        frame = ctk.CTkFrame(parent, border_width=2, border_color="#8B4513")
        frame.pack(fill="x", padx=5, pady=(10,4))
        ctk.CTkLabel(frame, text="Handtape (Manual Only)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=8, pady=(6,2))
        ctk.CTkLabel(frame,
            text="⚠  WARNING: Do not use for players with in-game arm tattoos — it will overwrite them.",
            text_color="#FF6B35", font=ctk.CTkFont(size=11), wraplength=480, justify="left"
        ).pack(anchor="w", padx=8, pady=(0,6))

        pid_row = ctk.CTkFrame(frame, fg_color="transparent")
        pid_row.pack(fill="x", padx=8, pady=(0,4))
        ctk.CTkButton(pid_row, text="+ Add Player", width=120, command=self._ht_add_player).pack(side="left", padx=(0,8))
        self.ht_players_lbl = ctk.CTkLabel(pid_row, text="No players added", font=ctk.CTkFont(size=11), text_color="gray")
        self.ht_players_lbl.pack(side="left", padx=8, fill="x", expand=True)
        ctk.CTkButton(pid_row, text="Clear", width=60, fg_color="gray40", command=self._ht_clear_players).pack(side="right", padx=(4,0))
        ctk.CTkButton(pid_row, text="- Remove", width=90, fg_color="#7a1a1a", command=self._ht_delete_player).pack(side="right")

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

    def _choose_appearance_csv(self):
        path = filedialog.askopenfilename(title="Select PESEditor Appearance CSV",
                                          filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if path:
            self.appearance_csv_path = path
            self.lbl_appearance.configure(text=os.path.basename(path), text_color="lightgreen")
            self.cfg["appearanceCsvPath"] = path
            save_config(self.cfg)

    def _ht_add_player(self):
        self._player_search_dialog(on_confirm=lambda pid, name: self._confirm_add_ht(pid, name))

    def _confirm_add_ht(self, pid, name):
        if pid not in self.ht_players: self.ht_players.append(pid)
        self._refresh_ht_label()

    def _ht_clear_players(self):
        self.ht_players.clear()
        self._refresh_ht_label()

    def _ht_delete_player(self):
        self._delete_player_dialog(player_list=self.ht_players, on_done=self._refresh_ht_label,
                                   title="Remove Handtape Player")

    def _refresh_ht_label(self):
        count = len(self.ht_players)
        if count == 0:
            self.ht_players_lbl.configure(text="No players added", text_color="gray")
        else:
            names = [self.id_to_name.get(pid, pid) for pid in self.ht_players[-3:]]
            self.ht_players_lbl.configure(text=f"{count} player(s): {', '.join(names)}", text_color="lightgreen")

    # ── player dialogs ────────────────────────────────────────────────────────

    def _delete_player_dialog(self, player_list, on_done, title="Remove Player"):
        if not player_list:
            messagebox.showinfo("No Players", "No players to remove.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("420x360")
        dialog.grab_set()
        dialog.focus()
        ctk.CTkLabel(dialog, text="Select a player to remove:", font=ctk.CTkFont(size=13)).pack(pady=(14,8))
        scroll = ctk.CTkScrollableFrame(dialog, height=220)
        scroll.pack(fill="x", padx=16, pady=(0,8))
        selected = {"pid": None, "btn": None}
        confirm_btn_ref = {}

        def select(pid, btn):
            if selected["btn"]: selected["btn"].configure(fg_color="transparent")
            selected["pid"] = pid
            selected["btn"] = btn
            btn.configure(fg_color="#7a1a1a")
            confirm_btn_ref["btn"].configure(state="normal")

        for pid in list(player_list):
            name  = self.id_to_name.get(pid, "")
            label = f"{pid}  —  {name}" if name else pid
            btn   = ctk.CTkButton(scroll, text=label, anchor="w", fg_color="transparent",
                                  hover_color="#5a1a1a", font=ctk.CTkFont(size=12))
            btn.configure(command=lambda p=pid, b=btn: select(p, b))
            btn.pack(fill="x", pady=1)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=(4,12))

        def do_remove():
            pid = selected["pid"]
            if pid and pid in player_list: player_list.remove(pid)
            on_done()
            dialog.destroy()

        confirm_btn = ctk.CTkButton(btn_row, text="Remove Player", width=140,
                                    fg_color="#7a1a1a", state="disabled", command=do_remove)
        confirm_btn.pack(side="left", padx=(0,10))
        confirm_btn_ref["btn"] = confirm_btn
        ctk.CTkButton(btn_row, text="Cancel", width=100, fg_color="gray40",
                      command=dialog.destroy).pack(side="left")

    def _player_search_dialog(self, on_confirm):
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
        btn_refs  = []

        def do_search(*_):
            for w in result_box.winfo_children(): w.destroy()
            btn_refs.clear()
            selected["pid"] = None; selected["name"] = None
            confirm_btn.configure(state="disabled")
            query = search_var.get().strip()
            if not query: return
            results = []
            if query.isdigit():
                pid  = query
                name = self.id_to_name.get(pid, "")
                if name: results = [(pid, name)]
                elif pid in self.id_to_name: results = [(pid, "")]
                else: status_lbl.configure(text="No player found with that ID.")
            else:
                q       = query.lower()
                results = [(pid, name) for pid, name in self.id_to_name.items() if q in name.lower()]
                results = sorted(results, key=lambda x: x[1])[:50]
                if not results: status_lbl.configure(text="No players found matching that name.")
                else: status_lbl.configure(text=f"{len(results)} result(s) — click to select")
            for pid, name in results:
                lbl = f"{pid}  —  {name}" if name else pid
                btn = ctk.CTkButton(result_box, text=lbl, anchor="w", fg_color="transparent",
                                    hover_color="#2a4a6a", font=ctk.CTkFont(size=12),
                                    command=lambda p=pid, n=name: select_player(p, n))
                btn.pack(fill="x", pady=1)
                btn_refs.append(btn)

        def select_player(pid, name):
            selected["pid"] = pid; selected["name"] = name
            display = f"{name}  (ID: {pid})" if name else f"ID: {pid}"
            status_lbl.configure(text=f"Selected: {display}", text_color="lightgreen")
            confirm_btn.configure(state="normal")

        search_var.trace_add("write", do_search)
        entry.bind("<Return>", do_search)
        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=(4,12))
        confirm_btn = ctk.CTkButton(btn_row, text="Add Player", width=130, state="disabled",
                                    fg_color="#1a7a1a",
                                    command=lambda: [on_confirm(selected["pid"], selected["name"]), dialog.destroy()])
        confirm_btn.pack(side="left", padx=(0,10))
        ctk.CTkButton(btn_row, text="Cancel", width=100, fg_color="gray40",
                      command=dialog.destroy).pack(side="left")

    # ── file choosers ─────────────────────────────────────────────────────────

    def _choose_mod_root(self):
        path = filedialog.askdirectory(title="Select Mod Root Folder")
        if path:
            self.lbl_root.configure(text=path, text_color="lightgreen")
            self.cfg["modRootPath"] = path
            save_config(self.cfg)
            self._log(f"Mod root set: {path}")
            self._detect_all_variations(path)

    def _detect_all_variations(self, mod_root):
        for key, folder in PER_VARIATION_KEYS.items():
            variations = detect_variations(mod_root, folder)
            self.detected_variations[key] = variations
            if variations:
                self._log(f"  [{MOD_LABELS[key]}] {len(variations)} variation(s): {', '.join(variations)}")
            else:
                self._log(f"  [{MOD_LABELS[key]}] No variations detected")
            w = self.mod_widgets.get(key)
            if w and w["variation_toggle_var"] and w["variation_toggle_var"].get():
                self._rebuild_variation_rows(key)

        for key, info in GROUPED_SECTIONS.items():
            variations = detect_grouped_variations(mod_root, info["folder_prefix"], info.get("exclude_folders"))
            self.detected_grouped[key] = variations
            if variations:
                self._log(f"  [{info['label']}] {len(variations)} variation(s): {', '.join(l for l,_ in variations)}")
            else:
                self._log(f"  [{info['label']}] No variations detected")
            gw = self.grouped_widgets.get(key)
            if gw and gw["toggle_var"].get():
                self._rebuild_grouped_rows(key)

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
                self.cfg["dbPath"] = path
                save_config(self.cfg)
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ── settings ──────────────────────────────────────────────────────────────

    def _load_ui_from_config(self):
        root = self.cfg.get("modRootPath", "")
        if root:
            self.lbl_root.configure(text=root, text_color="lightgreen")
            self._detect_all_variations(root)

        # Restore DB file path
        db_path = self.cfg.get("dbPath", "")
        if db_path and os.path.isfile(db_path):
            try:
                ids, names = parse_db_file_with_names(db_path)
                self.id_to_name = names
                if ids:
                    write_player_ids_csv(ids)
                    self.player_ids = ids
                    self._db_path   = db_path
                    ext = os.path.splitext(db_path)[1].lower()
                    fmt = "FL26 TXT" if ext == ".txt" else "CSV"
                    self.lbl_db.configure(text=os.path.basename(db_path), text_color="lightgreen")
                    self.lbl_db_count.configure(text=f"{fmt} | {len(ids):,} players")
            except Exception:
                pass

        # Restore appearance CSV path
        app_path = self.cfg.get("appearanceCsvPath", "")
        if app_path and os.path.isfile(app_path):
            self.appearance_csv_path = app_path
            self.lbl_appearance.configure(text=os.path.basename(app_path), text_color="lightgreen")

        mods = self.cfg.get("mods", {})
        for key, w in self.mod_widgets.items():
            mod = mods.get(key, {})
            if "enabled" in mod: w["enabled_var"].set(mod["enabled"])
            w["pct_var"].set(0)
            # manual IDs intentionally not loaded — cleared after each run
            if w["variation_toggle_var"] and mod.get("perVariationMode", False):
                w["variation_toggle_var"].set(True)
                self._toggle_variation_mode(key)

        grouped_cfg = self.cfg.get("grouped", {})
        for key, gw in self.grouped_widgets.items():
            grp = grouped_cfg.get(key, {})
            if "enabled" in grp: gw["enabled_var"].set(grp["enabled"])
            gw["pct_var"].set(0)
            if grp.get("perVariationMode", False):
                gw["toggle_var"].set(True)
                self._toggle_grouped_mode(key)

    def _save_settings(self):
        mods = self.cfg.setdefault("mods", {})
        for key, w in self.mod_widgets.items():
            mod = mods.setdefault(key, {})
            mod["enabled"]         = w["enabled_var"].get()
            mod["percent"]         = w["pct_var"].get()
            mod["manualPlayerIds"] = w["manual_ids"]
            if w["variation_toggle_var"]:
                per_var = w["variation_toggle_var"].get()
                mod["perVariationMode"] = per_var
                if per_var:
                    var_cfg = {}
                    for var_name, vw in self.variation_widgets[key].items():
                        var_cfg[var_name] = {
                            "mode"      : vw["mode_var"].get(),
                            "percent"   : vw["pct_var"].get(),
                            "manualIds" : vw["manual_ids"],
                        }
                    mod["variationSettings"] = var_cfg

        grouped = self.cfg.setdefault("grouped", {})
        for key, gw in self.grouped_widgets.items():
            grp = grouped.setdefault(key, {})
            grp["enabled"]         = gw["enabled_var"].get()
            grp["percent"]         = gw["pct_var"].get()
            grp["manualPlayerIds"] = gw["manual_ids"]
            per_var = gw["toggle_var"].get()
            grp["perVariationMode"] = per_var
            if per_var:
                var_cfg = {}
                for label, vw in gw["variations"].items():
                    var_cfg[label] = {
                        "folder_name" : vw["folder_name"],
                        "mode"        : vw["mode_var"].get(),
                        "percent"     : vw["pct_var"].get(),
                        "manualIds"   : vw["manual_ids"],
                    }
                grp["variationSettings"] = var_cfg

        # Save DB and appearance paths
        if self._db_path:
            self.cfg["dbPath"] = self._db_path
        if self.appearance_csv_path:
            self.cfg["appearanceCsvPath"] = self.appearance_csv_path

        save_config(self.cfg)
        self._log("Settings saved.")

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

    # ── button state ──────────────────────────────────────────────────────────

    def _set_all_buttons(self, state):
        self.btn_dry.configure(state=state)
        self.btn_run.configure(state=state)
        for w in self.mod_widgets.values():
            w["btn_sec_dry"].configure(state=state)
            w["btn_sec_apply"].configure(state=state)
            if w.get("btn_var_dry"):   w["btn_var_dry"].configure(state=state)
            if w.get("btn_var_apply"): w["btn_var_apply"].configure(state=state)
        for gw in self.grouped_widgets.values():
            gw["btn_dry"].configure(state=state)
            gw["btn_apply"].configure(state=state)

    # ── run: standard section ─────────────────────────────────────────────────

    def _clear_all_manual_ids(self):
        """Clear all manual player lists after a run — UI and config."""
        for key, w in self.mod_widgets.items():
            w["manual_ids"].clear()
            w["manual_lbl"].configure(text="0 players")
        for key, gw in self.grouped_widgets.items():
            gw["manual_ids"].clear()
            gw["manual_lbl"].configure(text="0 players")
            for vw in gw["variations"].values():
                vw["manual_ids"].clear()
                vw["man_lbl"].configure(text="0")
        for vw_dict in self.variation_widgets.values():
            for vw in vw_dict.values():
                vw["manual_ids"].clear()
                vw["man_lbl"].configure(text="0")
        self.ht_players.clear()
        self._refresh_ht_label()
        # Also clear from saved config so they don't reload on next launch
        for mod in self.cfg.get("mods", {}).values():
            mod.pop("manualPlayerIds", None)
        for grp in self.cfg.get("grouped", {}).values():
            grp.pop("manualPlayerIds", None)
            for vs in grp.get("variationSettings", {}).values():
                vs.pop("manualIds", None)
        save_config(self.cfg)

    def _run_section(self, key, dry_run=False):
        self._save_settings()
        root = self.cfg.get("modRootPath", "")
        if not root or not os.path.isdir(root):
            messagebox.showwarning("Missing Folder", "Please select a Mod Root Folder first.")
            return
        if not os.path.exists(PLAYERID_CSV):
            messagebox.showwarning("Missing DB", "Please select a Player DB file first.")
            return
        w = self.mod_widgets[key]
        if w["variation_toggle_var"] and w["variation_toggle_var"].get():
            hits = self._has_any_100_variation(key)
            if hits and not dry_run:
                if not messagebox.askyesno("⚠ 100% Assignment Warning",
                    f"Variations set to 100%:\n\n  {', '.join(hits)}\n\nEVERY eligible player will be assigned. Continue?"):
                    return
        if not dry_run:
            if not messagebox.askyesno("Confirm Apply",
                f"This will COPY folders for {MOD_LABELS[key]}.\n\nContinue?"):
                return
        mode       = "DryRun" if dry_run else "Run"
        mode_label = f"{'Dry Run' if dry_run else 'Apply'}: {MOD_LABELS[key]}"
        is_real    = not dry_run
        self._set_all_buttons("disabled")
        self.lbl_status.configure(text=f"Status: {mode_label}...")

        def run():
            script = os.path.join(PACKAGE_DIR, "Run-FL26-ModAutomation.ps1")
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-File", script, "-Mode", mode, "-ConfigPath", CONFIG_PATH, "-SingleMod", key]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW,
                                        text=True, encoding="utf-8", errors="replace")
                for line in proc.stdout:
                    self.after(0, self._log, line.rstrip())
                proc.wait()
                self.after(0, self._set_all_buttons, "normal")
                if proc.returncode == 0:
                    if is_real: self.after(0, self._clear_all_manual_ids)
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

    # ── run: grouped section ──────────────────────────────────────────────────

    def _run_grouped(self, key, dry_run=False):
        self._save_settings()
        root = self.cfg.get("modRootPath", "")
        if not root or not os.path.isdir(root):
            messagebox.showwarning("Missing Folder", "Please select a Mod Root Folder first.")
            return
        if not os.path.exists(PLAYERID_CSV):
            messagebox.showwarning("Missing DB", "Please select a Player DB file first.")
            return
        gw = self.grouped_widgets[key]
        if gw["toggle_var"].get():
            hits = self._has_any_100_grouped(key)
            if hits and not dry_run:
                if not messagebox.askyesno("⚠ 100% Assignment Warning",
                    f"Variations set to 100%:\n\n  {', '.join(hits)}\n\nEVERY eligible player will be assigned. Continue?"):
                    return
        if not dry_run:
            if not messagebox.askyesno("Confirm Apply",
                f"This will COPY folders for {GROUPED_SECTIONS[key]['label']}.\n\nContinue?"):
                return
        mode       = "DryRun" if dry_run else "Run"
        mode_label = f"{'Dry Run' if dry_run else 'Apply'}: {GROUPED_SECTIONS[key]['label']}"
        is_real    = not dry_run
        self._set_all_buttons("disabled")
        self.lbl_status.configure(text=f"Status: {mode_label}...")

        def run():
            script = os.path.join(PACKAGE_DIR, "Run-FL26-ModAutomation.ps1")
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-File", script, "-Mode", mode, "-ConfigPath", CONFIG_PATH, "-SingleMod", key]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW,
                                        text=True, encoding="utf-8", errors="replace")
                for line in proc.stdout:
                    self.after(0, self._log, line.rstrip())
                proc.wait()
                self.after(0, self._set_all_buttons, "normal")
                if proc.returncode == 0:
                    if is_real: self.after(0, self._clear_all_manual_ids)
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
        warnings = []
        for key, w in self.mod_widgets.items():
            if w["variation_toggle_var"] and w["variation_toggle_var"].get():
                hits = self._has_any_100_variation(key)
                if hits: warnings.append(f"{MOD_LABELS[key]}: {', '.join(hits)}")
        for key, gw in self.grouped_widgets.items():
            if gw["toggle_var"].get():
                hits = self._has_any_100_grouped(key)
                if hits: warnings.append(f"{GROUPED_SECTIONS[key]['label']}: {', '.join(hits)}")
        if warnings:
            warn_text = "\n".join(f"  • {w}" for w in warnings)
            if not messagebox.askyesno("⚠ 100% Assignment Warning",
                f"The following variations are set to 100%:\n\n{warn_text}\n\nEVERY eligible player will be assigned. Continue?"):
                return
        if not messagebox.askyesno("Confirm RUN ALL", "This will COPY folders for ALL enabled mods.\n\nContinue?"):
            return
        self._execute("Run")

    def _execute(self, mode):
        root = self.cfg.get("modRootPath", "")
        if not root or not os.path.isdir(root):
            messagebox.showwarning("Missing Folder", "Please select a Mod Root Folder first.")
            return
        if not os.path.exists(PLAYERID_CSV):
            messagebox.showwarning("Missing DB", "Please select a Player DB file first.")
            return
        is_real = (mode == "Run")
        self._set_all_buttons("disabled")
        self.lbl_status.configure(text=f"Status: Running {mode}...")

        def run():
            script = os.path.join(PACKAGE_DIR, "Run-FL26-ModAutomation.ps1")
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-File", script, "-Mode", mode, "-ConfigPath", CONFIG_PATH]
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW,
                                        text=True, encoding="utf-8", errors="replace")
                for line in proc.stdout:
                    self.after(0, self._log, line.rstrip())
                proc.wait()
                self.after(0, self._set_all_buttons, "normal")
                if proc.returncode == 0:
                    if is_real: self.after(0, self._clear_all_manual_ids)
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
        root    = self.cfg.get("modRootPath", "")
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
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                   "-File", script,
                   "-AppearanceCsvPath", self.appearance_csv_path,
                   "-RootPath", ht_root,
                   "-PlayerIdsPipe", ids_pipe,
                   "-HandsPipe", hands_pipe]
            if dry_run: cmd.append("-DryRun")
            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW,
                                        text=True, encoding="utf-8", errors="replace")
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
