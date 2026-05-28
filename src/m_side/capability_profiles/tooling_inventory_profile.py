"""Tooling inventory profile for shop capability."""
from pydantic import BaseModel, Field


class ToolingInventoryProfile(BaseModel):
    tool_id: str
    tool_type: str
    diameter_mm: float | None = None
    material: str | None = None
    max_depth_mm: float | None = None
    quantity_available: int = 0
    compatible_materials: list[str] = Field(default_factory=list)
