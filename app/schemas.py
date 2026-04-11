from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=4, max_length=240)


class ResearchRunRequest(BaseModel):
    scenario_id: str
    workspace_id: str | None = None
    label: str | None = None
    dataset_id: str = "synthetic_us_equities"
    seed: int = Field(default=21, ge=1, le=9999)


class CompareRequest(BaseModel):
    run_ids: list[str] = Field(min_length=2, max_length=4)
