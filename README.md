# blob-evolution Description
A semi comprehensive evolution simulator with predator and prey dynamics, lineages, and genetics.
# Local Initialization (Not for Github Users)
cd /Users/joshuaetherton/blob_evo/
python3 -m venv .venv
source .venv/bin/activate 
pip install numpy torch matplotlib

# Blob Evolution

## Quick start
```bash
# Run program with user interface
python -m evo_sim.main --ui
# or headless (no user interface)
python -m evo_sim.main --days 30 --pop 60 --seed 42 --csv runs/summary.csv
# analysis (create plots of previous program run with ui)
python analyze_ui_csv.py --overall runs/ui_daily.csv --species runs/ui_species_daily.csv --outdir reports

# Developer Notes
git status
git add -A
git commit -m "Describe what you changed"
git push
