from app.services.youtube import get_transcript


def main():

    print("=" * 40)
    print("LOCAL WHISPER TEST")
    print("=" * 40)

    url = input(
        "\nEnter YouTube URL: "
    ).strip()

    if not url:
        print("URL cannot be empty.")
        return

    try:

        transcript = get_transcript(url)

        print()
        print("=" * 40)
        print("TRANSCRIPTION SUCCESSFUL")
        print("=" * 40)

        print()
        print("Transcript:")
        print(transcript)

        print()
        print(
            f"Transcript length: {len(transcript)} characters"
        )

    except Exception as e:

        print()
        print("=" * 40)
        print("FAILED")
        print("=" * 40)

        print(type(e).__name__)
        print(str(e))


if __name__ == "__main__":
    main()