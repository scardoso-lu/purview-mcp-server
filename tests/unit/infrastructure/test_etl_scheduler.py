import pytest

from purview_mcp.domain.models.asset import Asset
from purview_mcp.infrastructure.etl.extract import AssetHit, Enumeration
from purview_mcp.infrastructure.etl.load import AssetRecord, RunCounts
from purview_mcp.infrastructure.etl.scheduler import EtlScheduler


class FakeLoader:
    def __init__(self, *, successful_run: bool = False, watermark: int | None = None) -> None:
        self._successful_run = successful_run
        self._watermark = watermark
        self.runs: list[tuple[int, str]] = []
        self.finished: list[tuple[int, str]] = []
        self.reconciled: list[int] = []
        self.upserted_assets = 0
        self._next_run_id = 1

    async def has_successful_run(self) -> bool:
        return self._successful_run

    async def last_high_watermark(self) -> int | None:
        return self._watermark

    async def start_run(self, kind: str) -> int:
        run_id = self._next_run_id
        self._next_run_id += 1
        self.runs.append((run_id, kind))
        return run_id

    async def finish_run(self, run_id, status, counts=None, error=None) -> None:  # noqa: ANN001
        self.finished.append((run_id, status))

    async def upsert_glossary_terms(self, run_id, terms) -> int:  # noqa: ANN001
        return len(terms)

    async def upsert_data_products(self, run_id, products) -> int:  # noqa: ANN001
        return len(products)

    async def upsert_assets(self, run_id, records) -> int:  # noqa: ANN001
        self.upserted_assets = len(records)
        return len(records)

    async def upsert_lineage(self, run_id, nodes, relations) -> None:  # noqa: ANN001
        pass

    async def reconcile_deletes(self, run_id) -> int:  # noqa: ANN001
        self.reconciled.append(run_id)
        return 0


class FakeExtractor:
    def __init__(self, hits: list[AssetHit], search_count: int | None = None) -> None:
        self._enum = Enumeration(hits=hits, search_count=search_count)
        self.enumerate_watermark: int | None = -1
        self.fail = False

    async def fetch_glossary_terms(self) -> list:
        if self.fail:
            raise RuntimeError("boom")
        return []

    async def fetch_data_products(self) -> list:
        return []

    async def enumerate_assets(self, watermark=None) -> Enumeration:  # noqa: ANN001
        self.enumerate_watermark = watermark
        return self._enum

    async def fetch_asset_record(self, guid: str) -> AssetRecord:
        asset = Asset(id=guid, name=guid, asset_type="t", qualified_name=guid)
        return AssetRecord(asset=asset, update_time=100)

    async def fetch_lineage(self, guid: str):  # noqa: ANN201
        return [], []


def _scheduler(loader, extractor, **kw):  # noqa: ANN001, ANN003
    return EtlScheduler(loader, extractor, **kw)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_full_run_reconciles_and_records_watermark() -> None:
    loader = FakeLoader()
    extractor = FakeExtractor([AssetHit("g1", 100)], search_count=1)
    sched = _scheduler(loader, extractor)

    counts = await sched.run_once(full=True)

    assert loader.runs == [(1, "full")]
    assert loader.finished == [(1, "success")]
    assert loader.reconciled == [1]  # full reconcile ran
    assert counts.assets_upserted == 1
    assert counts.high_watermark == 100


@pytest.mark.asyncio
async def test_incremental_run_uses_watermark_and_skips_reconcile() -> None:
    loader = FakeLoader(successful_run=True, watermark=50)
    extractor = FakeExtractor([AssetHit("g1", 100)])
    sched = _scheduler(loader, extractor)

    await sched.run_once(full=False)

    assert loader.runs == [(1, "incremental")]
    assert extractor.enumerate_watermark == 50  # watermark passed through
    assert loader.reconciled == []  # no deletes on incremental


@pytest.mark.asyncio
async def test_failure_marks_run_failed_and_raises() -> None:
    loader = FakeLoader()
    extractor = FakeExtractor([])
    extractor.fail = True
    sched = _scheduler(loader, extractor)

    with pytest.raises(RuntimeError):
        await sched.run_once(full=True)
    assert loader.finished == [(1, "failed")]


@pytest.mark.asyncio
async def test_loop_forces_full_on_empty_db_then_incremental() -> None:
    loader = FakeLoader(successful_run=False)
    extractor = FakeExtractor([])
    sched = _scheduler(loader, extractor, interval_seconds=0, full_reconcile_every_n_runs=3)

    seen: list[bool] = []

    async def fake_run_once(full: bool) -> RunCounts:
        seen.append(full)
        if len(seen) >= 3:
            sched._stop.set()
        return RunCounts()

    sched.run_once = fake_run_once  # type: ignore[assignment]
    await sched._loop()

    # Empty DB forces the first run full; subsequent runs follow the cadence.
    assert seen == [True, False, False]


@pytest.mark.asyncio
async def test_loop_survives_a_failing_cycle() -> None:
    loader = FakeLoader(successful_run=True)
    extractor = FakeExtractor([])
    sched = _scheduler(loader, extractor, interval_seconds=0, full_reconcile_every_n_runs=99)

    seen: list[bool] = []

    async def flaky_run_once(full: bool) -> RunCounts:
        seen.append(full)
        if len(seen) == 1:
            raise RuntimeError("transient")
        if len(seen) >= 2:
            sched._stop.set()
        return RunCounts()

    sched.run_once = flaky_run_once  # type: ignore[assignment]
    await sched._loop()

    # The loop kept going after the first cycle raised.
    assert len(seen) == 2
