from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AssetOwner(BaseModel):
    id: str
    display_name: str
    contact_type: str  # "Expert" | "Owner"
    email: str | None = None

    @classmethod
    def _mock(cls, **overrides: Any) -> AssetOwner:
        return cls(**{"id": "owner-1", "display_name": "Alice", "contact_type": "Owner", **overrides})


class DataQualityMetric(BaseModel):
    name: str
    value: float | None = None
    status: str | None = None

    @classmethod
    def _mock(cls, **overrides: Any) -> DataQualityMetric:
        return cls(**{"name": "completeness", "value": 0.95, **overrides})


class Asset(BaseModel):
    id: str
    name: str
    asset_type: str
    description: str | None = None
    owners: list[AssetOwner] = Field(default_factory=list)
    classification: list[str] = Field(default_factory=list)
    endorsement: str | None = None  # "Certified" | "Promoted" | None
    domain: str | None = None
    tags: list[str] = Field(default_factory=list)
    qualified_name: str
    collection: str | None = None
    data_quality: list[DataQualityMetric] = Field(default_factory=list)

    def has_description(self) -> bool:
        return bool(self.description and self.description.strip())

    @classmethod
    def _mock(cls, **overrides: Any) -> Asset:
        return cls(
            **{
                "id": "asset-guid",
                "name": "Test Asset",
                "asset_type": "azure_sql_table",
                "qualified_name": "mssql://server/db/schema/table",
                **overrides,
            }
        )
