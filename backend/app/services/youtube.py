# ============================================================
# backend/app/services/youtube.py
# ============================================================

import re
import os
import requests


# ============================================================
# SUPADATA CONFIGURATION
# ============================================================

SUPADATA_API_URL = (
    "https://api.supadata.ai/v1/transcript"
)


# ============================================================
# EXTRACT VIDEO ID
# ============================================================

def extract_video_id(youtube_url: str) -> str:
    """
    Extract the YouTube video ID from common YouTube URLs.
    """

    if not youtube_url:

        raise ValueError(
            "YouTube URL cannot be empty."
        )

    youtube_url = youtube_url.strip()

    patterns = [

        # https://www.youtube.com/watch?v=XXXXXXXXXXX
        r"(?:youtube\.com/watch\?v=)"
        r"([A-Za-z0-9_-]{11})",

        # https://youtu.be/XXXXXXXXXXX
        r"(?:youtu\.be/)"
        r"([A-Za-z0-9_-]{11})",

        # https://www.youtube.com/embed/XXXXXXXXXXX
        r"(?:youtube\.com/embed/)"
        r"([A-Za-z0-9_-]{11})",

        # https://www.youtube.com/shorts/XXXXXXXXXXX
        r"(?:youtube\.com/shorts/)"
        r"([A-Za-z0-9_-]{11})",

        # https://www.youtube.com/live/XXXXXXXXXXX
        r"(?:youtube\.com/live/)"
        r"([A-Za-z0-9_-]{11})",
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
        "Could not extract video ID."
    )


# ============================================================
# GET YOUTUBE TRANSCRIPT
# ============================================================

def get_youtube_transcript(
    youtube_url: str
) -> str:
    """
    Get YouTube transcript using Supadata.

    This avoids directly calling YouTube from the
    Vercel serverless function.
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
    print(
        f"Video ID: {video_id}"
    )
    print(
        "Using Supadata transcript API..."
    )
    print("=" * 70)

    # --------------------------------------------------------
    # Get API key
    # --------------------------------------------------------

    api_key = os.getenv(
        "SUPADATA_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "SUPADATA_API_KEY environment variable "
            "is not configured."
        )

    # --------------------------------------------------------
    # Request parameters
    # --------------------------------------------------------

    params = {
        "url": youtube_url,
        "text": "true",
        "mode": "auto"
    }

    headers = {
        "x-api-key": api_key,
        "Accept": "application/json"
    }

    try:

        # ----------------------------------------------------
        # Call Supadata
        # ----------------------------------------------------

        response = requests.get(
            SUPADATA_API_URL,
            params=params,
            headers=headers,
            timeout=60
        )

        print(
            f"Supadata status code: "
            f"{response.status_code}"
        )

        # ----------------------------------------------------
        # HTTP error
        # ----------------------------------------------------

        if not response.ok:

            print(
                "Supadata response:"
            )

            print(
                response.text
            )

            raise RuntimeError(
                f"Supadata API returned "
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        data = response.json()

        # ----------------------------------------------------
        # Handle direct text response
        # ----------------------------------------------------

        transcript = data.get(
            "content"
        )

        if isinstance(
            transcript,
            str
        ):

            full_text = transcript.strip()

        # ----------------------------------------------------
        # Handle segmented response
        # ----------------------------------------------------

        elif isinstance(
            transcript,
            list
        ):

            text_parts = []

            for item in transcript:

                if not isinstance(
                    item,
                    dict
                ):

                    continue

                text = item.get(
                    "text",
                    ""
                )

                if text:

                    text_parts.append(
                        str(text).strip()
                    )

            full_text = " ".join(
                text_parts
            ).strip()

        # ----------------------------------------------------
        # Some API responses may return transcript directly
        # ----------------------------------------------------

        elif isinstance(
            data.get("transcript"),
            str
        ):

            full_text = data[
                "transcript"
            ].strip()

        else:

            full_text = ""

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        if not full_text:

            raise RuntimeError(
                "Supadata returned an empty transcript."
            )

        # ----------------------------------------------------
        # Clean whitespace
        # ----------------------------------------------------

        full_text = re.sub(
            r"\s+",
            " ",
            full_text
        ).strip()

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------

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

    except requests.exceptions.Timeout:

        raise RuntimeError(
            "Supadata transcript request timed out."
        )

    except requests.exceptions.RequestException as exc:

        raise RuntimeError(
            f"Unable to connect to Supadata: {exc}"
        ) from exc

    except ValueError:

        raise RuntimeError(
            "Supadata returned invalid JSON."
        )

    except RuntimeError:

        raise

    except Exception as exc:

        raise RuntimeError(
            f"Transcript retrieval failed: {exc}"
        ) from exc