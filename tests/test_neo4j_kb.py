import copy

import pytest

from tools.neo4j_kb import (
    KnowledgeBaseError,
    KnowledgeGraph,
    evidence_id,
    rebase_relations,
    validate_kb,
)


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
def kb(knowledge_graph):
    return knowledge_graph.export_kb()


def test_neo4j_kb_is_valid_and_every_relation_has_evidence(kb):
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
    KnowledgeGraph(driver).support_for_risk_factors(["BMI", "HighBP"])
    assert driver.calls[0][1]["values"] == ["BMI", "HighBP"] and "f.key IN" in driver.calls[0][0]


def test_cypher_literals_escape_quotes_backslashes_and_newlines():
    from tools.neo4j_kb import _cy

    bs = chr(92)  # one backslash, spelled out to avoid escaping confusion
    assert _cy("it's") == "'it" + bs + "'s'"
    assert _cy("a" + bs + "b") == "'a" + bs + bs + "b'"
    assert _cy("dòng 1" + chr(10) + "dòng 2") == "'dòng 1 dòng 2'"
    assert _cy(None) == "null" and _cy(2017) == "2017"
    assert _cy(["a", "b'c"]) == "['a', 'b" + bs + "'c']"


def test_to_cypher_covers_every_kb_item_and_is_idempotent_merge(kb):
    from tools.neo4j_kb import to_cypher

    script = to_cypher(kb)
    statements = [line for line in script.splitlines() if line.endswith(";")]
    assert sum(line.startswith("CREATE CONSTRAINT") for line in statements) == 3
    assert sum(line.startswith("MERGE (s:Source") for line in statements) == len(kb["sources"])
    assert sum(line.startswith("MERGE (n:Entity") for line in statements) == len(kb["entities"])
    assert sum(line.startswith("MERGE (e:Evidence") for line in statements) == len(kb["evidence"])
    assert sum(line.startswith("MATCH (a:Entity") for line in statements) == len(kb["relations"])
    assert not any(line.startswith("CREATE (") for line in statements)


def test_neo4j_graph_and_entity_evidence(knowledge_graph):
    kb = knowledge_graph
    graph = kb.graph()
    assert graph["entities"] and graph["relations"]
    assert graph["evidence_count"] > 0 and graph["source_count"] > 0
    assert {"id", "name", "label"} <= graph["entities"][0].keys()
    assert all(r["evidence_count"] > 0 for r in graph["relations"])

    rows = kb.relations_with_evidence("high_bmi")
    assert rows
    assert all(r["evidence"] and r["source_title"] for r in rows)
    assert {"type2_diabetes", "prediabetes"} <= {r["other_id"] for r in rows}
    assert kb.relations_with_evidence("no_such_entity") == []


def test_evidence_id_depends_only_on_source_and_normalised_text():
    a = evidence_id("who-diabetes", "Đái tháo đường típ 2  là bệnh mạn tính.")
    assert a == evidence_id("who-diabetes", "Đái tháo đường típ 2 là bệnh mạn tính.")
    assert a.startswith("ev-who-diabetes-") and len(a) == len("ev-who-diabetes-") + 8
    assert a != evidence_id("who-diabetes", "Đái tháo đường típ 1 là bệnh mạn tính.")
    assert a != evidence_id("moh-qt-2017", "Đái tháo đường típ 2 là bệnh mạn tính.")


def test_kb_evidence_ids_match_their_content(kb):
    assert all(e["id"] == evidence_id(e["source"], e["text"]) for e in kb["evidence"])


def test_rebase_relations_keeps_present_evidence_and_reports_the_rest():
    relations = [
        {"from": "a", "type": "INCREASES_RISK_OF", "to": "b", "evidence": ["ev-1", "ev-gone"]},
        {"from": "c", "type": "ADDRESSES", "to": "a", "evidence": ["ev-gone"]},
        {"from": "c", "type": "DIAGNOSES", "to": "b", "evidence": ["ev-2"]},
    ]
    kept, dropped, unsupported = rebase_relations(relations, {"ev-1", "ev-2"})
    assert [r["evidence"] for r in kept] == [["ev-1"], ["ev-2"]]
    assert dropped == {"a-INCREASES_RISK_OF->b": ["ev-gone"], "c-ADDRESSES->a": ["ev-gone"]}
    assert unsupported == [relations[1]]
    assert relations[0]["evidence"] == ["ev-1", "ev-gone"]  # input is not mutated


def test_risk_query_follows_increases_risk_links_by_feature_key():
    driver = FakeDriver()
    KnowledgeGraph(driver).risk_evidence_for_factors(["high_bmi"])
    query, params = driver.calls[0]
    assert params["ids"] == ["high_bmi"] and "INCREASES_RISK_OF" in query and "f.id IN" in query


def test_aliases_are_validated_and_exported(kb):
    import copy

    from tools.neo4j_kb import to_cypher

    with_aliases = copy.deepcopy(kb)
    entity = with_aliases["entities"][0]
    entity["aliases"] = ["mập", "béo"]
    assert "n.aliases = ['mập', 'béo']" in to_cypher(validate_kb(with_aliases))

    entity["aliases"] = ["mập", " "]
    with pytest.raises(KnowledgeBaseError, match="aliases"):
        validate_kb(with_aliases)


def test_chat_support_query_uses_entity_ids():
    driver = FakeDriver()
    KnowledgeGraph(driver).support_for_factor_ids(["family_history"])
    query, params = driver.calls[0]
    assert params["values"] == ["family_history"] and "f.id IN" in query
