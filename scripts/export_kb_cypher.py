"""Sinh file Cypher (kb_diabet.cypher) từ KB JSON để nạp vào Neo4j bằng cypher-shell / Browser.

  python scripts/export_kb_cypher.py                      # data/kb/kb_diabet.cypher
  python scripts/export_kb_cypher.py --kb X.json --out Y.cypher
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.neo4j_kb import load_kb_file, to_cypher  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kb", default=str(PROJECT_ROOT / "data" / "kb" / "diabetes_kb.json"))
    parser.add_argument("--out", default=str(PROJECT_ROOT / "data" / "kb" / "kb_diabet.cypher"))
    args = parser.parse_args()

    script = to_cypher(load_kb_file(args.kb))
    Path(args.out).write_text(script, encoding="utf-8")
    statements = sum(1 for line in script.splitlines() if line.endswith(";"))
    print(f"Đã ghi {args.out}: {statements} câu lệnh Cypher")


if __name__ == "__main__":
    main()
