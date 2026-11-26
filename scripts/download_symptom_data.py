"""Download the public UCI 529 dataset with attribution and content fingerprint."""

import hashlib
import io
import json
import zipfile
from pathlib import Path

import requests

URL = "https://archive.ics.uci.edu/static/public/529/early%2Bstage%2Bdiabetes%2Brisk%2Bprediction%2Bdataset.zip"


def main():
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    member = next(name for name in archive.namelist() if name.endswith("diabetes_data_upload.csv"))
    content = archive.read(member)
    folder = Path(__file__).resolve().parents[1] / "data/train/symptoms"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "diabetes_data_upload.csv").write_bytes(content)
    (folder / "source.json").write_text(
        json.dumps(
            {
                "source": URL,
                "dataset_page": "https://archive.ics.uci.edu/dataset/529/early+stage+diabetes+risk+",
                "doi": "10.24432/C5VG8H",
                "license": "CC BY 4.0",
                "sha256": hashlib.sha256(content).hexdigest(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved {len(content)} bytes with UCI attribution and SHA-256.")


if __name__ == "__main__":
    main()
