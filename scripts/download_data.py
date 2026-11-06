"""
Dataset downloader script for the ISOT Fake News Dataset.

Downloads True.csv and Fake.csv into the data/ directory,
verifying file integrity and CSV schema.
"""

from pathlib import Path
import sys
import requests
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DATASET_FILES = {
    "True.csv": {
        "url": "https://raw.githubusercontent.com/Reinforz/Fake-News-detection-with-ISOT-Dataset/main/True.csv",
        "expected_min_bytes": 15 * 1024 * 1024,  # ~18.7 MB
    },
    "Fake.csv": {
        "url": "https://raw.githubusercontent.com/Reinforz/Fake-News-detection-with-ISOT-Dataset/main/Fake.csv",
        "expected_min_bytes": 20 * 1024 * 1024,  # ~23.7 MB
    },
}

EXPECTED_COLUMNS = {"title", "text", "subject", "date"}


def download_file(url: str, destination: Path, expected_min_bytes: int) -> None:
    """Download a file with streaming and basic progress."""
    print(f"Downloading {destination.name} from {url}...")
    headers = {"User-Agent": "FakeNewsDetection-Setup/1.0"}
    response = requests.get(url, stream=True, timeout=60, headers=headers)
    response.raise_for_status()

    total_bytes = 0
    temp_path = destination.with_suffix(".tmp")
    with open(temp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
            if chunk:
                f.write(chunk)
                total_bytes += len(chunk)
                print(f"  {destination.name}: {total_bytes / (1024 * 1024):.1f} MB downloaded", end="\r")

    print(f"\n  Finished {destination.name}: {total_bytes / (1024 * 1024):.2f} MB")

    if total_bytes < expected_min_bytes:
        temp_path.unlink(missing_ok=True)
        raise ValueError(
            f"Downloaded {destination.name} is too small ({total_bytes} bytes). Expected at least {expected_min_bytes} bytes."
        )

    temp_path.replace(destination)


def validate_csv(path: Path) -> dict[str, int]:
    """Validate CSV header and report row count."""
    df_sample = pd.read_csv(path, nrows=5)
    columns = set(df_sample.columns.str.strip().str.lower())
    if not EXPECTED_COLUMNS.issubset(columns):
        raise ValueError(f"{path.name} is missing expected columns {EXPECTED_COLUMNS}. Found: {columns}")

    # Read full file to count rows
    df = pd.read_csv(path)
    return {"rows": len(df), "columns": list(df.columns)}


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Target data directory: {DATA_DIR}")

    for filename, info in DATASET_FILES.items():
        dest = DATA_DIR / filename
        # Only re-download if file is missing or empty
        if not dest.exists() or dest.stat().st_size < info["expected_min_bytes"]:
            download_file(info["url"], dest, info["expected_min_bytes"])
        else:
            print(f"File {filename} already exists ({dest.stat().st_size / (1024 * 1024):.2f} MB), skipping download.")

        # Validate
        stats = validate_csv(dest)
        print(f"  Validated {filename}: {stats['rows']} rows, columns: {stats['columns']}")

    print("\nDataset acquisition completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
