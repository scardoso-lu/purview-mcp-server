from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DataProductOwner(BaseModel):
    id: str
    display_name: str | None = None
    email: str | None = None

    @classmethod
    def _mock(cls, **overrides: Any) -> DataProductOwner:
        return cls(**{"id": "owner-1", "display_name": "Alice", **overrides})


class DataProduct(BaseModel):
    id: str
    name: str
    description: str | None = None
    status: str | None = None  # "Draft" | "Active" | "Deprecated"
    owners: list[DataProductOwner] = Field(default_factory=list)
    domain_id: str | None = None
    domain_name: str | None = None
    asset_count: int = 0
    tags: list[str] = Field(default_factory=list)
    data_product_type: str | None = None

    @classmethod
    def _mock(cls, **overrides: Any) -> DataProduct:
        return cls(**{"id": "dp-1", "name": "Test Data Product", "status": "Active", **overrides})
