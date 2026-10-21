"""The engine: an MCP server whose tools the four agents call. Tool definitions only; the work is in the modules."""
import argparse
import json
import logging
import logging.handlers
import os
import sys

from mcp.server.mcpserver import MCPServer

from . import models, setup_check
from .paths import data_dir

mcp = MCPServer(
    "engine",
    instructions="Downloads, transcribes, subtitles, cuts, voices and dubs video and audio. "
    "Every tool returns a small JSON object; files are never overwritten.",
)


@mcp.tool()
def check_setup() -> str:
    """What is installed and what is missing: Python, ffmpeg, Deno, a browser for login pages, which models are
    downloaded and how many GB each missing one needs, free memory and disk. Fast; downloads nothing.
    Call it once before heavy work."""
    return json.dumps(setup_check.check_setup())


def setup_logging() -> None:
    """Details and tracebacks go to <data>/engine.log, never to the screen (stdout carries the MCP messages)."""
    handler = logging.handlers.RotatingFileHandler(data_dir() / "engine.log", maxBytes=2_000_000, backupCount=1,
                                                   encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def printer(prefix: str):
    """A progress reporter for the setup command: prints a line at every 10%."""
    shown = [-1]

    def report(percent, message):
        step = int(percent) // 10 * 10
        if step != shown[0]:
            shown[0] = step
            print(f"  {prefix}: {step}%", flush=True)
    return report


def warm(mode: str) -> None:
    """Downloads ffmpeg and the models for the setup mode. Skips whatever is already there, so it is safe to re-run."""
    print("ffmpeg (the video tool): " + ("already here" if models.ffmpeg_present() else "downloading"), flush=True)
    models.ensure_ffmpeg(printer("ffmpeg"))
    names = models.STANDARD if mode == "standard" else models.FULL
    for name in names:
        label = models.MODELS[name]["label"]
        if models.is_present(name):
            print(f"{label}: already here", flush=True)
            continue
        print(f"{label}: downloading {models.missing_gb([name])} GB", flush=True)
        models.ensure([name], printer(label))
    print(f"Done. Models are in {models.models_dir()}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="video-audio-engine", description="The Video Audio Agents engine.")
    parser.add_argument("--warm", choices=["standard", "full"],
                        help="download ffmpeg and the models for this setup mode, then exit")
    parser.add_argument("--check", action="store_true", help="print what is installed and missing, then exit")
    parser.add_argument("--data", help="the plugin's private data folder (the setup skill passes it)")
    args = parser.parse_args()
    if args.data:
        os.environ["VAA_DATA"] = args.data
    setup_logging()
    if not (args.warm or args.check):
        mcp.run()  # talks to Claude over stdin/stdout
        return
    try:
        if args.warm:
            warm(args.warm)
        print(json.dumps(setup_check.check_setup(), indent=2))
    except Exception as e:
        logging.getLogger("engine").exception("Setup failed")
        print(f"Setup stopped: {e}\nThe details are in {data_dir() / 'engine.log'}. Running it again is safe.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
