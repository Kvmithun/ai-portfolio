"""
Helper functions to extract text from PDFs and parse structured profiles via Groq LLM.
"""
import json
from pathlib import Path
import pdfplumber
from groq import Groq
from models import CandidateProfile
from prompts import EXTRA_INFORMATION


def read_pdf(path: Path) -> str:
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def read_resume_file(file_path_str: str) -> str:
    file_path = Path(file_path_str)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() == ".pdf":
        resume_text = read_pdf(file_path)
        return resume_text + "\n\n" + EXTRA_INFORMATION
    else:
        raise ValueError("Unsupported file type. Please provide a PDF file.")


def build_candidate_profile(candidate_text: str, client: Groq, model: str = "llama-3.3-70b-versatile") -> CandidateProfile:
    schema_json = json.dumps(CandidateProfile.model_json_schema(), indent=2)

    prompt = f"""
Extract the complete candidate profile from the provided text.

CRITICAL INSTRUCTIONS:
1. Include ALL main projects from the resume AND ALL GitHub projects listed under 'Additional Candidate Information'.
2. Combine all technical skills and additional skills from both sections without dropping any.
3. Match repository URLs from the additional information section to the corresponding project's 'github' field.
4. If there is extra metadata or notes that do not fit into standard fields, place them in 'unstructured_notes'.

Return strictly valid JSON matching this schema:
{schema_json}

Candidate Information:
{candidate_text}
"""

    completion = client.chat.completions.create(
        model=model,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert resume parser. Extract every single project, link, and skill "
                    "into valid JSON matching the provided schema. Do not drop extra projects or skills."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    json_response = completion.choices[0].message.content
    return CandidateProfile.model_validate_json(json_response)