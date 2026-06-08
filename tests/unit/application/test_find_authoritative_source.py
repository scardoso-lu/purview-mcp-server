import pytest
from pytest_mock import MockerFixture

from purview_mcp.application.use_cases.find_authoritative_source import (
    FindAuthoritativeSourceUseCase,
)
from purview_mcp.domain.models.asset import Asset


@pytest.mark.asyncio
async def test_certified_asset_is_selected_as_authoritative(
    mocker: MockerFixture,
    certified_asset: Asset,
    uncertified_asset: Asset,
) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [uncertified_asset, certified_asset]

    use_case = FindAuthoritativeSourceUseCase(catalog=mock_repo)
    result = await use_case.execute("customer")

    assert result is not None
    assert result.asset.id == certified_asset.id
    assert result.score > 0
    assert "Certified" in result.explanation


@pytest.mark.asyncio
async def test_returns_none_when_no_assets_found(mocker: MockerFixture) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = []

    use_case = FindAuthoritativeSourceUseCase(catalog=mock_repo)
    result = await use_case.execute("nonexistent concept")

    assert result is None


@pytest.mark.asyncio
async def test_alternatives_exclude_top_result(
    mocker: MockerFixture,
    certified_asset: Asset,
    promoted_asset: Asset,
    uncertified_asset: Asset,
) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [uncertified_asset, promoted_asset, certified_asset]

    use_case = FindAuthoritativeSourceUseCase(catalog=mock_repo)
    result = await use_case.execute("customer")

    assert result is not None
    alternative_ids = [a.id for a in result.alternatives]
    assert result.asset.id not in alternative_ids
