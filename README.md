# blob-evolution
A semi comprehensive evolution simulator with predator and prey dynamics, lineages, and genetics.

cd /Users/joshuaetherton/blob_evo/
python3 -m venv .venv
source .venv/bin/activate 
pip install numpy torch matplotlib




python3 -m evo_sim.main --days 50 --pop 80 --seed 123 --csv runs/summary.csv --plot



Run the UI with: python -m evo_sim.main --ui
Headless run: python -m evo_sim.main --days 100 --pop 60 --seed 42 --csv runs/summary.csv





python analyze_ui_csv.py --overall runs/ui_daily.csv --species runs/ui_species_daily.csv --outdir reports



Standard usage: creates fresh CSVs + plots in /reports
python analyze_ui_csv.py --overall runs/ui_daily.csv --species runs/ui_species_daily.csv --outdir reports



python -m evo_sim.main --ui
python analyze_ui_csv.py --overall runs/ui_daily.csv --species runs/ui_species_daily.csv --outdir reports --tag test


git status
git add -A
git commit -m "Describe what you changed"
git push
