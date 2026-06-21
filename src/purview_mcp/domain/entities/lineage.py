from pydantic import BaseModel, Field


class LineageNode(BaseModel):
    id: str
    name: str
    asset_type: str
    qualified_name: str


class LineageRelation(BaseModel):
    from_id: str
    to_id: str
    relation_type: str | None = None


class LineageGraph(BaseModel):
    asset_id: str
    upstream: list[LineageNode] = Field(default_factory=list)
    downstream: list[LineageNode] = Field(default_factory=list)
    relations: list[LineageRelation] = Field(default_factory=list)
