"""Built-in ETL scheduler: a background task that keeps Postgres in sync.

A strictly sequential loop runs one extract+load cycle at a time (so runs never
overlap). Every Nth cycle is a *full reconcile* (enumerate everything, then
delete rows that vanished); the rest are *incremental* (only entities newer than
the last watermark). On an empty database the first cycle is forced to full so
the server becomes useful as soon as possible.
"""

import asyncio

import structlog

from purview_mcp.domain.models.lineage import LineageNode, LineageRelation
from purview_mcp.infrastructure.etl.extract import Extractor
from purview_mcp.infrastructure.etl.load import AssetRecord, Loader, RunCounts

logger = structlog.get_logger(__name__)


class EtlScheduler:
    def __init__(
        self,
        loader: Loader,
        extractor: Extractor,
        *,
        interval_seconds: int = 900,
        full_reconcile_every_n_runs: int = 24,
        concurrency: int = 6,
    ) -> None:
        self._loader = loader
        self._extractor = extractor
        self._interval = interval_seconds
        self._full_every_n = max(1, full_reconcile_every_n_runs)
        self._semaphore = asyncio.Semaphore(max(1, concurrency))
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    # --- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="etl-scheduler")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    # --- loop ----------------------------------------------------------------

    async def _loop(self) -> None:
        run_index = 0
        # Force a full extract when the DB has never been populated.
        force_full = not await self._loader.has_successful_run()
        while not self._stop.is_set():
            full = force_full or (run_index % self._full_every_n == 0)
            force_full = False
            try:
                await self.run_once(full=full)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # never let one bad cycle kill the loop
                logger.error("etl.run.unhandled", error=str(exc), full=full)
            run_index += 1
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval)
            except asyncio.TimeoutError:
                pass

    # --- one cycle -----------------------------------------------------------

    async def run_once(self, full: bool) -> RunCounts:
        async with self._lock:
            return await self._run_once(full)

    async def _run_once(self, full: bool) -> RunCounts:
        kind = "full" if full else "incremental"
        watermark = None if full else await self._loader.last_high_watermark()
        run_id = await self._loader.start_run(kind)
        counts = RunCounts(high_watermark=watermark)
        log = logger.bind(run_id=run_id, kind=kind)
        log.info("etl.run.start", watermark=watermark)
        try:
            # Cheap, independent domains first so their tools work quickly.
            terms = await self._extractor.fetch_glossary_terms()
            counts.terms_upserted = await self._loader.upsert_glossary_terms(run_id, terms)
            products = await self._extractor.fetch_data_products()
            counts.products_upserted = await self._loader.upsert_data_products(run_id, products)

            # Assets + lineage (the expensive, per-GUID phase).
            enumeration = await self._extractor.enumerate_assets(watermark)
            records, nodes, relations, max_ut = await self._fetch_details(
                [h.guid for h in enumeration.hits]
            )
            counts.assets_upserted = await self._loader.upsert_assets(run_id, records)
            await self._loader.upsert_lineage(run_id, nodes, relations)
            if max_ut is not None:
                counts.high_watermark = max(counts.high_watermark or 0, max_ut)

            if (
                enumeration.search_count is not None
                and len(enumeration.hits) < enumeration.search_count
            ):
                log.warning(
                    "etl.enumerate.incomplete",
                    enumerated=len(enumeration.hits),
                    search_count=enumeration.search_count,
                )

            # Deletes only on a full reconcile, and only if we actually loaded data.
            if full and counts.assets_upserted > 0:
                counts.deletes = await self._loader.reconcile_deletes(run_id)

            await self._loader.finish_run(run_id, "success", counts)
            log.info(
                "etl.run.success",
                assets=counts.assets_upserted,
                terms=counts.terms_upserted,
                products=counts.products_upserted,
                deletes=counts.deletes,
                high_watermark=counts.high_watermark,
            )
            return counts
        except asyncio.CancelledError:
            await self._loader.finish_run(run_id, "failed", counts, error="cancelled")
            raise
        except Exception as exc:
            log.error("etl.run.failed", error=str(exc))
            await self._loader.finish_run(run_id, "failed", counts, error=str(exc))
            raise

    async def _fetch_details(
        self, guids: list[str]
    ) -> tuple[list[AssetRecord], list[LineageNode], list[LineageRelation], int | None]:
        records: list[AssetRecord] = []
        nodes: list[LineageNode] = []
        relations: list[LineageRelation] = []
        max_ut: int | None = None

        async def worker(guid: str) -> None:
            async with self._semaphore:
                record = await self._extractor.fetch_asset_record(guid)
                n, r = await self._extractor.fetch_lineage(guid)
            records.append(record)
            nodes.extend(n)
            relations.extend(r)

        await asyncio.gather(*(worker(g) for g in guids))
        for rec in records:
            if rec.update_time is not None:
                max_ut = rec.update_time if max_ut is None else max(max_ut, rec.update_time)
        return records, nodes, relations, max_ut
