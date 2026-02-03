# IAQF Project

## Project Structure

```
iaqf-project/
├── data/
│   ├── raw/          # downloaded CSV/API responses
│   └── processed/    # cleaned, merged datasets
├── code/
│   ├── 01_download.py
│   ├── 02_clean.py
│   ├── 03_analyze.py
│   └── 04_visualize.py
├── output/
│   ├── figures/      # all charts for paper
│   └── tables/       # CSV/Excel tables
├── paper/            # LaTeX/Word draft
└── README.md         # How to reproduce your work
```

## How to Reproduce

1. **Download Data**: Run `python code/01_download.py` to download raw data
2. **Clean Data**: Run `python code/02_clean.py` to process and clean the data
3. **Analyze**: Run `python code/03_analyze.py` to perform analysis
4. **Visualize**: Run `python code/04_visualize.py` to generate figures and tables
