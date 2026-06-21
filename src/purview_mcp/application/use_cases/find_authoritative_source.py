from purview_mcp.application.dto.asset_dto import AuthoritativeSourceDto
from purview_mcp.application.services.scoring import rank_assets
from purview_mcp.infrastructure.repositories.contract import CatalogRepositoryInterface


class FindAuthoritativeSourceUseCase:
    def __init__(self, catalog: CatalogRepositoryInterface) -> None:
        self._catalog = catalog

    async def execute(self, concept: str, limit: int = 10) -> AuthoritativeSourceDto:
        candidates = await self._catalog.search_assets(concept, limit=limit)
        if not candidates:
            return AuthoritativeSourceDto(
                found=False,
                message=f"No assets found for concept: '{concept}'",
            )

        ranked = rank_assets(candidates)
        best = ranked[0]
        explanation = (
            f"'{best.asset.name}' ranked highest (score={best.score}) because: "
            + ", ".join(best.reasons)
            + "."
            if best.reasons
            else f"'{best.asset.name}' is the best match found (score={best.score})."
        )

        return AuthoritativeSourceDto(
            found=True,
            asset=best.asset,
            score=best.score,
            explanation=explanation,
            alternatives=[s.asset for s in ranked[1:5]],
        )
