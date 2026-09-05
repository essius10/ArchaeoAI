"""Strict public schemas for the local professional portal demonstration."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROJECT_ID_PATTERN = re.compile(r"^prj_[a-z0-9]{12}$")
RESULT_ID_PATTERN = re.compile(r"^res_[a-z0-9]{12}$")
JOB_ID_PATTERN = re.compile(r"^job_[a-z0-9]{12}$")
SAFE_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,63}$")

ShortText = Annotated[str, Field(min_length=1, max_length=80)]
LongText = Annotated[str, Field(min_length=1, max_length=500)]


class StrictModel(BaseModel):
    """Reject unknown properties and normalize ordinary strings."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _safe_plain_text(value: str) -> str:
    lowered = value.casefold()
    unsafe = (
        "<",
        ">",
        "\x00",
        "file://",
        "http://",
        "https://",
        "../",
        "..\\",
        "c:\\",
        "/etc/",
    )
    if any(token in lowered for token in unsafe) or any(ord(char) < 32 for char in value):
        raise ValueError("unsafe or non-display text is not accepted")
    return value


class RetentionPolicy(StrEnum):
    SESSION_ONLY = "SESSION_ONLY"
    SEVEN_DAYS = "SEVEN_DAYS"
    THIRTY_DAYS = "THIRTY_DAYS"


class SyntheticScenario(StrEnum):
    MOUND_LIKE = "MOUND_LIKE"
    DEPRESSION_LIKE = "DEPRESSION_LIKE"
    PLANAR = "PLANAR"
    SINUSOIDAL = "SINUSOIDAL"
    MIXED_MATHEMATICAL = "MIXED_MATHEMATICAL"


class ProjectStatus(StrEnum):
    DRAFT = "DRAFT"
    AUTHORIZED_FOR_DEMO = "AUTHORIZED_FOR_DEMO"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED = "REVIEWED"
    REPORT_READY = "REPORT_READY"
    FAILED = "FAILED"


class ReviewState(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    IN_REVIEW = "IN_REVIEW"
    REVIEWED = "REVIEWED"
    ESCALATED = "ESCALATED"


class ReviewCategory(StrEnum):
    FURTHER_ASSESSMENT = "MORPHOLOGY_WARRANTS_FURTHER_ASSESSMENT"
    NOT_PRIORITIZED = "MORPHOLOGY_NOT_PRIORITIZED_AFTER_REVIEW"
    INSUFFICIENT = "INSUFFICIENT_TERRAIN_EVIDENCE"
    ARTEFACT_UNCERTAIN = "ARTEFACT_OR_UNCERTAIN"
    ESCALATE = "ESCALATE_TO_QUALIFIED_ARCHAEOLOGICAL_INTERPRETATION"


class ConfidenceDescriptor(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class EvidenceLevel(StrEnum):
    AI_OUTPUT = "AI_OUTPUT"
    AI_HYPOTHESIS = "AI_HYPOTHESIS"
    HUMAN_VETTED_OBSERVATION = "HUMAN_VETTED_OBSERVATION"
    ARCHAEOLOGIST_VALIDATED_INTERPRETATION = "ARCHAEOLOGIST_VALIDATED_INTERPRETATION"
    CONFIRMED_ARCHAEOLOGICAL_EVIDENCE = "CONFIRMED_ARCHAEOLOGICAL_EVIDENCE"


class ProjectCreate(StrictModel):
    project_name: ShortText
    organization: ShortText
    purpose: LongText
    project_reference: str = Field(min_length=1, max_length=64)
    authorized_data_confirmation: bool
    retention_policy: RetentionPolicy
    reviewer_requirement_acknowledgement: bool

    @field_validator("project_name", "organization", "purpose")
    @classmethod
    def validate_plain_text(cls, value: str) -> str:
        return _safe_plain_text(value)

    @field_validator("project_reference")
    @classmethod
    def validate_reference(cls, value: str) -> str:
        if SAFE_REFERENCE_PATTERN.fullmatch(value) is None:
            raise ValueError("project reference must use safe display characters")
        return value

    @model_validator(mode="after")
    def require_acknowledgements(self) -> ProjectCreate:
        if not self.authorized_data_confirmation:
            raise ValueError("authorized data confirmation is required")
        if not self.reviewer_requirement_acknowledgement:
            raise ValueError("reviewer acknowledgement is required")
        return self


class DemoAuthorization(StrictModel):
    authorized_data_confirmation: bool
    reviewer_requirement_acknowledgement: bool

    @model_validator(mode="after")
    def require_acknowledgements(self) -> DemoAuthorization:
        if not self.authorized_data_confirmation or not self.reviewer_requirement_acknowledgement:
            raise ValueError("both demonstration acknowledgements are required")
        return self


class DemoRunRequest(StrictModel):
    scenario: SyntheticScenario
    runtime: str = Field(default="SYNTHETIC_DEMO", pattern=r"^SYNTHETIC_DEMO$")


class ReviewRequest(StrictModel):
    category: ReviewCategory
    rationale: LongText
    confidence: ConfidenceDescriptor
    evidence_level: EvidenceLevel

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        return _safe_plain_text(value)

    @model_validator(mode="after")
    def require_human_level(self) -> ReviewRequest:
        if self.evidence_level is not EvidenceLevel.HUMAN_VETTED_OBSERVATION:
            raise ValueError("demo reviewer may create only HUMAN_VETTED_OBSERVATION")
        return self


class RetentionUpdate(StrictModel):
    retention_policy: RetentionPolicy


class ApprovedRuntimeRequest(StrictModel):
    runtime: str = Field(pattern=r"^APPROVED_MODEL$")
    model_identifier: str = Field(min_length=1, max_length=64)

    @field_validator("model_identifier")
    @classmethod
    def validate_model_identifier(cls, value: str) -> str:
        return _safe_plain_text(value)
