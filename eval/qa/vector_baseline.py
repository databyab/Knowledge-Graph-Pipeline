def retrieve_chunks(index: object, vectors: object, chunks: list[str], query: object, top_k: int) -> list[str]:
    distances, indexes = index.search(query, top_k)
    del distances
    return [chunks[int(index)] for index in indexes[0] if int(index) < len(chunks)]
