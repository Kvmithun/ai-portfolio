"""
Pydantic schemas for Candidate Profile extraction and structured data representation.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl


class Education(BaseModel):
    institution: str
    degree: str
    specialization: str
    cgpa: float
    duration: str


class Project(BaseModel):
    title: str
    description: str
    technologies: List[str]
    github: Optional[HttpUrl] = None


class CandidateProfile(BaseModel):
    name: str
    phone: str
    email: str
    location: str
    summary: str

    education: List[Education]
    technical_skills: List[str]
    additional_skills: List[str]

    projects: List[Project]
    experience: List[str]
    achievements: List[str]
    certifications: List[str]

    github: Optional[HttpUrl] = None
    linkedin: Optional[HttpUrl] = None
    unstructured_notes: Optional[Dict[str, Any]] = None