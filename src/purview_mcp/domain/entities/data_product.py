from pydantic import BaseModel, Field


class DataProductOwner(BaseModel):
    id: str
    display_name: str | None = None
    email: str | None = None


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
