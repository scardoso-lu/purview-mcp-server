from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from purview_mcp.domain.entities.asset import Asset
from purview_mcp.domain.entities.data_product import DataProduct
from purview_mcp.domain.entities.glossary import GlossaryTerm
from purview_mcp.domain.entities.lineage import LineageGraph


class CatalogRepositoryInterface(ABC):
    @abstractmethod
    async def search_assets(
        self,
        query: str,
        limit: int = 10,
        asset_type: str | None = None,
        classification: str | None = None,
        offset: int = 0,
    ) -> list[Asset]:
        raise NotImplementedError

    @abstractmethod
    async def get_asset_by_id(self, guid: str) -> Asset:
        raise NotImplementedError


class GovernanceRepositoryInterface(ABC):
    @abstractmethod
    async def search_glossary_terms(
        self,
        query: str,
        limit: int = 25,
        offset: int = 0,
    ) -> list[GlossaryTerm]:
        raise NotImplementedError

    @abstractmethod
    async def search_data_products(
        self,
        query: str,
        limit: int = 10,
        domain_id: str | None = None,
        offset: int = 0,
    ) -> list[DataProduct]:
        raise NotImplementedError


class LineageRepositoryInterface(ABC):
    @abstractmethod
    async def get_lineage(
        self,
        guid: str,
        direction: Literal["BOTH", "INPUT", "OUTPUT"] = "BOTH",
        depth: int = 3,
    ) -> LineageGraph:
        raise NotImplementedError
