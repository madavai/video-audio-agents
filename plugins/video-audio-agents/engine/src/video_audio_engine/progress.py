"""Runs a tool's slow work in a thread, passes its progress to Claude, stops it on Esc,
and turns any failure into one plain sentence (the details go to the log file)."""
import logging
import threading

import anyio
from mcp.server.mcpserver.exceptions import ToolError

from .paths import data_dir

log = logging.getLogger("engine")


class Stopped(BaseException):
    """Raised inside the work when the person pressed Esc. A BaseException, so `except Exception` doesn't swallow it."""


class Job:
    """Handed to the work function: it calls `report(percent, message)` often, which also stops it after Esc."""

    def __init__(self):
        self.stop = threading.Event()
        self.percent, self.message = None, ""

    def report(self, percent: float, message: str) -> None:
        self.check()
        self.percent, self.message = max(0.0, min(100.0, percent)), message

    def check(self) -> None:
        if self.stop.is_set():
            raise Stopped()


async def run(ctx, work, *args):
    """Runs `work(job, *args)` in a thread. Sends a progress notification at every 1% (or new message).
    On cancel: tells the work to stop, waits for it to tidy up, then lets the cancel through."""
    job, result = Job(), {}

    def target():
        try:
            result["value"] = work(job, *args)
        except BaseException as e:  # handed back to the async side below
            result["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    sent = (None, None)
    try:
        while True:
            alive = thread.is_alive()
            if job.percent is not None and (int(job.percent), job.message) != sent:
                sent = (int(job.percent), job.message)
                await ctx.report_progress(job.percent, 100, job.message)
            if not alive:
                break
            await anyio.sleep(0.2)
    except anyio.get_cancelled_exc_class():
        job.stop.set()
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(thread.join)
        raise
    error = result.get("error")
    if error is None:
        return result["value"]
    raise plain_error(error)


def plain_error(error: BaseException) -> ToolError:
    """A ToolError (shown to the person) as is; anything unexpected is logged with its traceback."""
    if isinstance(error, ToolError):
        return error
    log.error("Unexpected error", exc_info=error)
    return ToolError(f"Something went wrong ({error}). The details are in {data_dir() / 'engine.log'}.")
