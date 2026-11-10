from ekg.llm.base import LLMClient
from ekg.schemas import Entity


def adjudicate(client: LLMClient, left: Entity, right: Entity) -> bool:
    response = client.complete("Return only YES or NO.", f"Are these the same entity? {left.model_dump_json()} {right.model_dump_json()}")
    return response.strip().upper() == "YES"
