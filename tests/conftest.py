import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def knowledge_graph():
    from core.config import get_settings
    from tools.neo4j_kb import KnowledgeGraph, create_driver

    load_dotenv(PROJECT_ROOT / ".env")
    settings = get_settings()
    with create_driver(settings) as driver:
        graph = KnowledgeGraph(driver, settings.neo4j_database)
        graph.export_kb()
        yield graph
