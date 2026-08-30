def chunk_text(
    text: str,
    chunk_size: int = 12000,
    overlap: int = 1000
):
    """
    Split a long transcript into overlapping chunks.

    chunk_size and overlap are character-based.
    """

    if not text:
        return []

    if chunk_size <= overlap:
        raise ValueError(
            "chunk_size must be greater than overlap"
        )

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length
        )

        chunk = text[start:end]

        chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks