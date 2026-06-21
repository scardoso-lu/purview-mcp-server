from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LineageNode(BaseModel):
    id: str
    name: str
    asset_type: str
    qualified_name: str

    @classmethod
    def _mock(cls, **overrides: Any) -> LineageNode:
        return cls(
            **{
                "id": "node-1",
                "name": "Test Node",
                "asset_type": "azure_sql_table",
                "qualified_name": "mssql://server/db/schema/table",
                **overrides,
            }
        )


class LineageRelation(BaseModel):
    from_id: str
    to_id: str
    relation_type: str | None = None

    @classmethod
    def _mock(cls, **overrides: Any) -> LineageRelation:
        return cls(**{"from_id": "node-1", "to_id": "node-2", **overrides})


class LineageGraph(BaseModel):
    asset_id: str
    upstream: list[LineageNode] = Field(default_factory=list)
    downstream: list[LineageNode] = Field(default_factory=list)
    relations: list[LineageRelation] = Field(default_factory=list)

    @classmethod
    def _mock(cls, **overrides: Any) -> LineageGraph:
        return cls(**{"asset_id": "asset-guid", **overrides})
