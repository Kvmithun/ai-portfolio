from __future__ import annotations

"""
Flask backend application for AI Candidate Representative (Mithun KV).
Includes structured terminal logging.
"""
import os
import json
import logging
import re
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from groq import Groq

from models import CandidateProfile
from prompts import SYSTEM_PROMPT, EXTRA_INFORMATION
from resume_parser import read_pdf, build_candidate_profile
from utils import truncate_messages

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("AICandidateRep")

# ---------------------------------------------------------------------------
# Setup & Initialization
# ---------------------------------------------------------------------------
load_dotenv()

my_api_key = os.getenv("GROQ_API_KEY")
if not my_api_key:
    logger.critical("GROQ_API_KEY environment variable is not set in .env!")
    raise ValueError("GROQ_API_KEY environment variable is not set in .env")

client = Groq(api_key=my_api_key)
MODEL_NAME = "llama-3.3-70b-versatile"

app = Flask(__name__)
CORS(app)

# Dynamically target the uploads directory
UPLOADS_DIR = Path(__file__).parent / "uploads"

state = {
    "candidate_profile": None,
    "messages": [],
    "job_description": ""
}

SKILL_ALIASES = {
    "python": ["python"],
    "sql": ["sql", "mysql", "postgresql", "database"],
    "flask": ["flask"],
    "django": ["django"],
    "rest api": ["rest api", "rest apis", "api"],
    "numpy": ["numpy", "num py"],
    "pandas": ["pandas"],
    "matplotlib": ["matplotlib"],
    "seaborn": ["seaborn"],
    "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "tensorflow": ["tensorflow"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "ann", "cnn", "rnn", "lstm", "gru"],
    "nlp": ["nlp", "natural language processing"],
    "generative ai": ["generative ai", "genai", "llm", "large language model"],
    "transformers": ["transformer", "transformers"],
    "mlops": ["mlops", "dvc", "data versioning", "model pipeline"],
    "aws": ["aws", "s3", "aws s3"],
    "git": ["git"],
    "github": ["github"],
    "mongodb": ["mongodb", "mongo db"],
    "blockchain": ["blockchain", "algorand"],
    "jwt": ["jwt", "authentication"],
    "computer networks": ["computer network", "computer networks", "networking"],
    "operating systems": ["operating system", "operating systems", "os"],
}


def get_resume_path() -> Path | None:
    """Finds the first PDF file available in the uploads directory."""
    if not UPLOADS_DIR.exists():
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        return None

    # Search for all PDF files in the uploads directory
    pdf_files = list(UPLOADS_DIR.glob("*.pdf"))
    if pdf_files:
        # Use the first PDF found
        return pdf_files[0]

    return None


def load_default_candidate_profile():
    """Pre-loads Mithun's resume from the uploads folder and initializes Ground Truth context."""
    resume_path = get_resume_path()

    if not resume_path:
        logger.warning(f"No PDF resume found in {UPLOADS_DIR}. Waiting for manual context.")
        return

    logger.info(f"Attempting to load resume from: {resume_path}")

    try:
        pdf_text = read_pdf(resume_path)
        logger.info(f"PDF parsed successfully ({len(pdf_text)} characters extracted).")

        full_candidate_text = pdf_text + "\n\n" + EXTRA_INFORMATION

        logger.info("Building candidate profile via Groq structured outputs...")
        profile_model: CandidateProfile = build_candidate_profile(full_candidate_text, client, MODEL_NAME)

        # Dump with mode="json" to serialize HttpUrl objects to standard strings
        profile_dict = profile_model.model_dump(mode="json")

        state["candidate_profile"] = profile_dict

        state["messages"] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"CANDIDATE DATA (GROUND TRUTH):\n{json.dumps(profile_dict, indent=2)}",
            },
        ]
        logger.info(f"Candidate profile for '{profile_dict.get('name', 'Mithun KV')}' successfully loaded into state.")
    except Exception as err:
        logger.error(f"Failed to load candidate profile: {err}", exc_info=True)


# Pre-load on startup
load_default_candidate_profile()


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9+#.\s-]", " ", value.lower())


def has_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = normalize_text(phrase).strip()
    if not normalized_phrase:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])", text) is not None


def profile_skill_text(profile: dict) -> str:
    chunks = [
        profile.get("summary", ""),
        " ".join(profile.get("technical_skills", [])),
        " ".join(profile.get("additional_skills", [])),
        " ".join(profile.get("experience", [])),
        " ".join(profile.get("achievements", [])),
        " ".join(profile.get("certifications", [])),
    ]

    for project in profile.get("projects", []):
        chunks.extend([
            project.get("title", ""),
            project.get("description", ""),
            " ".join(project.get("technologies", [])),
        ])

    return normalize_text(" ".join(chunks))


def extract_jd_requirements(jd_text: str) -> list[str]:
    normalized_jd = normalize_text(jd_text)
    requirements = []

    for canonical_skill, aliases in SKILL_ALIASES.items():
        if any(has_phrase(normalized_jd, alias) for alias in aliases):
            requirements.append(canonical_skill)

    return requirements


def candidate_has_requirement(candidate_text: str, requirement: str) -> bool:
    aliases = SKILL_ALIASES.get(requirement, [requirement])
    return any(has_phrase(candidate_text, alias) for alias in aliases)


def calculate_match_score(profile: dict, jd_text: str) -> dict:
    jd_requirements = extract_jd_requirements(jd_text)
    candidate_text = profile_skill_text(profile)

    matched_skills = [
        requirement for requirement in jd_requirements
        if candidate_has_requirement(candidate_text, requirement)
    ]
    missing_skills = [
        requirement for requirement in jd_requirements
        if requirement not in matched_skills
    ]

    if not jd_requirements:
        score = 35
    else:
        coverage = len(matched_skills) / len(jd_requirements)
        score = round(coverage * 100)

        if len(jd_text) < 120:
            score = min(score, 70)
        elif len(jd_requirements) < 4:
            score = min(score, 75)

    if score >= 85:
        recommendation = "Strong Hire"
    elif score >= 70:
        recommendation = "Hire"
    elif score >= 45:
        recommendation = "Possible Match"
    else:
        recommendation = "Do Not Hire"

    return {
        "match_percentage": max(0, min(100, score)),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "hiring_recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def health_check():
    logger.info("Health check endpoint hit.")
    return jsonify({
        "status": "online",
        "service": "AI Candidate Representative API",
        "candidate_loaded": state["candidate_profile"] is not None,
        "candidate_name": state["candidate_profile"].get("name") if state["candidate_profile"] else None
    }), 200


@app.route("/profile", methods=["GET"])
def get_profile():
    logger.info("GET /profile requested.")
    if not state["candidate_profile"]:
        logger.warning("GET /profile requested but profile is not loaded.")
        return jsonify({"error": "Candidate profile not loaded"}), 404
    return jsonify(state["candidate_profile"]), 200


@app.route("/chat", methods=["POST"])
def chat():
    logger.info("POST /chat stream requested.")
    if not state["candidate_profile"]:
        logger.error("POST /chat failed: Candidate profile missing.")
        return jsonify({"error": "Candidate profile is missing on server."}), 500

    data = request.get_json()
    if not data or "message" not in data or not data["message"].strip():
        logger.warning("POST /chat received empty message payload.")
        return jsonify({"error": "Empty message prompt"}), 400

    user_message = data["message"].strip()
    logger.info(f"Received User Query: '{user_message[:60]}...'")

    state["messages"].append({"role": "user", "content": user_message})
    state["messages"] = truncate_messages(state["messages"], max_turns=8)

    def generate_stream():
        full_assistant_reply = ""
        token_count = 0
        try:
            logger.info(f"Initiating stream completion with model '{MODEL_NAME}'...")
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=state["messages"],
                temperature=0.0,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_assistant_reply += token
                    token_count += 1
                    yield f"data: {json.dumps({'token': token})}\n\n"

            state["messages"].append({"role": "assistant", "content": full_assistant_reply})
            state["messages"] = truncate_messages(state["messages"], max_turns=8)
            logger.info(f"Stream finished successfully. Total tokens emitted: {token_count}")
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as err:
            logger.error(f"Error during SSE streaming: {err}", exc_info=True)
            yield f"data: {json.dumps({'error': str(err)})}\n\n"

    return Response(stream_with_context(generate_stream()), content_type="text/event-stream")


@app.route("/match", methods=["POST"])
def match_resume_jd():
    logger.info("POST /match requested.")
    if not state["candidate_profile"]:
        logger.error("POST /match failed: Candidate profile not loaded.")
        return jsonify({"error": "Candidate profile not loaded."}), 500

    data = request.get_json() or {}
    jd_text = data.get("jd_text", "").strip()

    if not jd_text:
        logger.warning("POST /match received empty Job Description.")
        return jsonify({"error": "No Job Description provided."}), 400

    logger.info(f"Evaluating candidate match against JD ({len(jd_text)} characters)...")
    deterministic_match = calculate_match_score(state["candidate_profile"], jd_text)

    prompt = f"""
Compare the candidate profile against the provided Job Description.

Candidate Profile:
{json.dumps(state['candidate_profile'], indent=2)}

Job Description:
{jd_text}

Use this deterministic scoring result exactly. Do not change these values:
{json.dumps(deterministic_match, indent=2)}

Provide a structured assessment in valid JSON format with these exact keys:
1. "match_percentage": {deterministic_match["match_percentage"]}
2. "matched_skills": {json.dumps(deterministic_match["matched_skills"])}
3. "strengths": (list of bullet string points matching JD requirements)
4. "weaknesses": (list of bullet string points where candidate lacks experience)
5. "missing_skills": {json.dumps(deterministic_match["missing_skills"])}
6. "hiring_recommendation": "{deterministic_match["hiring_recommendation"]}"
7. "summary_reasoning": (concise paragraph explaining the deterministic match result)

Return ONLY valid JSON.
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert technical recruiter analyzing job fit."},
                {"role": "user", "content": prompt}
            ]
        )
        result_json = json.loads(completion.choices[0].message.content)
        result_json["match_percentage"] = deterministic_match["match_percentage"]
        result_json["matched_skills"] = deterministic_match["matched_skills"]
        result_json["missing_skills"] = deterministic_match["missing_skills"]
        result_json["hiring_recommendation"] = deterministic_match["hiring_recommendation"]
        logger.info(
            f"Match assessment complete. Score: {result_json.get('match_percentage')}% | Recommendation: {result_json.get('hiring_recommendation')}")
        return jsonify(result_json), 200

    except Exception as e:
        logger.error(f"Failed to execute match evaluation: {e}", exc_info=True)
        return jsonify({"error": f"Failed to perform matching: {str(e)}"}), 500


if __name__ == "__main__":
    logger.info("Starting Flask backend development server on http://0.0.0.0:5002")
    app.run(host="0.0.0.0", port=5002, debug=True)
