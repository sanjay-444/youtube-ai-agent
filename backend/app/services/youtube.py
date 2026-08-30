import re

from youtube_transcript_api import YouTubeTranscriptApi


# ============================================================
# EXTRACT VIDEO ID
# ============================================================

def extract_video_id(url: str) -> str:

    if not url:
        raise ValueError(
            "YouTube URL is required."
        )

    patterns = [

        r"(?:youtube\.com/watch\?v=)([^&]+)",

        r"(?:youtu\.be/)([^?&]+)",

        r"(?:youtube\.com/embed/)([^?&]+)",

        r"(?:youtube\.com/shorts/)([^?&]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            url
        )

        if match:

            return match.group(1)

    raise ValueError(
        "Invalid YouTube URL."
    )


# ============================================================
# FETCH TRANSCRIPT
# ============================================================

def get_youtube_transcript(
    youtube_url: str
) -> str:

    video_id = extract_video_id(
        youtube_url
    )

    print(
        f"Video ID: {video_id}"
    )

    print(
        "Trying YouTube transcript API..."
    )

    try:

        api = YouTubeTranscriptApi()

        # New youtube-transcript-api versions
        transcript = api.fetch(
            video_id
        )

        parts = []

        for item in transcript:

            if hasattr(item, "text"):

                text = item.text

            elif isinstance(item, dict):

                text = item.get(
                    "text",
                    ""
                )

            else:

                text = str(item)

            if text:

                parts.append(
                    text.strip()
                )

        result = " ".join(parts).strip()

        if not result:

            raise RuntimeError(
                "Transcript was empty."
            )

        print(
            "YouTube transcript retrieved successfully."
        )

        print(
            f"Transcript length: "
            f"{len(result)} characters"
        )

        return result

    except Exception as exc:

        print(
            f"Transcript retrieval failed: {exc}"
        )

        raise RuntimeError(
            "Could not retrieve YouTube transcript. "
            "YouTube may be blocking the request, "
            "the video may not have captions, or "
            "the transcript may be unavailable."
        ) from exc