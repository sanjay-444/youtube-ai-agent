from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.agents.graph import build_graph


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="YouTube AI Video Analyzer",
    description="Analyze any YouTube video and generate an AI-powered PDF report.",
    version="1.0.0",
      docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# REQUEST MODEL
# ============================================================

class AnalyzeRequest(BaseModel):

    youtube_url: str = Field(
        ...,
        description="YouTube video URL"
    )


# ============================================================
# ROOT
# ============================================================

@app.get("/api/")
def root():

    return {
        "success": True,
        "message": "YouTube AI Video Analyzer API is running",
        "docs": "/docs"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return {
        "success": True,
        "status": "healthy"
    }


# ============================================================
# ANALYZE VIDEO
# ============================================================

@app.post("/api/analyze")
def analyze_video(request: AnalyzeRequest):

    youtube_url = request.youtube_url.strip()

    # --------------------------------------------------------
    # Validate URL
    # --------------------------------------------------------

    if not youtube_url:

        raise HTTPException(
            status_code=400,
            detail="YouTube URL is required."
        )

    if (
        "youtube.com" not in youtube_url
        and
        "youtu.be" not in youtube_url
    ):

        raise HTTPException(
            status_code=400,
            detail="Please provide a valid YouTube URL."
        )

    print()
    print("=" * 70)
    print("NEW VIDEO ANALYSIS")
    print("=" * 70)
    print(f"YouTube URL: {youtube_url}")
    print("=" * 70)

    try:

        # ----------------------------------------------------
        # Build Agentic AI Graph
        # ----------------------------------------------------

        print()
        print("Building Agentic AI graph...")

        graph = build_graph()

        print("Agentic AI graph built successfully.")

        # ----------------------------------------------------
        # Initial State
        # ----------------------------------------------------

        initial_state = {

            "youtube_url": youtube_url,

            # IMPORTANT:
            # None tells graph.py to retrieve the transcript
            "transcript": None,

            "analysis_context": "",

            "summary": {},

            "action_items": [],

            "evaluation": {},

            "quality_score": 0,

            "pdf_path": ""
        }

        # ----------------------------------------------------
        # Run Graph
        # ----------------------------------------------------

        print()
        print("Starting video analysis...")

        result = graph.invoke(initial_state)

        # ----------------------------------------------------
        # Get PDF Path
        # ----------------------------------------------------

        pdf_path = result.get(
            "pdf_path",
            ""
        )

        if not pdf_path:

            raise RuntimeError(
                "Analysis completed, but PDF path was not returned."
            )

        pdf_path = Path(pdf_path)

        # ----------------------------------------------------
        # Check PDF
        # ----------------------------------------------------

        if not pdf_path.exists():

            raise RuntimeError(
                f"PDF file not found: {pdf_path}"
            )

        if pdf_path.stat().st_size == 0:

            raise RuntimeError(
                "Generated PDF is empty."
            )

        print()
        print("=" * 70)
        print("ANALYSIS COMPLETED")
        print("=" * 70)
        print(f"PDF: {pdf_path}")
        print("=" * 70)

        # ----------------------------------------------------
        # Return PDF
        # ----------------------------------------------------

        return FileResponse(

            path=str(pdf_path),

            media_type="application/pdf",

            filename=pdf_path.name,

            headers={
                "Content-Disposition":
                f'attachment; filename="{pdf_path.name}"'
            }
        )

    except HTTPException:

        raise

    except Exception as exc:

        print()
        print("=" * 70)
        print("ANALYSIS FAILED")
        print("=" * 70)
        print(f"Error: {exc}")
        print("=" * 70)

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )