import hashlib
import re

from ekg.schemas import Chunk


def split_sentences(text: str, max_words: int = 1_000) -> list[str]:
    sentences: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        words = sentence.split()
        sentences.extend(" ".join(words[index:index + max_words]) for index in range(0, len(words), max_words) if words[index:index + max_words])
    return [sentence for sentence in sentences if sentence]


def build_chunks(text: str, source_id: str, context: str | None, chunk_words: int, sentence_overlap: int) -> list[Chunk]:
    sentences = split_sentences(text, chunk_words)
    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < len(sentences):
        words = 0
        end = start
        while end < len(sentences) and (end == start or words + len(sentences[end].split()) <= chunk_words):
            words += len(sentences[end].split())
            end += 1
        chunk_text = " ".join(sentences[start:end])
        digest = hashlib.sha256(chunk_text.encode()).hexdigest()
        chunks.append(Chunk(chunk_id=f"{source_id}:{index}", source_id=source_id, context=context, text=chunk_text, text_hash=digest))
        index += 1
        start = max(end - sentence_overlap, start + 1)
    return chunks
