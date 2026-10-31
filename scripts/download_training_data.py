"""Download the public BRFSS binary dataset into the project's data directory."""

import csv
import shutil
from pathlib import Path
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "diabetes_binary_health_indicators_BRFSS2015.csv"
SOURCE_URL = "https://archive.ics.uci.edu/static/public/891/data.csv"


def main():
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_PATH.with_suffix(".csv.part")
    try:
        with urlopen(SOURCE_URL, timeout=120) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        with temporary.open(encoding="utf-8-sig", newline="") as downloaded:
            if "Diabetes_binary" not in next(csv.reader(downloaded)):
                raise ValueError("Downloaded CSV has no Diabetes_binary column.")
        temporary.replace(DATA_PATH)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Dataset saved to {DATA_PATH}")


if __name__ == "__main__":
    main()
