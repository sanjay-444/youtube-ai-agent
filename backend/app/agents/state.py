from typing import TypedDict


class VideoState(TypedDict):

    job_id: str

    youtube_url: str

    transcript: str

    transcript_chunks: list

    use_chunking: bool

    analysis_context: str

    summary: dict

    action_items: dict

    evaluation: str

    quality_score: int

    pdf_path: str