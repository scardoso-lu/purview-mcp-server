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
    mock_repo.search_assets.assert_called_once_with("customer", 50, None, None, offset=0)


@pytest.mark.asyncio
async def test_search_assets_passes_filters(mocker: MockerFixture) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = []

    use_case = SearchAssetsUseCase(catalog=mock_repo)
    await use_case.execute("sales", asset_type="azure_sql_table", classification="GDPR")

    mock_repo.search_assets.assert_called_once_with(
        "sales", 50, "azure_sql_table", "GDPR", offset=0
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
    # Fetches from raw offset 0 because filtering happens client-side.
    mock_repo.search_assets.assert_called_once_with("customer", 50, None, None, offset=0)


@pytest.mark.asyncio
async def test_search_assets_pages_until_filtered_page_filled(
    mocker: MockerFixture, certified_asset: Asset, uncertified_asset: Asset
) -> None:
    # limit=2 -> page_size 50. First raw page is full but has no documented
    # assets, so the loop must fetch the next raw page at offset=50.
    first_page = [uncertified_asset.model_copy(update={"id": f"undoc-{i}"}) for i in range(50)]
    second_page = [
        certified_asset.model_copy(update={"id": "doc-1"}),
        certified_asset.model_copy(update={"id": "doc-2"}),
    ]
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.side_effect = [first_page, second_page]

    use_case = SearchAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer", limit=2)

    assert [a.id for a in result] == ["doc-1", "doc-2"]
    assert mock_repo.search_assets.call_count == 2
    mock_repo.search_assets.assert_any_call("customer", 50, None, None, offset=0)
    mock_repo.search_assets.assert_any_call("customer", 50, None, None, offset=50)


@pytest.mark.asyncio
async def test_search_assets_stops_at_raw_scan_cap(
    mocker: MockerFixture, uncertified_asset: Asset
) -> None:
    # Every raw page is full of undocumented assets; the loop must give up
    # after scanning _MAX_RAW_SCAN (10000) raw results instead of looping
    # forever. needed=110 -> page_size 220 -> ceil(10000/220) = 46 calls.
    full_page = [uncertified_asset.model_copy(update={"id": "undoc"})] * 220
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = full_page

    use_case = SearchAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer", limit=100, offset=10)

    assert result == []
    assert mock_repo.search_assets.call_count == 46
