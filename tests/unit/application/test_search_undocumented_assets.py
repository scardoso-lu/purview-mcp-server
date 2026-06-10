import pytest
from pytest_mock import MockerFixture

from purview_mcp.application.use_cases.search_undocumented_assets import (
    SearchUndocumentedAssetsUseCase,
)
from purview_mcp.domain.models.asset import Asset


@pytest.mark.asyncio
async def test_returns_only_assets_without_description(
    mocker: MockerFixture, certified_asset: Asset, uncertified_asset: Asset
) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [certified_asset, uncertified_asset]

    use_case = SearchUndocumentedAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer")

    assert [a.id for a in result] == [uncertified_asset.id]
    mock_repo.search_assets.assert_called_once_with("customer", 20, None, None, offset=0)


@pytest.mark.asyncio
async def test_blank_description_counts_as_undocumented(
    mocker: MockerFixture, certified_asset: Asset
) -> None:
    blank = certified_asset.model_copy(update={"id": "guid-blank", "description": "   "})
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [certified_asset, blank]

    use_case = SearchUndocumentedAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer")

    assert [a.id for a in result] == ["guid-blank"]


@pytest.mark.asyncio
async def test_passes_filters_and_applies_offset(
    mocker: MockerFixture, uncertified_asset: Asset
) -> None:
    second = uncertified_asset.model_copy(update={"id": "guid-undocumented-2"})
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [uncertified_asset, second]

    use_case = SearchUndocumentedAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer", limit=1, asset_type="azure_sql_view", offset=1)

    assert [a.id for a in result] == ["guid-undocumented-2"]
    mock_repo.search_assets.assert_called_once_with("customer", 4, "azure_sql_view", None, offset=0)


@pytest.mark.asyncio
async def test_empty_when_all_assets_documented(
    mocker: MockerFixture, certified_asset: Asset, promoted_asset: Asset
) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [certified_asset, promoted_asset]

    use_case = SearchUndocumentedAssetsUseCase(catalog=mock_repo)
    assert await use_case.execute("customer") == []
