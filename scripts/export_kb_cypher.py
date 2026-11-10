"""Xuất tri thức từ Neo4j thành script Cypher để nạp hoặc dựng lại cơ sở dữ liệu.

python scripts/export_kb_cypher.py                      # artifacts/kb_diabet.cypher
python scripts/export_kb_cypher.py --out Y.cypher
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import get_settings  # noqa: E402
from tools.neo4j_kb import KnowledgeGraph, create_driver, to_cypher  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(PROJECT_ROOT / "artifacts" / "kb_diabet.cypher"))
    args = parser.parse_args()

    settings = get_settings()
    with create_driver(settings) as driver:
        script = to_cypher(KnowledgeGraph(driver, settings.neo4j_database).export_kb())
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(script, encoding="utf-8")
    statements = sum(1 for line in script.splitlines() if line.endswith(";"))
    print(f"Đã ghi {args.out}: {statements} câu lệnh Cypher")


if __name__ == "__main__":
    main()
