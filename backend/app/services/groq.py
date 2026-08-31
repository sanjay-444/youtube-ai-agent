import os
import time
from typing import Optional

from dotenv import load_dotenv
from groq import Groq, RateLimitError, APIError


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


GROQ_API_KEY = os.getenv("GROQ_API_KEY")


if not GROQ_API_KEY:

    raise RuntimeError(
        "GROQ_API_KEY environment variable is not set.\n"
        "Make sure your .env file contains:\n"
        "GROQ_API_KEY=your_key_here"
    )


# ============================================================
# GROQ CLIENT
# ============================================================

client = Groq(

    api_key=GROQ_API_KEY,

    timeout=120.0
)


# ============================================================
# MODEL
# ============================================================

MODEL_NAME = "openai/gpt-oss-20b"


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_TEMPERATURE = 0.2

# IMPORTANT:
# Use max_completion_tokens instead of max_tokens
DEFAULT_MAX_COMPLETION_TOKENS = 2000

MAX_RETRIES = 2


# ============================================================
# CALL GROQ
# ============================================================

def call_groq(
    system_prompt: str,
    user_prompt: str,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_COMPLETION_TOKENS,
    retries: int = MAX_RETRIES,
    reasoning_effort: str = "low",
) -> str:

    """
    Centralized Groq API call.

    Designed for openai/gpt-oss-20b.

    Important:
        GPT-OSS is a reasoning model.

        Therefore:
            max_completion_tokens
        is used instead of:
            max_tokens

        reasoning_effort="low"
        keeps reasoning cost and latency lower.
    """

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not system_prompt:

        raise ValueError(
            "system_prompt cannot be empty."
        )


    if not user_prompt:

        raise ValueError(
            "user_prompt cannot be empty."
        )


    # --------------------------------------------------------
    # VALIDATE REASONING
    # --------------------------------------------------------

    allowed_reasoning = {
        "low",
        "medium",
        "high"
    }


    if reasoning_effort not in allowed_reasoning:

        raise ValueError(
            "reasoning_effort must be "
            "'low', 'medium', or 'high'."
        )


    # ========================================================
    # RETRY LOOP
    # ========================================================

    for attempt in range(
        1,
        retries + 1
    ):

        try:

            print()

            print(
                f"Groq request "
                f"(attempt {attempt}/{retries})..."
            )


            # ====================================================
            # API REQUEST
            # ====================================================

            response = client.chat.completions.create(

                model=MODEL_NAME,

                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],

                temperature=temperature,

                # IMPORTANT FOR GPT-OSS
                max_completion_tokens=max_tokens,

                # Reduce reasoning consumption
                reasoning_effort=reasoning_effort,

                # Do not return reasoning to application
                include_reasoning=False,

                stream=False
            )


            # ====================================================
            # VALIDATE RESPONSE
            # ====================================================

            if not response.choices:

                raise RuntimeError(
                    "Groq returned no choices."
                )


            choice = response.choices[0]


            message = choice.message


            if message is None:

                raise RuntimeError(
                    "Groq returned no message."
                )


            # ====================================================
            # DEBUG INFORMATION
            # ====================================================

            finish_reason = getattr(
                choice,
                "finish_reason",
                None
            )


            print(
                f"Groq finish reason: "
                f"{finish_reason}"
            )


            content = getattr(
                message,
                "content",
                None
            )


            # ====================================================
            # EMPTY CONTENT HANDLING
            # ====================================================

            if content is None:

                content = ""


            content = str(
                content
            ).strip()


            if not content:

                reasoning = getattr(
                    message,
                    "reasoning",
                    None
                )


                if reasoning:

                    print(
                        "Groq generated reasoning "
                        "but no visible content."
                    )


                print(
                    f"Finish reason: "
                    f"{finish_reason}"
                )


                # ------------------------------------------------
                # If token limit caused blank response,
                # retry with larger completion budget.
                # ------------------------------------------------

                if (
                    finish_reason == "length"
                    and
                    attempt < retries
                ):

                    print(
                        "Response stopped because "
                        "of token limit."
                    )

                    print(
                        "Increasing completion token budget..."
                    )

                    max_tokens = min(
                        max_tokens * 2,
                        16384
                    )

                    time.sleep(1)

                    continue


                raise RuntimeError(
                    "Groq returned blank content."
                )


            # ====================================================
            # SUCCESS
            # ====================================================

            print(
                "Groq request successful."
            )


            return content


        # ========================================================
        # RATE LIMIT
        # ========================================================

        except RateLimitError as exc:

            print()

            print(
                "Groq rate limit reached."
            )

            print(
                f"Attempt: "
                f"{attempt}/{retries}"
            )


            if attempt >= retries:

                raise RuntimeError(
                    f"Groq rate limit exceeded: "
                    f"{exc}"
                ) from exc


            wait_time = min(
                20 * (2 ** (attempt - 1)),
                120
            )


            print(
                f"Waiting "
                f"{wait_time} seconds..."
            )


            time.sleep(
                wait_time
            )


        # ========================================================
        # API ERROR
        # ========================================================

        except APIError as exc:

            print()

            print(
                f"Groq API error: "
                f"{exc}"
            )


            if attempt >= retries:

                raise RuntimeError(
                    f"Groq API request failed: "
                    f"{exc}"
                ) from exc


            wait_time = 5 * attempt


            print(
                f"Retrying in "
                f"{wait_time} seconds..."
            )


            time.sleep(
                wait_time
            )


        # ========================================================
        # OTHER ERRORS
        # ========================================================

        except Exception as exc:

            print()

            print(
                f"Unexpected Groq error: "
                f"{exc}"
            )


            if attempt >= retries:

                raise RuntimeError(
                    f"Groq request failed after "
                    f"{attempt} attempts: {exc}"
                ) from exc


            time.sleep(2)


    # ========================================================
    # FINAL FAILURE
    # ========================================================

    raise RuntimeError(
        "Groq request failed."
    )


# ============================================================
# JSON HELPER
# ============================================================

def call_groq_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2000,
    retries: int = MAX_RETRIES,
):

    """
    Call GPT-OSS and request JSON output.

    Returns the raw JSON string.

    JSON parsing is intentionally handled by graph.py
    so that graph.py can clean markdown fences and
    recover from minor formatting problems.
    """

    return call_groq(

        system_prompt=system_prompt,

        user_prompt=user_prompt,

        temperature=0.1,

        max_tokens=max_tokens,

        retries=retries,

        reasoning_effort="low"
    )