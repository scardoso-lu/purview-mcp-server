import pytest
from pytest_mock import MockerFixture

from purview_mcp.application.use_cases.search_assets import SearchAssetsUseCase
from purview_mcp.domain.models.asset import Asset


@pytest.mark.asyncio
async def test_search_assets_returns_list(mocker: MockerFixture, certified_asset: Asset) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [certified_asset]

    use_case = SearchAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer", limit=5)

    assert len(result) == 1
    assert result[0].id == certified_asset.id
    mock_repo.search_assets.assert_called_once_with("customer", 5, None, None, offset=0)


@pytest.mark.asyncio
async def test_search_assets_passes_filters(mocker: MockerFixture) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = []

    use_case = SearchAssetsUseCase(catalog=mock_repo)
    await use_case.execute("sales", asset_type="azure_sql_table", classification="GDPR")

    mock_repo.search_assets.assert_called_once_with(
        "sales", 10, "azure_sql_table", "GDPR", offset=0
    )
