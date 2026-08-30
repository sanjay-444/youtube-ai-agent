from app.services.youtube import get_transcript


url = "https://www.youtube.com/watch?v=Lu8lXXlstvM"

try:

    transcript = get_transcript(url)

    print("\n==============================")
    print("SUCCESS")
    print("==============================")

    print(
        f"Transcript length: {len(transcript)}"
    )

    print("\nFirst 500 characters:\n")

    print(
        transcript[:500]
    )

except Exception as e:

    print("\n==============================")
    print("FAILED")
    print("==============================")

    print(e)