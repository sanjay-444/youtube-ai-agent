import os

from app.agents.graph import build_graph


# ============================================================
# CONFIGURATION
# ============================================================

TRANSCRIPT_FILE = os.path.join(
    "data",
    "sample_transcript.txt"
)


# ============================================================
# LOAD LOCAL TRANSCRIPT
# ============================================================

def load_transcript():

    if not os.path.exists(
        TRANSCRIPT_FILE
    ):
        raise FileNotFoundError(
            f"Transcript file not found: "
            f"{TRANSCRIPT_FILE}"
        )

    with open(
        TRANSCRIPT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        transcript = file.read().strip()

    if not transcript:

        raise ValueError(
            "Transcript file is empty."
        )

    return transcript


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "================================"
    )

    print(
        "YouTube AI Video Analyzer"
    )

    print(
        "================================"
    )

    print(
        "\nUsing local transcript..."
    )

    transcript = load_transcript()

    print(
        f"Transcript length: "
        f"{len(transcript)} characters"
    )

    print(
        "\nBuilding Agentic AI graph..."
    )

    graph = build_graph()

    print(
        "\nStarting analysis..."
    )

    # ========================================================
    # GRAPH INPUT
    # ========================================================

    result = graph.invoke({

        "youtube_url":
            "local://sample_transcript",

        "transcript":
            transcript,

        "analysis_context":
            "",

        "summary":
            {},

        "action_items":
            [],

        "evaluation":
            {},

        "quality_score":
            0,

        "pdf_path":
            ""

    })


    # ========================================================
    # FINAL RESULT
    # ========================================================

    print(
        "\n================================"
    )

    print(
        "FINAL RESULT"
    )

    print(
        "================================"
    )


    summary = result.get(
        "summary",
        {}
    )

    if summary:

        print(
            "\nEXECUTIVE SUMMARY\n"
        )

        print(
            summary.get(
                "executive_summary",
                ""
            )
        )


        print(
            "\nKEY TAKEAWAYS\n"
        )

        for item in summary.get(
            "key_takeaways",
            []
        ):

            print(
                f"- {item}"
            )


        print(
            "\nIMPORTANT CONCEPTS\n"
        )

        for item in summary.get(
            "important_concepts",
            []
        ):

            print(
                f"- {item}"
            )


        print(
            "\nACTION ITEMS\n"
        )

        actions = summary.get(
            "action_items",
            []
        )

        if actions:

            for index, item in enumerate(
                actions,
                start=1
            ):

                if isinstance(
                    item,
                    dict
                ):

                    print(
                        f"{index}. "
                        f"{item.get('action', '')}"
                    )

                    print(
                        f"   Priority: "
                        f"{item.get('priority', 'MEDIUM')}"
                    )

                    print(
                        f"   Reason: "
                        f"{item.get('reason', '')}"
                    )

                else:

                    print(
                        f"{index}. {item}"
                    )

        else:

            print(
                "No action items generated."
            )


        print(
            "\nCONCLUSION\n"
        )

        print(
            summary.get(
                "conclusion",
                ""
            )
        )


    # ========================================================
    # EVALUATION
    # ========================================================

    evaluation = result.get(
        "evaluation",
        {}
    )

    print(
        "\n================================"
    )

    print(
        "EVALUATION"
    )

    print(
        "================================"
    )

    if evaluation:

        print(
            evaluation
        )

    else:

        print(
            "No evaluation generated."
        )


    # ========================================================
    # PDF
    # ========================================================

    pdf_path = result.get(
        "pdf_path",
        ""
    )

    if pdf_path:

        print(
            "\n================================"
        )

        print(
            "PDF GENERATED"
        )

        print(
            "================================"
        )

        print(
            pdf_path
        )


    print(
        "\n================================"
    )

    print(
        "ANALYSIS COMPLETED"
    )

    print(
        "================================"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()