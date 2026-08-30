from app.services.groq import call_groq


def summarize_chunk(
    chunk: str,
    chunk_number: int = 0,
    total_chunks: int = 0
) -> str:

    """
    Summarize one transcript chunk.

    Designed to minimize Groq token consumption.
    """

    if not chunk:
        return ""

    # ============================================================
    # LIMIT CHUNK SIZE
    # ============================================================

    MAX_CHUNK_CHARS = 9000

    if len(chunk) > MAX_CHUNK_CHARS:

        chunk = chunk[:MAX_CHUNK_CHARS]

    # ============================================================
    # SYSTEM PROMPT
    # ============================================================

    system_prompt = """
You are a YouTube transcript compression agent.

Your job is to compress the transcript into useful information
for a later final analysis agent.

Rules:

- Use ONLY information from the transcript.
- Do NOT hallucinate.
- Remove repetition.
- Keep important technical details.
- Keep important instructions.
- Keep commands and code-related information.
- Keep decisions and recommendations.
- Keep actionable tasks.
- Be concise.
- Do not write an introduction.
- Do not write a conclusion.
- Return plain text only.
"""

    # ============================================================
    # USER PROMPT
    # ============================================================

    user_prompt = f"""
Transcript chunk {chunk_number} of {total_chunks}:

{chunk}

Extract ONLY the important information.

Use this format:

KEY_POINTS:
- ...

TECHNICAL_DETAILS:
- ...

ACTIONS:
- ...

IMPORTANT_TERMS:
- ...

Maximum output:
approximately 300-400 words.
"""

    # ============================================================
    # GROQ REQUEST
    # ============================================================

    result = call_groq(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.1,
        max_tokens=500
    )

    if not result:
        return ""

    return result.strip()