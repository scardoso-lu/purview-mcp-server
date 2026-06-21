from pydantic import BaseModel, Field


class GlossaryTerm(BaseModel):
    id: str
    name: str
    qualified_name: str
    definition: str | None = None
    status: str | None = None  # "Draft" | "Approved" | "Alert" | "Expired"
    long_description: str | None = None
    examples: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    stewards: list[str] = Field(default_factory=list)
    experts: list[str] = Field(default_factory=list)
