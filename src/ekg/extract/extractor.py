import json
import logging
import re
from dataclasses import dataclass

from pydantic import TypeAdapter, ValidationError

from ekg.extract.prompts import make_system, make_user
from ekg.llm.base import LLMClient
from ekg.schemas import Chunk, Triple

LOGGER = logging.getLogger(__name__)


class ExtractionError(ValueError):
    def __init__(self, reason: str, raw_triples: int, dropped: dict[str, int], finish_reason: str | None, truncated: bool) -> None:
        super().__init__(reason)
        self.reason = reason
        self.raw_triples = raw_triples
        self.dropped = dropped
        self.finish_reason = finish_reason
        self.truncated = truncated


@dataclass(frozen=True)
class ExtractionReport:
    triples: list[Triple]
    raw_triples: int
    dropped: dict[str, int]
    finish_reason: str | None
    truncated: bool


def parse_json_response(raw: str) -> object:
    value = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value, flags=re.DOTALL | re.IGNORECASE)
    return json.loads(fenced.group(1) if fenced else value)


def normalize_response_shape(value: object) -> object:
    if isinstance(value, dict) and isinstance(value.get("triples"), list):
        value = value["triples"]
    if not isinstance(value, list):
        return value
    normalized: list[object] = []
    for item in value:
        if not isinstance(item, dict):
            normalized.append(item)
            continue
        current = dict(item)
        head = current.get("head")
        tail = current.get("tail")
        if "head" not in current and "subject" in current:
            current["head"] = {"name": current.pop("subject"), "type": current.pop("subject_type", "Concept")}
        if "tail" not in current and "object" in current:
            current["tail"] = {"name": current.pop("object"), "type": current.pop("object_type", "Concept")}
        if isinstance(head, dict) and "name" not in head and "subject" in head:
            current["head"] = {"name": head["subject"], "type": head.get("type", "Concept")}
        if isinstance(tail, dict) and "name" not in tail and "object" in tail:
            current["tail"] = {"name": tail["object"], "type": tail.get("type", "Concept")}
        normalized.append(current)
    return normalized


def extract_triples(client: LLMClient, chunk: Chunk, ontology: dict[str, object], use_ontology: bool, max_retries: int) -> list[Triple]:
    return extract_triples_report(client, chunk, ontology, use_ontology, max_retries).triples


def extract_triples_report(client: LLMClient, chunk: Chunk, ontology: dict[str, object], use_ontology: bool, max_retries: int) -> ExtractionReport:
    relations = set(ontology.get("relations", {}))
    system = make_system(ontology)
    error = "extraction_failed"
    raw_triples = 0
    dropped = {"schema_invalid": 0, "entity_name_invalid": 0, "relation_not_in_ontology": 0, "evidence_not_substring": 0}
    finish_reason: str | None = None
    truncated = False
    for _ in range(max_retries + 1):
        raw_triples = 0
        user = make_user(chunk.text, error)
        try:
            raw = client.complete(system, user)
            finish_reason = getattr(client, "last_finish_reason", None)
            truncated = bool(getattr(client, "last_truncated", False))
            normalized = normalize_response_shape(parse_json_response(raw))
            raw_triples = len(normalized) if isinstance(normalized, list) else 0
            values = TypeAdapter(list[Triple]).validate_python(normalized)
            for triple in values:
                if use_ontology and triple.relation not in relations:
                    dropped["relation_not_in_ontology"] += 1
                    raise ExtractionError("relation_not_in_ontology", raw_triples, dropped, finish_reason, truncated)
                if triple.evidence not in chunk.text:
                    dropped["evidence_not_substring"] += 1
                    raise ExtractionError("evidence_not_substring", raw_triples, dropped, finish_reason, truncated)
            accepted = []
            for triple in values:
                head_valid = valid_entity_name(triple.head.name, triple.head.type) and all(
                    valid_entity_name(alias, triple.head.type) for alias in triple.head.same_as
                )
                tail_valid = valid_entity_name(triple.tail.name, triple.tail.type) and all(
                    valid_entity_name(alias, triple.tail.type) for alias in triple.tail.same_as
                )
                if not head_valid or not tail_valid:
                    dropped["entity_name_invalid"] += 1
                else:
                    accepted.append(triple)
            return ExtractionReport(accepted, raw_triples, dropped, getattr(client, "last_finish_reason", None), bool(getattr(client, "last_truncated", False)))
        except json.JSONDecodeError:
            client.invalidate(system, user)
            error = "json_invalid"
        except ValidationError:
            client.invalidate(system, user)
            dropped["schema_invalid"] += raw_triples
            error = "schema_invalid"
        except ExtractionError as exc:
            client.invalidate(system, user)
            error = exc.reason
    raise ExtractionError(error, raw_triples, dropped, finish_reason, truncated)


def valid_entity_name(name: str, entity_type: str) -> bool:
    words = name.split()
    return bool(words) and len(words) <= 5 and (
        entity_type != "Event" or name[0].isupper() or name[0].isdigit()
    )
