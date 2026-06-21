from purview_mcp.application.dto.asset_dto import AuthoritativeSourceDto
from purview_mcp.domain.repositories.interfaces import CatalogRepositoryInterface
from purview_mcp.domain.services.scoring import rank_assets
from purview_mcp.shared.observability import Logger


class FindAuthoritativeSourceUseCase:
    def __init__(self, catalog: CatalogRepositoryInterface, log: Logger) -> None:
        self._catalog = catalog
        self._log = log

    async def execute(self, concept: str, limit: int = 10) -> AuthoritativeSourceDto:
        candidates = await self._catalog.search_assets(concept, limit=limit)
        if not candidates:
            self._log.warning("catalog.find_authoritative_source.not_found", concept=concept)
            return AuthoritativeSourceDto(
                found=False,
                message=f"No assets found for concept: '{concept}'",
            )

        ranked = rank_assets(candidates)
        best = ranked[0]
        explanation = (
            f"'{best.asset.name}' ranked highest (score={best.score}) because: {best.explanation}."
            if best.score > 0
            else f"'{best.asset.name}' is the best match found (score={best.score})."
        )

        self._log.info(
            "catalog.find_authoritative_source.completed", concept=concept, score=best.score
        )
        return AuthoritativeSourceDto(
            found=True,
            asset=best.asset.model_dump(),
            score=best.score,
            explanation=explanation,
            alternatives=[s.asset.model_dump() for s in ranked[1:5]],
        )
