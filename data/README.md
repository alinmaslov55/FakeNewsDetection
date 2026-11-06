# Fake News Detection — Dataset Documentation

## Overview
This directory stores the raw and processed datasets used to train and evaluate the Fake News Detection credibility models.

## Raw Datasets: ISOT Fake News Dataset
The dataset utilized is the **ISOT Fake News Dataset** (University of Victoria / Kaggle benchmark):
- **`True.csv`**: 21,417 authentic news articles collected from Reuters.com.
- **`Fake.csv`**: 23,481 fabricated and misleading news articles flagged by fact-checking organizations (e.g., Politifact) and unreliable websites.

### Raw Schema
Both files share the following columns:
| Column | Type | Description |
| :--- | :--- | :--- |
| `title` | string | Headline of the news article |
| `text` | string | Full body text of the article |
| `subject` | string | Category topic (e.g., `politicsNews`, `worldnews`, `Government News`, `US_News`, etc.) |
| `date` | string | Publication date string |

## Acquisition & Reproducibility
The dataset can be automatically fetched and validated using the project acquisition script:
```bash
python scripts/download_data.py
```

## Processed Dataset (`processed_news.csv`)
Generated during `DAT-01` (`notebooks/01_data_exploration.ipynb`):
- Merged headlines and text into unified corpus (`full_text`).
- Null and whitespace-only rows removed.
- Verbatim duplicate articles dropped.
- Standardized binary label: `1` for `REAL`, `0` for `FAKE`.
- Identified and documented publisher datelines (e.g., `(Reuters) - `) for removal by `NLP-01`.

## Git Tracking
As per `.gitignore`:
- `*.csv` and `*.jsonl` files are ignored to keep the repository lightweight.
- `README.md` and `.gitkeep` are retained in version control.
