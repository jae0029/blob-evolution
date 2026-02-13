#!/usr/bin/env python3
"""
Analyze UI CSVs produced by DailyCsvLogger.

Every run:
  - Saves plots under --outdir
  - Exports cleaned/aggregated CSVs with a fresh timestamp:
      overall_summary_<timestamp>[__<tag>].csv
      species_summary_<timestamp>[__<tag>].csv  (if --species provided)

Usage:
  python analyze_ui_csv.py --overall runs/ui_daily.csv \
                           --species runs/ui_species_daily.csv \
                           --outdir reports \
                           --tag optional_label
"""
import argparse, os, sys, time
import pandas as pd
import matplotlib.pyplot as plt

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def timestamp(tag: str | None = None) -> str:
    t = time.strftime("%Y%m%d_%H%M%S")
    return f"{t}__{tag}" if tag else t

def load_csvs(overall_path: str, species_path: str | None):
    if not overall_path or not os.path.exists(overall_path):
        print(
            "\n[ERROR] Overall CSV not found.\n"
            f"  Expected: {overall_path}\n"
            "  Hints:\n"
            "   • Run the UI long enough for at least one day to finish.\n"
            "   • Confirm logger paths in evo_sim/ui/app.py match these args.\n"
            "   • Default logger writes to runs/ui_daily.csv (and ui_species_daily.csv).\n",
            file=sys.stderr
        )
        sys.exit(1)

    df_overall = pd.read_csv(overall_path)

    df_species = None
    if species_path and species_path.strip():
        if os.path.exists(species_path):
            df_species = pd.read_csv(species_path)
        else:
            print(
                "[WARN] Species CSV path provided but not found; continuing without per‑species export/plots:\n"
                f"  {species_path}\n",
                file=sys.stderr
            )
            df_species = None
    return df_overall, df_species

def clean_overall(df_overall: pd.DataFrame) -> pd.DataFrame:
    # Cast numerics and keep expected columns if present
    num_cols = ("day","n","alive_end","ate0","ate1","ate2p",
                "avg_speed","avg_size","avg_sense","avg_metabolism",
                "food_per_day","day_steps")
    for col in num_cols:
        if col in df_overall.columns:
            df_overall[col] = pd.to_numeric(df_overall[col], errors="coerce")

    # If multiple sessions are combined, group per session/day (safe aggregation)
    if "session_id" in df_overall.columns:
        keys = ["session_id", "day"]
        agg = {
            "n":"mean","alive_end":"mean","ate0":"mean","ate1":"mean","ate2p":"mean",
            "avg_speed":"mean","avg_size":"mean","avg_sense":"mean","avg_metabolism":"mean",
            "food_per_day":"mean","day_steps":"mean"
        }
        # Only keep cols that actually exist
        agg = {k:v for k,v in agg.items() if k in df_overall.columns}
        clean = (df_overall
                 .groupby(keys, as_index=False)
                 .agg(agg)
                 .sort_values(keys))
    else:
        # Single session file
        clean = df_overall.sort_values("day") if "day" in df_overall.columns else df_overall.copy()

    return clean

def clean_species(df_species: pd.DataFrame) -> pd.DataFrame:
    if df_species is None or len(df_species) == 0:
        return pd.DataFrame()

    num_cols = ("day","species_id","n","alive_end","ate0","ate1","ate2p",
                "avg_speed","avg_size","avg_sense","metabolism")
    for col in num_cols:
        if col in df_species.columns:
            df_species[col] = pd.to_numeric(df_species[col], errors="coerce")

    keys = ["session_id","species_id","species_name","day"] \
        if "session_id" in df_species.columns else ["species_id","species_name","day"]

    agg = {
        "n":"mean","alive_end":"mean","ate0":"mean","ate1":"mean","ate2p":"mean",
        "avg_speed":"mean","avg_size":"mean","avg_sense":"mean","metabolism":"mean"
    }
    agg = {k:v for k,v in agg.items() if k in df_species.columns}

    clean = (df_species
             .groupby(keys, as_index=False)
             .agg(agg)
             .sort_values(keys))
    return clean

def export_csv(df: pd.DataFrame, outdir: str, base: str, tag: str | None) -> str:
    ensure_dir(outdir)
    fname = f"{base}_{timestamp(tag)}.csv"
    fpath = os.path.join(outdir, fname)
    df.to_csv(fpath, index=False)
    print(f"[OK] Wrote {fpath}")
    return fpath

def plot_overall(df_overall: pd.DataFrame, outdir: str, tag: str | None):
    ensure_dir(outdir)
    fig, ax = plt.subplots(3, 1, figsize=(10, 11), sharex=True)  # ← three rows now

    g = df_overall

    # ---- Subplot 1: counts ----
    if "day" in g.columns and "n" in g.columns:
        ax[0].plot(g["day"], g["n"], label="N (start of day)")
    if "alive_end" in g.columns:
        ax[0].plot(g["day"], g["alive_end"], label="Alive end-of-day")
    if "ate0" in g.columns:
        ax[0].plot(g["day"], g["ate0"], label="Ate 0")
    if "ate1" in g.columns:
        ax[0].plot(g["day"], g["ate1"], label="Ate 1")
    if "ate2p" in g.columns:
        ax[0].plot(g["day"], g["ate2p"], label="Ate 2+")
    ax[0].set_ylabel("Count")
    ax[0].legend(loc="best")
    ax[0].grid(alpha=0.25)

    # ---- Subplot 2: traits (Speed & Size only) ----
    if "avg_speed" in g.columns:
        ax[1].plot(g["day"], g["avg_speed"], label="Avg speed")
    if "avg_size" in g.columns:
        ax[1].plot(g["day"], g["avg_size"],  label="Avg size")
    ax[1].set_ylabel("Trait value")
    ax[1].legend(loc="best")
    ax[1].grid(alpha=0.25)

    # ---- Subplot 3: Sense only (new) ----
    if "avg_sense" in g.columns:
        ax[2].plot(g["day"], g["avg_sense"], color="tab:purple", label="Avg sense")
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
    if df_species is None or len(df_species) == 0:
        print("[INFO] No species CSV provided or empty; skipping per‑species plots.")
        return
    ensure_dir(outdir)

    # Cast numerics (safe)
    for col in ("day","n","alive_end","ate0","ate1","ate2p","avg_speed","avg_size","avg_sense"):
        if col in df_species.columns:
            df_species[col] = pd.to_numeric(df_species[col], errors="coerce")

    # Choose grouping key (id preferred)
    group_key = "species_id" if "species_id" in df_species.columns else (
                "species_name" if "species_name" in df_species.columns else None)
    if group_key is None:
        print("[INFO] No species identifier columns found; skipping species plots.")
        return

    for key, sub in df_species.groupby(group_key):
        fig, ax = plt.subplots(3, 1, figsize=(10, 11), sharex=True)

        name = None
        if "species_name" in sub.columns:
            try:
                name = str(sub["species_name"].iloc[0])
            except Exception:
                name = f"{group_key}={key}"
        else:
            name = f"{group_key}={key}"

        # ---- Subplot 1: counts ----
        if all(c in sub.columns for c in ("day","n")):
            ax[0].plot(sub["day"], sub["n"], label=f"{name} (N)")
        if "alive_end" in sub.columns:
            ax[0].plot(sub["day"], sub["alive_end"], label="Alive end")
        if "ate0" in sub.columns:
            ax[0].plot(sub["day"], sub["ate0"], label="Ate 0")
        if "ate1" in sub.columns:
            ax[0].plot(sub["day"], sub["ate1"], label="Ate 1")
        if "ate2p" in sub.columns:
            ax[0].plot(sub["day"], sub["ate2p"], label="Ate 2+")
        ax[0].set_ylabel("Count")
        ax[0].legend(loc="best")
        ax[0].grid(alpha=0.25)

        # ---- Subplot 2: Speed & Size only ----
        if "avg_speed" in sub.columns:
            ax[1].plot(sub["day"], sub["avg_speed"], label="Speed")
        if "avg_size" in sub.columns:
            ax[1].plot(sub["day"], sub["avg_size"],  label="Size")
        ax[1].set_ylabel("Trait value")
        ax[1].legend(loc="best")
        ax[1].grid(alpha=0.25)

        # ---- Subplot 3: Sense only ----
        if "avg_sense" in sub.columns:
            ax[2].plot(sub["day"], sub["avg_sense"], color="tab:purple", label="Sense")
        ax[2].set_xlabel("Day")
        ax[2].set_ylabel("Sense")
        ax[2].legend(loc="best")
        ax[2].grid(alpha=0.25)

        fig.suptitle(f"Species {key} — {name}")
        fig.tight_layout()
        png = os.path.join(outdir, f"species_{key}_trends_{timestamp(tag)}.png")
        fig.savefig(png, dpi=160)
        plt.close(fig)
        print(f"[OK] Saved {png}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--overall", type=str, default="runs/ui_daily.csv",
                    help="Path to overall daily CSV written by the UI")
    ap.add_argument("--species", type=str, default="runs/ui_species_daily.csv",
                    help="Path to per‑species daily CSV (pass '' to disable)")
    ap.add_argument("--outdir", type=str, default="reports",
                    help="Output directory for plots and exported CSVs")
    ap.add_argument("--tag", type=str, default="",
                    help="Optional label to append to filenames (e.g., 'lowfood')")
    args = ap.parse_args()

    df_overall_raw, df_species_raw = load_csvs(args.overall, args.species if args.species else None)

    # Clean/aggregate
    df_overall = clean_overall(df_overall_raw)
    df_species = clean_species(df_species_raw) if df_species_raw is not None else pd.DataFrame()

    # Always export fresh CSVs with timestamp (and optional tag)
    export_csv(df_overall, args.outdir, base="overall_summary", tag=(args.tag or None))
    if df_species is not None and len(df_species) > 0 and (args.species and args.species.strip()):
        export_csv(df_species, args.outdir, base="species_summary", tag=(args.tag or None))

    # Plots (also timestamped)
    plot_overall(df_overall, args.outdir, tag=(args.tag or None))
    if df_species is not None and len(df_species) > 0 and (args.species and args.species.strip()):
        plot_species(df_species, args.outdir, tag=(args.tag or None))

    print(f"\nDone. Outputs are in: {args.outdir}")

if __name__ == "__main__":
    main()