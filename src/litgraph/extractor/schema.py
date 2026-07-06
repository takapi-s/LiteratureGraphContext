"""Pydantic schemas for paper extraction."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    text: str
    evidence_text: str
    page: int = Field(ge=1)
    section: str


class PaperExtraction(BaseModel):
    paper_id: str
    title: Optional[str] = None
    year: Optional[int] = None
    tasks: List[str] = Field(default_factory=list)
    methods: List[str] = Field(default_factory=list)
    datasets: List[str] = Field(default_factory=list)
    metrics: List[str] = Field(default_factory=list)
    contributions: List[EvidenceItem] = Field(default_factory=list)
    claims: List[EvidenceItem] = Field(default_factory=list)
    limitations: List[EvidenceItem] = Field(default_factory=list)
