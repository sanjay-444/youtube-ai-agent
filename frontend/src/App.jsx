import { useState } from "react";
import "./App.css";


function App() {

  const [url, setUrl] = useState("");

  const [loading, setLoading] = useState(false);

  const [message, setMessage] = useState("");

  const [error, setError] = useState("");


  // ==========================================================
  // ANALYZE VIDEO
  // ==========================================================

  const analyzeVideo = async () => {

    setMessage("");
    setError("");

    // --------------------------------------------------------
    // Validation
    // --------------------------------------------------------

    if (!url.trim()) {

      setError(
        "Please enter a YouTube video URL."
      );

      return;
    }

    if (
      !url.includes("youtube.com") &&
      !url.includes("youtu.be")
    ) {

      setError(
        "Please enter a valid YouTube URL."
      );

      return;
    }

    setLoading(true);

    try {

      // ------------------------------------------------------
      // API REQUEST
      // ------------------------------------------------------

      const response = await fetch(
        "api/analyze",
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json"
          },

          body: JSON.stringify({
            youtube_url: url.trim()
          })
        }
      );


      // ------------------------------------------------------
      // ERROR RESPONSE
      // ------------------------------------------------------

      if (!response.ok) {

        let errorMessage =
          "Video analysis failed.";

        try {

          const errorData =
            await response.json();

          errorMessage =
            errorData.detail ||
            errorMessage;

        } catch {

          // Ignore JSON parsing failure

        }

        throw new Error(
          errorMessage
        );
      }


      // ------------------------------------------------------
      // RECEIVE PDF
      // ------------------------------------------------------

      const blob =
        await response.blob();


      if (
        !blob ||
        blob.size === 0
      ) {

        throw new Error(
          "The server returned an empty PDF."
        );
      }


      // ------------------------------------------------------
      // CREATE DOWNLOAD
      // ------------------------------------------------------

      const downloadUrl =
        window.URL.createObjectURL(
          blob
        );


      const link =
        document.createElement("a");


      link.href =
        downloadUrl;


      link.download =
        "youtube_analysis.pdf";


      document.body.appendChild(
        link
      );


      link.click();


      link.remove();


      window.URL.revokeObjectURL(
        downloadUrl
      );


      // ------------------------------------------------------
      // SUCCESS
      // ------------------------------------------------------

      setMessage(
        "Analysis completed successfully! Your PDF has been downloaded."
      );

    } catch (err) {

      console.error(err);

      setError(
        err.message ||
        "Something went wrong."
      );

    } finally {

      setLoading(false);
    }
  };


  // ==========================================================
  // ENTER KEY
  // ==========================================================

  const handleKeyDown = (event) => {

    if (
      event.key === "Enter" &&
      !loading
    ) {

      analyzeVideo();
    }
  };


  // ==========================================================
  // UI
  // ==========================================================

  return (

    <div className="app">

      {/* ====================================================
          BACKGROUND
      ==================================================== */}

      <div className="background-orb orb-one"></div>

      <div className="background-orb orb-two"></div>

      <div className="background-orb orb-three"></div>


      {/* ====================================================
          HEADER
      ==================================================== */}

      <header className="header">

        <div className="logo">

          <div className="logo-icon">
            ▶
          </div>

          <span>
            YouTube AI
          </span>

        </div>


        <div className="header-badge">

          <span className="status-dot"></span>

          AI POWERED

        </div>

      </header>


      {/* ====================================================
          MAIN
      ==================================================== */}

      <main className="main">

        {/* ==================================================
            HERO
        ================================================== */}

        <section className="hero">

          <div className="ai-badge">

            <span>✦</span>

            Intelligent Video Analysis

          </div>


          <h1>

            Turn Any YouTube Video

            <br />

            Into <span>AI Insights</span>

          </h1>


          <p className="hero-description">

            Paste a YouTube URL and let our AI analyze the
            transcript, extract the most important ideas,
            and generate a professional PDF report.

          </p>


          {/* =================================================
              ANALYZER CARD
          ================================================= */}

          <div className="analyzer-card">

            <div className="input-label">

              <span className="link-icon">
                🔗
              </span>

              YouTube Video URL

            </div>


            <div className="input-row">

              <input

                type="text"

                value={url}

                onChange={(event) =>
                  setUrl(event.target.value)
                }

                onKeyDown={handleKeyDown}

                placeholder="https://www.youtube.com/watch?v=..."

                disabled={loading}

              />


              <button

                onClick={analyzeVideo}

                disabled={loading}

                className={
                  loading
                    ? "analyze-button loading"
                    : "analyze-button"
                }

              >

                {loading ? (

                  <>

                    <span className="spinner"></span>

                    Analyzing...

                  </>

                ) : (

                  <>

                    Analyze Video

                    <span className="arrow">
                      →
                    </span>

                  </>

                )}

              </button>

            </div>


            <div className="input-hint">

              <span>🔒</span>

              Your video URL is processed securely.

            </div>


            {/* =================================================
                SUCCESS
            ================================================= */}

            {message && (

              <div className="success-message">

                <span className="success-icon">
                  ✓
                </span>

                {message}

              </div>

            )}


            {/* =================================================
                ERROR
            ================================================= */}

            {error && (

              <div className="error-message">

                <span>
                  ⚠
                </span>

                {error}

              </div>

            )}

          </div>

        </section>


        {/* ==================================================
            FEATURES
        ================================================== */}

        <section className="features">

          <div className="feature-card">

            <div className="feature-icon purple">
              🧠
            </div>

            <h3>
              Smart Summary
            </h3>

            <p>
              Transform lengthy videos into
              concise AI-generated summaries.
            </p>

          </div>


          <div className="feature-card">

            <div className="feature-icon blue">
              💡
            </div>

            <h3>
              Key Insights
            </h3>

            <p>
              Extract important concepts,
              takeaways and actionable ideas.
            </p>

          </div>


          <div className="feature-card">

            <div className="feature-icon pink">
              📄
            </div>

            <h3>
              PDF Report
            </h3>

            <p>
              Download a professional report
              containing your complete analysis.
            </p>

          </div>

        </section>


        {/* ==================================================
            HOW IT WORKS
        ================================================== */}

        <section className="how-section">

          <div className="section-title">

            <span>
              SIMPLE PROCESS
            </span>

            <h2>
              How it works
            </h2>

          </div>


          <div className="steps">

            <div className="step">

              <div className="step-number">
                01
              </div>

              <h3>
                Paste URL
              </h3>

              <p>
                Enter any supported YouTube
                video URL.
              </p>

            </div>


            <div className="step-line"></div>


            <div className="step">

              <div className="step-number">
                02
              </div>

              <h3>
                AI Analysis
              </h3>

              <p>
                Our agent extracts and analyzes
                the video transcript.
              </p>

            </div>


            <div className="step-line"></div>


            <div className="step">

              <div className="step-number">
                03
              </div>

              <h3>
                Download Report
              </h3>

              <p>
                Receive a structured PDF report
                with useful insights.
              </p>

            </div>

          </div>

        </section>

      </main>


      {/* ====================================================
          FOOTER
      ==================================================== */}

      <footer>

        <div>
          YouTube AI Analyzer
        </div>

        <div>
          Powered by Agentic AI
        </div>

      </footer>

    </div>
  );
}


export default App;