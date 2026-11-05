import json, sys
from pathlib import Path
import numpy as np, pandas as pd, joblib
import matplotlib.pyplot as plt

ROOT = Path.cwd()
if not (ROOT / "models").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "report" / "images"
TAB = ROOT / "report" / "tables"
OUT.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "axes.grid": True, "grid.alpha": .3,
                     "axes.spines.top": False, "axes.spines.right": False})
metrics = json.loads((ROOT / "artifacts" / "metrics.json").read_text(encoding="utf-8"))
vn = lambda x, d=4: f"{x:.{d}f}".replace(".", ",")      # số thập phân kiểu Việt Nam
print(metrics["model_version"], metrics["rows_total"], metrics["selected_threshold"])
