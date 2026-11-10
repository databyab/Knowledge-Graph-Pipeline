from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_id: str
    source_id: str
    context: str | None = None
    text: str
    text_hash: str


class EntityRef(BaseModel):
    name: str
    type: str


class Triple(BaseModel):
    head: EntityRef
    relation: str
    tail: EntityRef
    evidence: str
    confidence: float = Field(ge=0, le=1)


class Entity(BaseModel):
    id: str
    name: str
    type: str
    aliases: list[str] = Field(default_factory=list)
    context: str | None = None


class Edge(BaseModel):
    head_id: str
    relation: str
    tail_id: str
    evidence: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    contradictory: bool = False


class Graph(BaseModel):
    entities: list[Entity] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
