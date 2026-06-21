from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GlossaryTerm(BaseModel):
    id: str
    name: str
    qualified_name: str
    definition: str | None = None
    status: Literal["Draft", "Approved", "Alert", "Expired"] | None = None
    long_description: str | None = None
    examples: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    stewards: list[str] = Field(default_factory=list)
    experts: list[str] = Field(default_factory=list)

    @classmethod
    def _mock(cls, **overrides: Any) -> GlossaryTerm:
        return cls(
            **{
                "id": "term-1",
                "name": "Test Term",
                "qualified_name": "Glossary.TestTerm",
                "status": "Approved",
                **overrides,
            }
        )
