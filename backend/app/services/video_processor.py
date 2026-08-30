from concurrent.futures import ThreadPoolExecutor, as_completed

from app.agents.chunk_summary import summarize_chunk


def split_transcript(
    transcript: str,
    chunk_size: int = 9000
):

    chunks = []

    for i in range(
        0,
        len(transcript),
        chunk_size
    ):

        chunk = transcript[
            i:i + chunk_size
        ]

        if chunk.strip():
            chunks.append(chunk)

    return chunks


def process_long_video(
    transcript: str
):

    print(
        "\n[3] Processing transcript chunks..."
    )

    chunks = split_transcript(
        transcript,
        chunk_size=9000
    )

    total_chunks = len(chunks)

    print(
        f"Transcript split into "
        f"{total_chunks} chunks"
    )

    results = [
        ""
    ] * total_chunks

    # ============================================================
    # IMPORTANT
    # ============================================================
    #
    # Do NOT send 13 requests simultaneously.
    #
    # Groq has rate/token limits.
    #
    # We intentionally use only 2 workers.
    #
    # ============================================================

    MAX_WORKERS = 2

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        future_map = {}

        for index, chunk in enumerate(chunks):

            print(
                f"\nProcessing chunk "
                f"{index + 1}/{total_chunks}..."
            )

            future = executor.submit(
                summarize_chunk,
                chunk,
                index + 1,
                total_chunks
            )

            future_map[
                future
            ] = index

        for future in as_completed(
            future_map
        ):

            index = future_map[
                future
            ]

            try:

                result = future.result()

                results[index] = result

                print(
                    f"Chunk {index + 1}/"
                    f"{total_chunks} completed"
                )

            except Exception as e:

                print(
                    f"Chunk {index + 1} failed:"
                )

                print(e)

                results[index] = ""


    # ============================================================
    # COMBINE RESULTS
    # ============================================================

    valid_results = [
        result
        for result in results
        if result
    ]

    combined_context = "\n\n".join(
        valid_results
    )

    print(
        f"\nCompressed context length: "
        f"{len(combined_context)}"
    )

    return combined_context