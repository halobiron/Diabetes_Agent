import copy

import pytest

from core.config import get_settings
from tools.neo4j_kb import KnowledgeBaseError, KnowledgeGraph, load_kb_file, validate_kb


class FakeRecord:
    def __init__(self, data):
        self._data = data

    def data(self):
        return self._data


class FakeSession:
    def __init__(self, calls, results):
        self.calls = calls
        self.results = results

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query, **params):
        self.calls.append((query, params))
        return [FakeRecord(row) for row in self.results]


class FakeDriver:
    def __init__(self, results=()):
        self.calls = []
        self.results = results

    def session(self, database=None):
        return FakeSession(self.calls, self.results)


@pytest.fixture(scope="module")
def kb():
    return load_kb_file(get_settings().kb_path)


def test_shipped_kb_is_valid_and_every_relation_has_evidence(kb):
    validate_kb(kb)
    assert all(rel["evidence"] for rel in kb["relations"])


def test_validation_rejects_dangling_references(kb):
    broken = copy.deepcopy(kb)
    broken["relations"][0]["evidence"] = ["missing"]
    broken["relations"][1]["to"] = "nowhere"
    broken["entities"][0]["label"] = "Bad`Label"
    with pytest.raises(KnowledgeBaseError) as error:
        validate_kb(broken)
    message = str(error.value)
    assert "unknown evidence missing" in message
    assert "unknown entity nowhere" in message
    assert "unknown label" in message


def test_load_upserts_everything_then_prunes(kb):
    driver = FakeDriver(results=[{"nodes": 1, "relationships": 1}])
    KnowledgeGraph(driver).load(kb)

    queries = [q for q, _ in driver.calls]
    assert sum("CREATE CONSTRAINT" in q for q in queries) == 3
    assert any("MERGE (s:Source" in q for q in queries)
    assert any("SET n:RiskFactor" in q for q in queries)
    assert any("MERGE (a)-[r:INCREASES_RISK_OF]->(b)" in q for q in queries)
    assert "DETACH DELETE" in queries[-1]
    assert driver.calls[-1][1] == {"v": kb["version"]}


def test_load_without_prune_keeps_old_items(kb):
    driver = FakeDriver()
    KnowledgeGraph(driver).load(kb, prune=False)
    assert not any("DELETE" in q for q, _ in driver.calls)


def test_relations_query_passes_entity_and_returns_rows():
    row = {"relation": "REDUCES_RISK_OF", "evidence": "text", "source_id": "dpp-2002"}
    driver = FakeDriver(results=[row])
    rows = KnowledgeGraph(driver).relations_with_evidence("lifestyle_program")
    assert rows == [row]
    query, params = driver.calls[0]
    assert params["id"] == "lifestyle_program"
    assert "[:FROM]->(s:Source)" in query


def test_support_query_uses_feature_keys():
    driver = FakeDriver()
    KnowledgeGraph(driver).support_for_risk_factors(["bmi", "bp"])
    assert driver.calls[0][1]["keys"] == ["bmi", "bp"]
