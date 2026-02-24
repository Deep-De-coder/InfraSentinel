"""Change request schema."""

from __future__ import annotations

from pydantic import BaseModel

from packages.core.models.steps import StepDefinition


class ChangeRequest(BaseModel):
    change_id: str
    title: str
    summary: str | None = None
    steps: list[StepDefinition]
