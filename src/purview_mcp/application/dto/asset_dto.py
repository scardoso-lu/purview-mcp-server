from pydantic import Field

from purview_mcp.application.dto import BaseSchema
from purview_mcp.domain.entities.asset import Asset


class AuthoritativeSourceDto(BaseSchema):
    found: bool
    asset: Asset | None = None
    score: int | None = None
    explanation: str | None = None
    alternatives: list[Asset] = Field(default_factory=list)
    message: str | None = None
