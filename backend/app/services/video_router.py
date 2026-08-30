def should_chunk(
    transcript: str,
    threshold: int = 12000
) -> bool:

    return len(transcript) > threshold