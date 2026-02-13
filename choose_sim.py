#!/usr/bin/env python3
"""
Interactive launcher that runs either:
  • Full Predation/Speciation (evo_sim) — UI, then analyze *that session only*
  • Natural Selection 2.0    (ns_sim_2_0) — UI, then analyze *that session only*

You can run it fully interactive (just `python choose_sim.py`) or non-interactively:
  python choose_sim.py --mode full --tag demo
  python choose_sim.py --mode ns   --tag demo

Notes:
- For NS mode, make sure your package folder is named:  ns_sim_2_0
  and the UI entry is:                               ns_sim_2_0.main
"""

import argparse
import subprocess
import sys
import os
import csv
from pathlib import Path

# --------------- helpers ---------------

def prompt_choice(prompt, options, default=None):
    opts_str = "/".join(options)
    dstr = f" [{default}]" if default else ""
    while True:
        val = input(f"{prompt} ({opts_str}){dstr}: ").strip().lower()
        if not val and default:
            return default
        for opt in options:
            if val == opt.lower():
                return opt
        print(f"Please enter one of: {opts_str}")

def prompt_str(prompt, default=""):
    s = input(f"{prompt} [{default}]: ").strip()
    return s if s else default

def latest_session_id(overall_csv_path: str) -> str | None:
    """Return the last session_id in file order from a UI daily CSV."""
    p = Path(overall_csv_path)
    if not p.exists():
        return None
    last_sid = None
    with p.open(newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            sid = row.get("session_id")
            if sid:
                last_sid = sid
    return last_sid

def run_and_analyze(ui_cmd: list[str], overall_csv: str, species_csv: str, outdir: str, tag: str):
    # 1) Run UI (blocks until window closes)
    print("[launcher] Starting UI:", " ".join(ui_cmd))
    ret = subprocess.call(ui_cmd)
    if ret != 0:
        print(f"[launcher] UI exited with code {ret}", file=sys.stderr)

    # 2) Analyze *that* session only
    sid = latest_session_id(overall_csv)
    if not sid:
        print(f"[launcher] Could not resolve latest session_id from {overall_csv}; did a day complete?")
        sys.exit(0)

    ana_cmd = [
        sys.executable, "analyze_ui_csv.py",
        "--overall", overall_csv,
        "--species", species_csv,
        "--outdir", outdir,
        "--tag", tag,
        "--session", sid
    ]
    print("\n[launcher] Analyzing session:", sid)
    print("[launcher] Running:", " ".join(ana_cmd))
    sys.exit(subprocess.call(ana_cmd))

# --------------- main ---------------

def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--mode", choices=["full", "ns"], default=None,
                    help="full = evo_sim UI; ns = ns_sim_2_0 UI")
    ap.add_argument("--tag", type=str, default="")
    ap.add_argument("--outdir", type=str, default="reports")
    # Let users pass additional args to the UI modules if they like:
    args, passthru = ap.parse_known_args()

    print("=== Choose Simulation Mode ===")
    mode = args.mode or prompt_choice("Run which sim?", ["full", "ns"], default="full")
    tag = args.tag or prompt_str("Optional tag for reports (e.g., demo)", "")
    outdir = args.outdir

    if mode == "full":
        # FULL (evo_sim) — UI then analyze
        ui_cmd = [sys.executable, "-m", "evo_sim.main", "--ui", *passthru]
        overall_csv = "runs/ui_daily.csv"
        species_csv = "runs/ui_species_daily.csv"
        return run_and_analyze(ui_cmd, overall_csv, species_csv, outdir, tag)

    else:
        # NS (ns_sim_2_0) — UI then analyze
        # Make sure your NS UI logger writes to runs_ns/* (as we set up in the NS UI app)
        ui_cmd = [sys.executable, "-m", "ns_sim_2_0.main", "--ui", *passthru]
        overall_csv = "runs_ns/ui_daily.csv"
        species_csv = "runs_ns/ui_species_daily.csv"
        return run_and_analyze(ui_cmd, overall_csv, species_csv, outdir, tag)

if __name__ == "__main__":
    main()