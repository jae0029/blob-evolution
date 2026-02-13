#!/usr/bin/env python3
"""
Analyze UI CSVs produced by DailyCsvLogger.

Per-run folders:
  - If --session is provided (or 'latest' resolved), outputs go to:  <outdir>/<session_id>/
  - Else, outputs go to:                                           <outdir>/<timestamp>/

Plots:
  Overall (one PNG):
    (1) ONLY Total N + per-species N
    (2) Avg speed & Avg size
    (3) Avg sense
  Species (one PNG per species):
    (1) ONLY species N
    (2) Avg speed & Avg size
    (3) Avg sense

CSV exports:
  overall_summary_<timestamp>__<tag>.csv
  species_summary_<timestamp>__<tag>.csv
"""
import argparse
import os
import sys
import time
import pandas as pd

# Headless plotting
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ------------------------- utilities -------------------------
def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def timestamp(tag: str | None = None) -> str:
    t = time.strftime("%Y%m%d_%H%M%S")
    return f"{t}__{tag}" if tag else t

def exists(path: str | None) -> bool:
    return bool(path and os.path.exists(path))


# ------------------------- loading ---------------------------
def load_csvs(overall_path: str, species_path: str | None):
    if not exists(overall_path):
        print(
            "\n[ERROR] Overall CSV not found.\n"
            f"  Expected: {overall_path}\n"
            "Hints:\n"
            "  • Run the UI until at least one day completes (Day 1 → 2).\n"
            "  • Confirm the logger paths in evo_sim/ui/app.py match these args.\n",
            file=sys.stderr
        )
        sys.exit(1)

    df_overall = pd.read_csv(overall_path)
    df_species = pd.read_csv(species_path) if (species_path and exists(species_path)) else None
    return df_overall, df_species


def _latest_session_id(df: pd.DataFrame) -> str | None:
    """Return the last session_id in file order (used by --session latest)."""
    if "session_id" not in df.columns or len(df) == 0:
        return None
    s = df["session_id"].dropna()
    return s.iloc[-1] if len(s) else None


# ------------------------- plotting --------------------------
def plot_overall(df_overall: pd.DataFrame,
                 df_species: pd.DataFrame | None,
                 outdir: str,
                 tag: str | None):
    """
    (1) ONLY Total N + per‑species N
    (2) Avg speed & Avg size
    (3) Avg sense
    """
    ensure_dir(outdir)
    fig, ax = plt.subplots(3, 1, figsize=(10, 11), sharex=True)

    # (1) Total N + per-species N
    g_overall = df_overall.copy()
    for col in ("day", "n"):
        if col in g_overall.columns:
            g_overall[col] = pd.to_numeric(g_overall[col], errors="coerce")

    if "session_id" in g_overall.columns:
        g_overall = g_overall.groupby("day", as_index=False)["n"].mean()

    if {"day", "n"} <= set(g_overall.columns):
        ax[0].plot(g_overall["day"], g_overall["n"],
                   label="Total N", color="black", linewidth=2.25)

    if df_species is not None and len(df_species) > 0:
        dfs = df_species.copy()
        for col in ("day", "n"):
            if col in dfs.columns:
                dfs[col] = pd.to_numeric(dfs[col], errors="coerce")

        has_sid = "species_id" in dfs.columns
        has_sname = "species_name" in dfs.columns
        group_keys = []
        if has_sid:   group_keys.append("species_id")
        if has_sname: group_keys.append("species_name")
        group_keys.append("day")

        try:
            g_species = dfs.groupby(group_keys, as_index=False)["n"].mean()
            species_keys = (["species_id", "species_name"] if (has_sid and has_sname)
                            else (["species_id"] if has_sid else ["species_name"]))
            for spec_key, sub in g_species.groupby(species_keys):
                label = ("N — " + " ".join(str(v) for v in spec_key if not isinstance(spec_key, float))) \
                        if isinstance(spec_key, tuple) else f"N — {spec_key}"
                ax[0].plot(sub["day"], sub["n"], linewidth=1.6, label=label)
        except Exception as e:
            print(f"[WARN] Skipping per-species N overlay: {e}", file=sys.stderr)

    ax[0].set_ylabel("Count")
    ax[0].legend(loc="best", ncols=2)
    ax[0].grid(alpha=0.25)

    # (2) Avg speed & Avg size
    if "avg_speed" in df_overall.columns:
        ax[1].plot(df_overall["day"], df_overall["avg_speed"], label="Avg speed")
    if "avg_size" in df_overall.columns:
        ax[1].plot(df_overall["day"], df_overall["avg_size"],  label="Avg size")
    ax[1].set_ylabel("Trait value")
    ax[1].legend(loc="best")
    ax[1].grid(alpha=0.25)

    # (3) Avg sense
    if "avg_sense" in df_overall.columns:
        ax[2].plot(df_overall["day"], df_overall["avg_sense"],
                   color="tab:purple", label="Avg sense")
    ax[2].set_xlabel("Day")
    ax[2].set_ylabel("Sense")
    ax[2].legend(loc="best")
    ax[2].grid(alpha=0.25)

    fig.tight_layout()
    png = os.path.join(outdir, f"overall_trends_{timestamp(tag)}.png")
    fig.savefig(png, dpi=160)
    plt.close(fig)
    print(f"[OK] Saved {png}")


def plot_species(df_species: pd.DataFrame, outdir: str, tag: str | None):
    """Species figures: N only (top), Speed&Size, Sense."""
    if df_species is None or len(df_species) == 0:
        print("[INFO] No species CSV provided or rows = 0; skipping per‑species plots.")
        return

    needed = {"day", "n"}
    if not needed.issubset(df_species.columns):
        print(f"[WARN] df_species missing required columns {needed - set(df_species.columns)}; skipping species plots.")
        return

    for col in ("day", "n", "avg_speed", "avg_size", "avg_sense"):
        if col in df_species.columns:
            df_species[col] = pd.to_numeric(df_species[col], errors="coerce")

    group_key = "species_id" if "species_id" in df_species.columns else (
                "species_name" if "species_name" in df_species.columns else None)
    if group_key is None:
        print("[WARN] No species identifier column (species_id/species_name); skipping species plots.")
        return

    for key, sub in df_species.groupby(group_key):
        agg = {"n": "mean"}
        if "avg_speed" in sub.columns: agg["avg_speed"] = "mean"
        if "avg_size"  in sub.columns: agg["avg_size"]  = "mean"
        if "avg_sense" in sub.columns: agg["avg_sense"] = "mean"

        sub_g = (sub.groupby("day", as_index=False)
                    .agg(agg)
                    .sort_values("day"))

        # Display name
        if "species_name" in sub.columns and pd.notna(sub["species_name"].iloc[0]):
            name = str(sub["species_name"].iloc[0])
        else:
            name = f"{group_key}={key}"

        fig, ax = plt.subplots(3, 1, figsize=(10, 11), sharex=True)

        # (1) ONLY N
        ax[0].plot(sub_g["day"], sub_g["n"], label=f"N — {name}", linewidth=2.0)
        ax[0].set_ylabel("Count")
        ax[0].legend(loc="best")
        ax[0].grid(alpha=0.25)

        # (2) Speed & Size
        drawn = False
        if "avg_speed" in sub_g.columns:
            ax[1].plot(sub_g["day"], sub_g["avg_speed"], label="Speed")
            drawn = True
        if "avg_size" in sub_g.columns:
            ax[1].plot(sub_g["day"], sub_g["avg_size"],  label="Size")
            drawn = True
        if drawn:
            ax[1].legend(loc="best")
        ax[1].set_ylabel("Trait value")
        ax[1].grid(alpha=0.25)

        # (3) Sense
        if "avg_sense" in sub_g.columns:
            ax[2].plot(sub_g["day"], sub_g["avg_sense"], color="tab:purple", label="Sense")
            ax[2].legend(loc="best")
        ax[2].set_xlabel("Day")
        ax[2].set_ylabel("Sense")
        ax[2].grid(alpha=0.25)

        fig.suptitle(f"Species {key} — {name}")
        fig.tight_layout()
        png = os.path.join(outdir, f"species_{key}_trends_{timestamp(tag)}.png")
        fig.savefig(png, dpi=160)
        plt.close(fig)
        print(f"[OK] Saved {png}")


# ------------------------- exports ---------------------------
def export_csv(df: pd.DataFrame, outdir: str, base: str, tag: str | None) -> str:
    ensure_dir(outdir)
    fname = f"{base}_{timestamp(tag)}.csv"
    path = os.path.join(outdir, fname)
    df.to_csv(path, index=False)
    print(f"[OK] Wrote {path}")
    return path


def clean_overall(df_overall: pd.DataFrame) -> pd.DataFrame:
    # Cast numerics
    for col in ("day","n","alive_end","ate0","ate1","ate2p",
                "avg_speed","avg_size","avg_sense","avg_metabolism",
                "food_per_day","day_steps"):
        if col in df_overall.columns:
            df_overall[col] = pd.to_numeric(df_overall[col], errors="coerce")

    if "session_id" in df_overall.columns:
        keep = [c for c in ("n","alive_end","ate0","ate1","ate2p",
                            "avg_speed","avg_size","avg_sense","avg_metabolism",
                            "food_per_day","day_steps") if c in df_overall.columns]
        d = df_overall.groupby("day", as_index=False)[keep].mean()
        return d.sort_values("day")
    return df_overall.sort_values("day") if "day" in df_overall.columns else df_overall.copy()


def clean_species(df_species: pd.DataFrame | None) -> pd.DataFrame:
    if df_species is None or len(df_species) == 0:
        return pd.DataFrame()
    for col in ("day","n","alive_end","ate0","ate1","ate2p",
                "avg_speed","avg_size","avg_sense","metabolism"):
        if col in df_species.columns:
            df_species[col] = pd.to_numeric(df_species[col], errors="coerce")
    keep = [c for c in ("n","alive_end","ate0","ate1","ate2p",
                        "avg_speed","avg_size","avg_sense","metabolism") if c in df_species.columns]
    keys = [k for k in ("species_id","species_name","day") if k in df_species.columns]
    d = df_species.groupby(keys, as_index=False)[keep].mean()
    return d.sort_values(keys)


# ------------------------- main ------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overall", type=str, default="runs/ui_daily.csv",
                    help="Path to overall daily CSV written by the UI")
    ap.add_argument("--species", type=str, default="runs/ui_species_daily.csv",
                    help="Path to per‑species daily CSV (pass '' to disable)")
    ap.add_argument("--outdir", type=str, default="reports",
                    help="Base output directory for plots and exported CSVs")
    ap.add_argument("--tag", type=str, default="",
                    help="Optional label to append to filenames (e.g., 'demo')")
    ap.add_argument("--session", type=str, default="",
                    help="Session ID to analyze; use 'latest' to pick the most recent session automatically.")
    args = ap.parse_args()

    df_overall_raw, df_species_raw = load_csvs(args.overall, args.species if args.species else None)

    # Filter by session if requested
    df_overall = df_overall_raw.copy()
    df_species = df_species_raw.copy() if df_species_raw is not None else None

    effective_outdir = args.outdir  # may change below

    if args.session:
        if "session_id" not in df_overall.columns:
            print("[WARN] --session provided but overall CSV has no session_id; ignoring.")
        else:
            sid = args.session
            if sid == "latest":
                sid = _latest_session_id(df_overall_raw)   # resolve from raw (unfiltered)
            if sid:
                # Filter frames
                df_overall = df_overall[df_overall["session_id"] == sid].copy()
                if df_species is not None and "session_id" in df_species.columns:
                    df_species = df_species[df_species["session_id"] == sid].copy()
                print(f"[OK] Filtering analysis to session_id={sid}")
                # -------- Outdir per session --------
                effective_outdir = os.path.join(args.outdir, sid)
                ensure_dir(effective_outdir)
                print(f"[INFO] Writing plots/CSVs under: {effective_outdir}")
            else:
                print("[WARN] Could not resolve latest session_id; analyzing all data.")

    # If still no per-session outdir (no --session), create a timestamped subfolder
    if effective_outdir == args.outdir:
        stamp_dir = time.strftime("%Y%m%d_%H%M%S")
        effective_outdir = os.path.join(args.outdir, stamp_dir)
        ensure_dir(effective_outdir)
        print(f"[INFO] No session filter; writing under timestamped folder: {effective_outdir}")

    print(f"[INFO] Overall rows after filter: {len(df_overall)}")
    if df_species is not None:
        print(f"[INFO] Species rows after filter: {len(df_species)}")

    # Export cleaned CSVs (to per-run folder)
    df_overall_clean = clean_overall(df_overall)
    export_csv(df_overall_clean, effective_outdir, base="overall_summary", tag=(args.tag or None))

    df_species_clean = clean_species(df_species)
    if args.species and args.species.strip() and len(df_species_clean) > 0:
        export_csv(df_species_clean, effective_outdir, base="species_summary", tag=(args.tag or None))

    # Plots (to per-run folder)
    plot_overall(df_overall, df_species, effective_outdir, tag=(args.tag or None))
    if args.species and args.species.strip() and df_species is not None and len(df_species) > 0:
        plot_species(df_species, effective_outdir, tag=(args.tag or None))
    else:
        print("[INFO] No per‑species rows to plot (after optional --session filter); skipping species plots.")

    print(f"\nDone. Outputs are in: {effective_outdir}")

if __name__ == "__main__":
    main()