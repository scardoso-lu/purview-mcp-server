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
    mock_repo.search_assets.assert_called_once_with("customer", 10, None, None, offset=0)


@pytest.mark.asyncio
async def test_search_assets_passes_filters(mocker: MockerFixture) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = []

    use_case = SearchAssetsUseCase(catalog=mock_repo)
    await use_case.execute("sales", asset_type="azure_sql_table", classification="GDPR")

    mock_repo.search_assets.assert_called_once_with(
        "sales", 20, "azure_sql_table", "GDPR", offset=0
    )


@pytest.mark.asyncio
async def test_search_assets_excludes_undocumented(
    mocker: MockerFixture, certified_asset: Asset, uncertified_asset: Asset
) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [certified_asset, uncertified_asset]

    use_case = SearchAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer")

    assert [a.id for a in result] == [certified_asset.id]


@pytest.mark.asyncio
async def test_search_assets_excludes_blank_description(
    mocker: MockerFixture, certified_asset: Asset
) -> None:
    blank = certified_asset.model_copy(update={"id": "guid-blank", "description": "   "})
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [blank, certified_asset]

    use_case = SearchAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer")

    assert [a.id for a in result] == [certified_asset.id]


@pytest.mark.asyncio
async def test_search_assets_offset_slices_described_results(
    mocker: MockerFixture, certified_asset: Asset, promoted_asset: Asset
) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [certified_asset, promoted_asset]

    use_case = SearchAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer", limit=1, offset=1)

    assert [a.id for a in result] == [promoted_asset.id]
    # Over-fetches from offset 0 because filtering happens client-side.
    mock_repo.search_assets.assert_called_once_with("customer", 4, None, None, offset=0)
