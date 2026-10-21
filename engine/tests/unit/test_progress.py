import threading
import time

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import progress


class FakeContext:
    def __init__(self):
        self.sent = []

    async def report_progress(self, percent, total, message):
        self.sent.append((int(percent), total, message))


def test_progress_is_passed_on_and_the_result_returned():
    ctx = FakeContext()

    def work(job):
        for pct in (0, 50, 100):
            job.report(pct, f"step {pct}")
            time.sleep(0.5)
        return "done"

    assert anyio.run(progress.run, ctx, work) == "done"
    assert ctx.sent == [(0, 100, "step 0"), (50, 100, "step 50"), (100, 100, "step 100")]


def test_cancel_stops_the_work_and_lets_it_tidy_up():
    tidied = threading.Event()

    def work(job):
        try:
            while True:
                job.report(1, "working")
                time.sleep(0.05)
        except progress.Stopped:
            tidied.set()
            raise

    async def main():
        with anyio.move_on_after(0.5):
            await progress.run(FakeContext(), work)

    anyio.run(main)
    assert tidied.is_set()


def test_a_plain_error_reaches_the_person_unchanged():
    def work(job):
        raise ToolError("This link needs a login.")

    with pytest.raises(ToolError, match="^This link needs a login.$"):
        anyio.run(progress.run, FakeContext(), work)


def test_an_unexpected_error_is_logged_and_explained(private_data):
    def work(job):
        raise ZeroDivisionError("division by zero")

    with pytest.raises(ToolError) as error:
        anyio.run(progress.run, FakeContext(), work)
    assert "division by zero" in str(error.value) and "engine.log" in str(error.value)
