import json
from pathlib import Path

ENTITY_LABELS = {"Condition", "RiskFactor", "Test", "Intervention"}
RELATION_TYPES = {
    "INCREASES_RISK_OF",
    "DIAGNOSES",
    "REDUCES_RISK_OF",
    "ADDRESSES",
    "SHOULD_TEST_WITH",
}


class KnowledgeBaseError(ValueError):
    pass


def load_kb_file(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_kb(kb):
    """Check the KB file is internally consistent. Returns the KB; raises KnowledgeBaseError."""
    errors = []

    def ids_of(items, kind):
        ids = [item.get("id") for item in items]
        if len(ids) != len(set(ids)):
            errors.append(f"duplicate {kind} ids")
        return set(ids)

    source_ids = ids_of(kb.get("sources", []), "source")
    entity_ids = ids_of(kb.get("entities", []), "entity")
    evidence_ids = ids_of(kb.get("evidence", []), "evidence")

    for entity in kb.get("entities", []):
        if entity.get("label") not in ENTITY_LABELS:
            errors.append(f"entity {entity.get('id')}: unknown label {entity.get('label')}")
    for item in kb.get("evidence", []):
        if item.get("source") not in source_ids:
            errors.append(f"evidence {item['id']}: unknown source {item.get('source')}")
        if not item.get("text"):
            errors.append(f"evidence {item['id']}: empty text")
    for rel in kb.get("relations", []):
        name = f"{rel.get('from')}-{rel.get('type')}->{rel.get('to')}"
        if rel.get("type") not in RELATION_TYPES:
            errors.append(f"relation {name}: unknown type")
        for end in ("from", "to"):
            if rel.get(end) not in entity_ids:
                errors.append(f"relation {name}: unknown entity {rel.get(end)}")
        if not rel.get("evidence"):
            errors.append(f"relation {name}: no evidence")
        for evidence_id in rel.get("evidence", []):
            if evidence_id not in evidence_ids:
                errors.append(f"relation {name}: unknown evidence {evidence_id}")

    if errors:
        raise KnowledgeBaseError("; ".join(errors))
    return kb


def create_driver(settings):
    from neo4j import GraphDatabase

    auth = (settings.neo4j_user, settings.neo4j_password) if settings.neo4j_password else None
    return GraphDatabase.driver(settings.neo4j_uri, auth=auth)


class KnowledgeGraph:
    """Diabetes knowledge graph stored in Neo4j. Takes a driver so tests can pass a fake."""

    def __init__(self, driver, database="neo4j"):
        self.driver = driver
        self.database = database

    def _run(self, query, **params):
        with self.driver.session(database=self.database) as session:
            return [record.data() for record in session.run(query, **params)]

    def ensure_schema(self):
        for label in ("Entity", "Evidence", "Source"):
            self._run(
                f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
            )

    def load(self, kb, prune=True):
        """Idempotent upsert of the whole KB; with prune, removes graph items no longer in the file."""
        validate_kb(kb)
        self.ensure_schema()
        version = kb["version"]

        self._run(
            "UNWIND $rows AS row MERGE (s:Source {id: row.id}) "
            "SET s.title = row.title, s.publisher = row.publisher, s.year = row.year, "
            "s.url = row.url, s.kb_version = $version",
            rows=kb["sources"],
            version=version,
        )
        for label in sorted({e["label"] for e in kb["entities"]}):
            rows = [e for e in kb["entities"] if e["label"] == label]
            self._run(
                "UNWIND $rows AS row MERGE (n:Entity {id: row.id}) "
                f"SET n:{label}, n.name = row.name, n.description = row.description, "
                "n.key = row.key, n.kb_version = $version",
                rows=rows,
                version=version,
            )
        self._run(
            "UNWIND $rows AS row MERGE (e:Evidence {id: row.id}) "
            "SET e.text = row.text, e.section = row.section, e.kb_version = $version "
            "WITH e, row MATCH (s:Source {id: row.source}) MERGE (e)-[f:FROM]->(s) SET f.kb_version = $version",
            rows=kb["evidence"],
            version=version,
        )
        for rel_type in sorted({r["type"] for r in kb["relations"]}):
            rows = [r for r in kb["relations"] if r["type"] == rel_type]
            self._run(
                "UNWIND $rows AS row "
                "MATCH (a:Entity {id: row.from}), (b:Entity {id: row.to}) "
                f"MERGE (a)-[r:{rel_type}]->(b) "
                "SET r.evidence_ids = row.evidence, r.kb_version = $version",
                rows=rows,
                version=version,
            )

        if prune:
            self.prune(version)

    def prune(self, version):
        self._run("MATCH ()-[r]->() WHERE r.kb_version <> $v DELETE r", v=version)
        self._run(
            "MATCH (n) WHERE (n:Entity OR n:Evidence OR n:Source) AND n.kb_version <> $v "
            "DETACH DELETE n",
            v=version,
        )

    def stats(self):
        return self._run(
            "MATCH (n) WHERE n:Entity OR n:Evidence OR n:Source "
            "WITH count(n) AS nodes "
            "OPTIONAL MATCH ()-[r]->() "
            "RETURN nodes, count(r) AS relationships"
        )[0]

    def find_entities(self, text, limit=5):
        return self._run(
            "MATCH (n:Entity) WHERE toLower(n.name) CONTAINS toLower($text) "
            "OR toLower(n.description) CONTAINS toLower($text) "
            "RETURN n.id AS id, n.name AS name, labels(n) AS labels "
            "ORDER BY n.name LIMIT $limit",
            text=text,
            limit=limit,
        )

    def relations_with_evidence(self, entity_id, limit=20):
        """Every relation touching the entity, each with its supporting evidence and source."""
        return self._run(
            "MATCH (a:Entity {id: $id})-[r]-(b:Entity) "
            "WITH a, r, b, startNode(r) = a AS outgoing "
            "UNWIND r.evidence_ids AS evidence_id "
            "MATCH (e:Evidence {id: evidence_id})-[:FROM]->(s:Source) "
            "RETURN type(r) AS relation, outgoing, b.id AS other_id, b.name AS other_name, "
            "e.id AS evidence_id, e.text AS evidence, e.section AS section, "
            "s.id AS source_id, s.title AS source_title, s.publisher AS publisher, "
            "s.year AS year, s.url AS url "
            "ORDER BY relation, other_name, evidence_id LIMIT $limit",
            id=entity_id,
            limit=limit,
        )

    def support_for_risk_factors(self, factor_keys, limit=20):
        """Interventions and tests linked to risk factors (by model feature key), with evidence."""
        return self._run(
            "MATCH (f:RiskFactor) WHERE f.key IN $keys "
            "MATCH (x:Entity)-[r]-(f) WHERE (x:Intervention OR x:Test) "
            "AND type(r) IN ['ADDRESSES', 'SHOULD_TEST_WITH'] "
            "UNWIND r.evidence_ids AS evidence_id "
            "MATCH (e:Evidence {id: evidence_id})-[:FROM]->(s:Source) "
            "RETURN f.id AS risk_factor, x.id AS support_id, x.name AS support_name, "
            "labels(x) AS support_labels, type(r) AS relation, e.id AS evidence_id, "
            "e.text AS evidence, s.id AS source_id, s.title AS source_title, s.url AS url "
            "ORDER BY risk_factor, support_name LIMIT $limit",
            keys=list(factor_keys),
            limit=limit,
        )
