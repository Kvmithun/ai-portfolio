# AI Candidate Representative

An AI-powered Candidate Representative that answers recruiter questions using a structured candidate profile extracted from a resume. The system acts as a digital representative of a candidate by providing grounded responses about skills, projects, education, experience, and achievements while maintaining conversational context.

Unlike traditional chatbots, the assistant is initialized with a candidate profile at startup and responds only from verified information instead of generating unsupported or speculative answers. It can also analyze a Job Description (JD) to evaluate the candidate's suitability by identifying matching skills, missing requirements, strengths, and providing an overall hiring recommendation.

## Core Idea

Recruiters often spend significant time reviewing resumes and asking repetitive screening questions. This project automates that initial interaction by creating an AI representative capable of:

- Answering recruiter questions about the candidate.
- Explaining projects, skills, education, and achievements.
- Maintaining conversation history for contextual follow-up questions.
- Comparing the candidate profile with a Job Description.
- Providing grounded, resume-based responses without hallucination.

## Features

- AI-powered recruiter assistant
- Resume-grounded question answering
- Structured candidate profile using Pydantic
- Conversation memory
- Streaming AI responses
- Job Description matching
- Match score generation
- Strengths and missing skills analysis
- Hiring recommendation
- Prompt guardrails to minimize hallucinations
- Modular backend architecture

## Tech Stack

### Backend

- Python
- Flask
- Groq API
- Pydantic

### Frontend

- HTML
- CSS
- JavaScript

## Workflow

1. Candidate profile is initialized from the resume during application startup.
2. The structured profile is stored in memory.
3. Recruiters interact with the AI through a chat interface.
4. Every response is generated using only the candidate profile and conversation history.
5. A Job Description can be provided to evaluate candidate suitability.
6. The assistant returns insights including strengths, missing skills, match percentage, and interview recommendation.

## Project Structure

```
AI-Candidate-Representative/
│
├── backend/
│   ├── app.py
│   ├── main.py
│   ├── models.py
│   ├── prompts.py
│   ├── resume_parser.py
│   ├── utils.py
│   ├── requirements.txt
│   └── uploads/
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── assets/
│
└── README.md
```

## Future Enhancements

- Multi-candidate support
- Resume upload and profile generation
- Authentication and recruiter dashboard
- Interview analytics
- Candidate comparison
- Cloud deployment
- ATS integration
- Multi-model LLM support