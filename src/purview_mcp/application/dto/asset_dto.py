from typing import Any

from pydantic import Field

from purview_mcp.application.dto import BaseSchema


class AuthoritativeSourceDto(BaseSchema):
    found: bool
    asset: dict[str, Any] | None = None
    score: int | None = None
    explanation: str | None = None
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    message: str | None = None
