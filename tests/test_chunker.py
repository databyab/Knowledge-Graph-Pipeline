from ekg.ingest.chunker import build_chunks


def test_chunk_ids_and_hashes_are_deterministic() -> None:
    first = build_chunks("One. Two. Three.", "source", None, 2, 1)
    second = build_chunks("One. Two. Three.", "source", None, 2, 1)
    assert [item.model_dump() for item in first] == [item.model_dump() for item in second]
