from purview_mcp.application.services.scoring import rank_assets, score_asset
from purview_mcp.domain.models.asset import Asset


def test_certified_asset_gets_highest_score(certified_asset: Asset) -> None:
    scored = score_asset(certified_asset)
    assert scored.score >= 6  # certified(3) + owner(2) + description(1)
    assert "Certified" in " ".join(scored.reasons)


def test_uncertified_no_owner_scores_zero(uncertified_asset: Asset) -> None:
    scored = score_asset(uncertified_asset)
    assert scored.score == 0
    assert scored.reasons == []


def test_promoted_asset_scores_less_than_certified(
    certified_asset: Asset, promoted_asset: Asset
) -> None:
    certified_score = score_asset(certified_asset).score
    promoted_score = score_asset(promoted_asset).score
    assert certified_score > promoted_score


def test_rank_assets_orders_by_score_descending(
    certified_asset: Asset, promoted_asset: Asset, uncertified_asset: Asset
) -> None:
    ranked = rank_assets([uncertified_asset, certified_asset, promoted_asset])
    assert ranked[0].asset.id == certified_asset.id
    assert ranked[-1].asset.id == uncertified_asset.id
