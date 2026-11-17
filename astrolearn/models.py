"""Validated API contracts, separate from storage and routing."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ObservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = Field(min_length=1, max_length=120)
    notes: str = Field(default="", max_length=4000)

    @field_validator("target", mode="before")
    @classmethod
    def strip_target(cls, value: object) -> object:
        # Strip before length validation so whitespace-only targets are rejected.
        return value.strip() if isinstance(value, str) else value


class Observation(ObservationCreate):
    id: int
    created_at: datetime


class LearningObject(BaseModel):
    id: str
    name: str
    category: str
    description: str
