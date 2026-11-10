import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import get_settings
from tools.neo4j_kb import KnowledgeGraph, create_driver, load_kb_file, validate_kb


def main():
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Restore an offline KB snapshot into Neo4j.")
    parser.add_argument("--kb", default=str(settings.kb_path), help="Offline KB JSON snapshot")
    parser.add_argument("--dry-run", action="store_true", help="validate the file, skip Neo4j")
    parser.add_argument(
        "--no-prune", action="store_true", help="keep graph items missing from file"
    )
    args = parser.parse_args()

    kb = validate_kb(load_kb_file(args.kb))
    print(
        f"KB {kb['version']}: {len(kb['entities'])} entities, {len(kb['evidence'])} evidence, "
        f"{len(kb['relations'])} relations, {len(kb['sources'])} sources - valid"
    )
    if args.dry_run:
        return

    driver = create_driver(settings)
    try:
        graph = KnowledgeGraph(driver, settings.neo4j_database)
        graph.load(kb, prune=not args.no_prune)
        print("Loaded into Neo4j:", graph.stats())
    finally:
        driver.close()


if __name__ == "__main__":
    main()
