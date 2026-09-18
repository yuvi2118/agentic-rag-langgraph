"""Paragraph-based chunker: packs paragraphs into chunks up to max_chars,
carrying a small trailing overlap into the next chunk so context isn't lost
at a chunk boundary."""


def chunk_text(
    text: str, metadata: dict, max_chars: int = 1500, overlap: int = 150
) -> list[dict]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para

        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            # single paragraph longer than max_chars: hard-split it
            for i in range(0, len(para), max_chars):
                chunks.append(para[i : i + max_chars])
            current = ""

    if current:
        chunks.append(current)

    return [
        {"text": chunk, "metadata": {**metadata, "chunk_index": i}}
        for i, chunk in enumerate(chunks)
    ]
