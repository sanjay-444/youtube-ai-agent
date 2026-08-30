# ============================================================
# backend/app/services/youtube.py
# ============================================================

import re

from youtube_transcript_api import YouTubeTranscriptApi


# ============================================================
# EXTRACT YOUTUBE VIDEO ID
# ============================================================

def extract_video_id(youtube_url: str) -> str:
    """
    Extract the 11-character YouTube video ID from common
    YouTube URL formats.

    Supported:
        https://www.youtube.com/watch?v=XXXXXXXXXXX
        https://youtube.com/watch?v=XXXXXXXXXXX
        https://youtu.be/XXXXXXXXXXX
        https://www.youtube.com/embed/XXXXXXXXXXX
        https://www.youtube.com/shorts/XXXXXXXXXXX
    """

    if not youtube_url:
        raise ValueError(
            "YouTube URL cannot be empty."
        )

    youtube_url = youtube_url.strip()

    patterns = [

        # Standard YouTube URL
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",

        # youtu.be URL
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",

        # YouTube embed URL
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",

        # YouTube Shorts URL
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",

        # YouTube live URL
        r"(?:youtube\.com/live/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            youtube_url,
            re.IGNORECASE
        )

        if match:

            video_id = match.group(1)

            print(
                f"Video ID extracted: {video_id}"
            )

            return video_id

    raise ValueError(
        "Invalid YouTube URL. "
        "Could not extract the video ID."
    )


# ============================================================
# GET YOUTUBE TRANSCRIPT
# ============================================================

def get_youtube_transcript(
    youtube_url: str
) -> str:
    """
    Retrieve the transcript for a YouTube video.

    Parameters
    ----------
    youtube_url:
        YouTube video URL.

    Returns
    -------
    str
        Complete transcript as plain text.

    Raises
    ------
    RuntimeError
        If YouTube blocks the request or no transcript
        can be retrieved.
    """

    # --------------------------------------------------------
    # Extract video ID
    # --------------------------------------------------------

    video_id = extract_video_id(
        youtube_url
    )

    print()
    print("=" * 70)
    print("YOUTUBE TRANSCRIPT")
    print("=" * 70)
    print(f"Video ID: {video_id}")
    print("Trying YouTube transcript API...")
    print("=" * 70)

    try:

        # ----------------------------------------------------
        # Create API client
        # ----------------------------------------------------

        api = YouTubeTranscriptApi()

        # ----------------------------------------------------
        # Fetch transcript
        # ----------------------------------------------------

        transcript = api.fetch(
            video_id
        )

        # ----------------------------------------------------
        # Convert transcript to text
        # ----------------------------------------------------

        text_parts = []

        for item in transcript:

            # New youtube-transcript-api versions
            if hasattr(item, "text"):

                text = item.text

            # Backward compatibility
            elif isinstance(item, dict):

                text = item.get(
                    "text",
                    ""
                )

            else:

                text = ""

            if text:

                text_parts.append(
                    str(text).strip()
                )

        # ----------------------------------------------------
        # Combine transcript
        # ----------------------------------------------------

        full_text = " ".join(
            text_parts
        )

        full_text = re.sub(
            r"\s+",
            " ",
            full_text
        ).strip()

        # ----------------------------------------------------
        # Validate transcript
        # ----------------------------------------------------

        if not full_text:

            raise RuntimeError(
                "Transcript was retrieved but "
                "contains no text."
            )

        print()
        print("=" * 70)
        print("TRANSCRIPT RETRIEVED SUCCESSFULLY")
        print("=" * 70)
        print(
            f"Characters: {len(full_text)}"
        )
        print(
            f"Words: {len(full_text.split())}"
        )
        print("=" * 70)

        return full_text

    except Exception as exc:

        # ----------------------------------------------------
        # Log original error
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("TRANSCRIPT RETRIEVAL FAILED")
        print("=" * 70)
        print(
            f"Error type: {type(exc).__name__}"
        )
        print(
            f"Error: {exc}"
        )
        print("=" * 70)

        error_message = str(exc)

        # ----------------------------------------------------
        # YouTube IP blocking
        # ----------------------------------------------------

        if (
            "RequestBlocked" in error_message
            or
            "IpBlocked" in error_message
            or
            "cloud provider" in error_message.lower()
            or
            "blocking requests" in error_message.lower()
        ):

            raise RuntimeError(
                "YouTube is blocking transcript requests "
                "from the server IP. This commonly happens "
                "when the application is deployed on cloud "
                "platforms such as Vercel. "
                "A transcript proxy or external transcript "
                "service is required for production deployment."
            ) from exc

        # ----------------------------------------------------
        # Transcript unavailable
        # ----------------------------------------------------

        if (
            "CouldNotRetrieveTranscript"
            in error_message
            or
            "NoTranscriptFound"
            in error_message
            or
            "TranscriptNotFound"
            in error_message
        ):

            raise RuntimeError(
                "No accessible transcript was found "
                "for this YouTube video."
            ) from exc

        # ----------------------------------------------------
        # Generic error
        # ----------------------------------------------------

        raise RuntimeError(
            "Unable to retrieve the YouTube transcript. "
            f"Original error: {error_message}"
        ) from exc