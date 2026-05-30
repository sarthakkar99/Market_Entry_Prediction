"""
models.py
---------
Pydantic schemas for all request and response payloads.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Annotated
from pydantic import BaseModel, Field, field_validator, field_validator


# ── Inbound ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    companies:     list[str] = Field(..., example=["Stripe", "Adyen"])
    target_market: str       = Field(..., min_length=1, max_length=100, example="Insurance")
    country:       str       = Field(default="Global", example="United States")

    @field_validator("companies")
    @classmethod
    def validate_companies(cls, v):
        if not v:
            raise ValueError("At least one company is required")
        return [c.strip() for c in v[:3] if c.strip()]


# ── Per-agent result ─────────────────────────────────────────────────────────

class AgentResult(BaseModel):
    agent_id:  str
    label:     str
    emoji:     str
    score:     int
    max_score: int
    findings:  list[str]
    reasoning: str
    sources:   list[str]


# ── Per-company result ───────────────────────────────────────────────────────

class CompanyReport(BaseModel):
    company:               str
    market:                str
    country:               str
    score:                 int
    probability:           int
    confidence:            str
    timeline:              str
    verdict:               str
    key_findings:          list[str]
    strategic_implication: str
    recommended_actions:   list[str]
    agent_results:         list[AgentResult]


# ── SSE event payloads ───────────────────────────────────────────────────────

class ErrorEvent(BaseModel):
    event:   str = "error"
    message: str