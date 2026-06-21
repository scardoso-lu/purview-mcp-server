from dataclasses import dataclass
from typing import Any

from purview_mcp.domain.entities.asset import Asset


@dataclass(frozen=True)
class ScoredAsset:
    asset: Asset
    score: int
    explanation: str

    @classmethod
    def _mock(cls, **overrides: Any) -> "ScoredAsset":
        return cls(
            **{
                "asset": Asset._mock(),
                "score": 3,
                "explanation": "Certified endorsement",
                **overrides,
            }
        )


def score_asset(asset: Asset) -> ScoredAsset:
    """Score an asset on governance metadata quality for authoritative source detection."""
    score = 0
    reasons: list[str] = []

    if asset.endorsement == "Certified":
        score += 3
        reasons.append("Certified endorsement")
    elif asset.endorsement == "Promoted":
        score += 2
        reasons.append("Promoted endorsement")

    if asset.owners:
        score += 2
        reasons.append(f"{len(asset.owners)} owner(s) assigned")

    if asset.description:
        score += 1
        reasons.append("Has description")

    if asset.domain:
        score += 1
        reasons.append(f"Belongs to domain: {asset.domain}")

    if asset.classification:
        score += 1
        reasons.append(f"{len(asset.classification)} classification(s)")

    explanation = ", ".join(reasons) if reasons else "no governance signals"
    return ScoredAsset(asset=asset, score=score, explanation=explanation)


def rank_assets(assets: list[Asset]) -> list[ScoredAsset]:
    scored = [score_asset(a) for a in assets]
    return sorted(scored, key=lambda s: s.score, reverse=True)
