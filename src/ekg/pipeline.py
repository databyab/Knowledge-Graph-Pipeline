import hashlib
import logging
from pathlib import Path
from typing import cast

from ekg.extract.extractor import extract_triples_report
from ekg.ingest.chunker import build_chunks
from ekg.llm.base import LLMClient
from ekg.normalize.aliases import apply_alias, normalize_name
from ekg.resolve.cluster import resolve_entities
from ekg.schemas import Edge, Entity, EntityRef, Graph
from ekg.settings import load_yaml
from ekg.store.neo4j_store import Neo4jStore
from ekg.store.sqlite_store import SQLiteStore
from ekg.validate.checks import relation_valid, validate_graph

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def ref_id(ref: EntityRef, source_id: str, context: str | None) -> str:
    return hashlib.sha256(f"{source_id}|{normalize_name(ref.name)}|{ref.type}|{context}".encode()).hexdigest()[:16]


def build_graph(text: str, source_id: str, context: str | None, client: LLMClient, config_dir: Path, sqlite: SQLiteStore, entity_config: dict[str, object] | None = None, neo4j: Neo4jStore | None = None) -> Graph:
    ontology = load_yaml(config_dir / "ontology.yaml")
    config = load_yaml(config_dir / "pipeline.yaml")
    chunks = build_chunks(text, source_id, context, cast(int, config["chunk_words"]), cast(int, config["sentence_overlap"]))
    if len(chunks) > cast(int, config["max_chunks"]):
        raise ValueError("input creates too many chunks")
    aliases_value = entity_config.get("aliases", {}) if entity_config else {}
    aliases = aliases_value if isinstance(aliases_value, dict) else {}
    entities: dict[str, Entity] = {}
    edges: list[Edge] = []
    max_output_tokens = cast(int, config["max_output_tokens"])
    for chunk_index, chunk in enumerate(chunks):
        LOGGER.info("chunk index=%d words=%d max_output_tokens=%d", chunk_index, len(chunk.text.split()), max_output_tokens)
        report = extract_triples_report(client, chunk, ontology, cast(bool, config["use_ontology"]), cast(int, config["max_retries"]))
        dropped = dict(report.dropped)
        for triple in report.triples:
            head_name = apply_alias(triple.head.name, {str(key): str(value) for key, value in aliases.items()})
            tail_name = apply_alias(triple.tail.name, {str(key): str(value) for key, value in aliases.items()})
            head_ref = triple.head.model_copy(update={"name": head_name})
            tail_ref = triple.tail.model_copy(update={"name": tail_name})
            head = Entity(id=ref_id(head_ref, source_id, context), name=head_name, type=triple.head.type, context=context)
            tail = Entity(id=ref_id(tail_ref, source_id, context), name=tail_name, type=triple.tail.type, context=context)
            if not relation_valid(triple.relation, triple.head.type, triple.tail.type, ontology):
                dropped["domain_range"] = dropped.get("domain_range", 0) + 1
            if head.id == tail.id:
                dropped["self_loop"] = dropped.get("self_loop", 0) + 1
            entities[head.id] = head
            entities[tail.id] = tail
            edges.append(Edge(head_id=head.id, relation=triple.relation, tail_id=tail.id, evidence=[triple.evidence], chunk_ids=[chunk.chunk_id], confidence=triple.confidence))
        LOGGER.info("chunk index=%d words=%d raw_triples=%d schema_invalid=%d relation_not_in_ontology=%d evidence_not_substring=%d domain_range=%d self_loop=%d finish_reason=%s truncated=%s max_output_tokens=%d", chunk_index, len(chunk.text.split()), report.raw_triples, dropped.get("schema_invalid", 0), dropped.get("relation_not_in_ontology", 0), dropped.get("evidence_not_substring", 0), dropped.get("domain_range", 0), dropped.get("self_loop", 0), report.finish_reason, report.truncated, max_output_tokens)
    LOGGER.info("run entities_before_resolution=%d edges_before_validation=%d", len(entities), len(edges))
    resolved_entities, resolved_edges = resolve_entities(list(entities.values()), edges, cast(float, config["er_high_threshold"]), cast(float, config["er_low_threshold"]), client)
    graph = validate_graph(resolved_entities, resolved_edges, ontology)
    LOGGER.info("run entities_after_resolution=%d edges_after_validation=%d", len(resolved_entities), len(graph.edges))
    sqlite.save_graph(source_id, graph)
    if neo4j is not None:
        neo4j.save(source_id, graph)
    LOGGER.info("run edges_written=%d", len(graph.edges))
    return graph
