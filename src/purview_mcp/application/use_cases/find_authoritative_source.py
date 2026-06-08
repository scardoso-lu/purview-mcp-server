from dataclasses import dataclass

from purview_mcp.application.services.scoring import ScoredAsset, rank_assets
from purview_mcp.domain.models.asset import Asset
from purview_mcp.domain.ports.catalog_port import ICatalogRepository

_MAX_ALTERNATIVES = 4


@dataclass
class AuthoritativeSourceResult:
    asset: Asset
    score: int
    explanation: str
    alternatives: list[Asset]


class FindAuthoritativeSourceUseCase:
    def __init__(self, catalog: ICatalogRepository) -> None:
        self._catalog = catalog

    async def execute(self, concept: str, limit: int = 10) -> AuthoritativeSourceResult | None:
        candidates = await self._catalog.search_assets(concept, limit=limit)
        if not candidates:
            return None

        ranked: list[ScoredAsset] = rank_assets(candidates)
        best = ranked[0]
        if best.reasons:
            explanation = (
                f"'{best.asset.name}' ranked highest (score={best.score}) because: "
                f"{', '.join(best.reasons)}."
            )
        else:
            explanation = f"'{best.asset.name}' is the best match found (score={best.score})."

        return AuthoritativeSourceResult(
            asset=best.asset,
            score=best.score,
            explanation=explanation,
            alternatives=[s.asset for s in ranked[1 : 1 + _MAX_ALTERNATIVES]],
        )
