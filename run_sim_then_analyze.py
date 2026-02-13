#!/usr/bin/env python3
"""
One-shot runner:
  1) Launch UI (blocks until you close it)
  2) Analyze only the latest session from UI logs (or the one just produced)

Usage:
  python run_sim_then_analyze.py --outdir reports --tag demo
"""
import argparse
import subprocess
import sys
import os
import csv

def get_latest_session_id(overall_path: str) -> str | None:
    if not os.path.exists(overall_path):
        return None
    last_sid = None
    with open(overall_path, newline="") as f:
        for row in csv.DictReader(f):
            sid = row.get("session_id")
            if sid:
                last_sid = sid
    return last_sid

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overall", default="runs/ui_daily.csv")
    ap.add_argument("--species", default="runs/ui_species_daily.csv")
    ap.add_argument("--outdir", default="reports")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    # 1) Run the UI
    ui_cmd = [sys.executable, "-m", "evo_sim.main", "--ui"]
    print("[launcher] Starting UI:", " ".join(ui_cmd))
    ret = subprocess.call(ui_cmd)
    if ret != 0:
        print(f"[launcher] UI exited with code {ret}", file=sys.stderr)

    # 2) Resolve latest session_id
    sid = get_latest_session_id(args.overall)
    if not sid:
        print("[launcher] No session_id found in overall CSV; maybe no day completed yet?")
        sys.exit(0)

    # 3) Analyze only this session
    ana_cmd = [
        sys.executable, "analyze_ui_csv.py",
        "--overall", args.overall,
        "--species", args.species,
        "--outdir", args.outdir,
        "--tag", args.tag,
        "--session", sid
    ]
    print("[launcher] Analyzing session:", sid)
    print("[launcher] Running:", " ".join(ana_cmd))
    sys.exit(subprocess.call(ana_cmd))

if __name__ == "__main__":
    main()