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
    mock_repo.search_assets.assert_called_once_with("customer", 50, None, None, offset=0)


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
    mock_repo.search_assets.assert_called_once_with(
        "customer", 50, "azure_sql_view", None, offset=0
    )


@pytest.mark.asyncio
async def test_pages_until_filtered_page_filled(
    mocker: MockerFixture, certified_asset: Asset, uncertified_asset: Asset
) -> None:
    first_page = [certified_asset.model_copy(update={"id": f"doc-{i}"}) for i in range(50)]
    second_page = [uncertified_asset.model_copy(update={"id": "undoc-1"})]
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.side_effect = [first_page, second_page]

    use_case = SearchUndocumentedAssetsUseCase(catalog=mock_repo)
    result = await use_case.execute("customer", limit=2)

    assert [a.id for a in result] == ["undoc-1"]
    assert mock_repo.search_assets.call_count == 2
    mock_repo.search_assets.assert_any_call("customer", 50, None, None, offset=50)


@pytest.mark.asyncio
async def test_empty_when_all_assets_documented(
    mocker: MockerFixture, certified_asset: Asset, promoted_asset: Asset
) -> None:
    mock_repo = mocker.AsyncMock()
    mock_repo.search_assets.return_value = [certified_asset, promoted_asset]

    use_case = SearchUndocumentedAssetsUseCase(catalog=mock_repo)
    assert await use_case.execute("customer") == []
