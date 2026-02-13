#!/usr/bin/env python3
import argparse, subprocess, sys, os, csv

def get_latest_session_id(overall_path: str) -> str | None:
    if not os.path.exists(overall_path):
        return None
    # read last non-header row's session_id
    last_sid = None
    with open(overall_path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
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

    # 1) Run the UI. This blocks until you close the window.
    ui_cmd = [sys.executable, "-m", "evo_sim.main", "--ui"]
    print("[launcher] Starting UI:", " ".join(ui_cmd))
    ret = subprocess.call(ui_cmd)
    if ret != 0:
        print(f"[launcher] UI exited with code {ret}", file=sys.stderr)

    # 2) Resolve latest session_id from the UI CSV
    sid = get_latest_session_id(args.overall)
    if not sid:
        print("[launcher] No session_id found in overall CSV; maybe no day completed?")
        sys.exit(0)

    # 3) Run analysis for THIS session only
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