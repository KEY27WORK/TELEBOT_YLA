# tests/size_chart/test_size_chart_service_cancel.py
import asyncio
import pytest
from typing import List

from app.infrastructure.size_chart.size_chart_service import SizeChartService
from app.domain.size_chart.interfaces import ProgressEvent, Stage, ProgressFn

HTML = """
<div class="product-info__block-item">
  <img src="https://cdn.shopify.com/img/men-size-chart.png">
  <img srcset="https://cdn.shopify.com/img/size_grid.png 320w, https://cdn.shopify.com/img/size_grid_2x.png 640w">
</div>
"""

class FakeProgress:
    def __init__(self) -> None:
        self.events: List[ProgressEvent] = []

    async def __call__(self, ev: ProgressEvent):
        self.events.append(ev)

    def by_stage(self, stage: Stage):
        return [e for e in self.events if e.stage == stage]


@pytest.mark.asyncio
async def test_size_chart_service_cancel_marks_done_with_error_cancelled():
    svc = SizeChartService(concurrency=2)
    prog = FakeProgress()

    async def runner():
        return await svc.process_all_size_charts(HTML, on_progress=prog)  # type: ignore[arg-type]

    task = asyncio.create_task(runner())
    await asyncio.sleep(0.05)  # дать задачам стартануть
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # Проверяем прогресс:
    started = prog.by_stage(Stage.STARTED)
    done = prog.by_stage(Stage.DONE)

    # Каждый стартовавший должен получить DONE(error='cancelled')
    started_urls = {e.url for e in started}
    cancelled_urls = {e.url for e in done if e.error == "cancelled"}

    assert started_urls, "Ожидали, что хотя бы один айтем стартует до отмены"
    assert started_urls.issubset(cancelled_urls), f"Не всем стартовавшим проставлен DONE(cancelled). started={started_urls}, cancelled={cancelled_urls}"