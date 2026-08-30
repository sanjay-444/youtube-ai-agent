from app.services.pdf_generator import generate_pdf


summary = {
    "executive_summary": (
        "This video explains how to build a FastAPI "
        "application with PostgreSQL and React."
    ),

    "key_takeaways": [
        "Build a FastAPI application.",
        "Use PostgreSQL with SQLAlchemy.",
        "Configure CORS for React.",
    ],

    "important_concepts": [
        "FastAPI",
        "SQLAlchemy",
        "PostgreSQL",
        "React",
        "CORS",
    ],

    "conclusion": (
        "The tutorial demonstrates how to build "
        "a full-stack application."
    ),
}


action_items = [
    {
        "action": "Create a Python virtual environment",
        "priority": "HIGH",
        "reason": "Isolates project dependencies.",
    },
    {
        "action": "Install FastAPI and Uvicorn",
        "priority": "HIGH",
        "reason": "Required to run the backend.",
    },
]


evaluation = {
    "quality_score": 9,
    "summary_score": 9,
    "action_items_score": 8,
    "feedback": (
        "The analysis is accurate and complete."
    ),
}


pdf_path = generate_pdf(
    summary=summary,
    action_items=action_items,
    evaluation=evaluation,
    youtube_url=(
        "https://www.youtube.com/watch?v=Lu8lXXlstvM"
    ),
)


print()
print("==============================")
print("PDF GENERATED SUCCESSFULLY")
print("==============================")
print(f"PDF path: {pdf_path}")