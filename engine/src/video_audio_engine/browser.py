"""Pages behind a login: open the page in Edge or Chrome, catch its video or audio stream, and hand the
page's cookies to the downloader. The login is remembered in a private browser profile."""
import os
import time

from mcp.server.mcpserver.exceptions import ToolError

from . import paths
from .setup_check import find_browser

CHANNELS = {"edge": "msedge", "chrome": "chrome", "chromium": None}  # chromium: Playwright's own, if setup installed it
FIRST_WAIT, LATER_WAIT = 600, 60  # seconds: time to log in the first time; after that the login is remembered
PLAY = "document.querySelectorAll('video, audio').forEach(v => { v.muted = true; v.play().catch(() => {}); })"
opened_before = False


def find_stream(job, url: str) -> dict:
    """Opens `url` in a visible browser window, starts its video muted, and returns
    {"stream", "title", "cookies" (Netscape text), "referer"} for the first video or audio it loads."""
    global opened_before
    from playwright.sync_api import Error as PlaywrightError, sync_playwright

    browser = find_browser()
    if not browser:
        raise ToolError("This link can't be downloaded directly and needs a browser, but neither Edge nor Chrome "
                        "is installed. Install one of them, or ask to \"set up the login browser\".")
    wait = int(os.environ.get("VAA_BROWSER_WAIT") or (LATER_WAIT if opened_before else FIRST_WAIT))
    opened_before = True
    found = []

    def catch(request):
        if not found and (request.resource_type == "media" or ".m3u8" in request.url or ".mpd" in request.url):
            found.append(request.url)

    job.report(0, "A browser window opened. Log in if asked (first time only) and press play if the video "
                  "doesn't start.")
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                str(paths.data_dir() / "browser-profile"), channel=CHANNELS[browser],
                headless=os.environ.get("VAA_BROWSER_HEADLESS") == "1")  # headless only in tests
        except PlaywrightError as e:
            raise ToolError(f"The browser couldn't be opened ({str(e).splitlines()[0]}). Close any browser window "
                            "this tool opened before, then try again.") from e
        try:
            context.on("request", catch)  # catches new tabs too
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url)
            deadline = time.monotonic() + wait
            while not found and time.monotonic() < deadline:
                job.check()
                for frame in page.frames:
                    try:
                        frame.evaluate(PLAY)
                    except PlaywrightError:
                        pass  # a frame that went away or blocks scripts
                page.wait_for_timeout(2000)
            if not found:
                raise ToolError("No video or audio was found on this page. Open the lesson itself (not the course "
                                "list), log in if asked, and press play if the video doesn't start.")
            return {"stream": found[0], "title": page.title(), "cookies": netscape(context.cookies()),
                    "referer": page.url}
        except PlaywrightError as e:
            raise ToolError(f"The page couldn't be read ({str(e).splitlines()[0]}). If the browser window was "
                            "closed, try again and leave it open until the download starts.") from e
        finally:
            try:
                context.close()
            except PlaywrightError:
                pass  # already closed by the person


def netscape(cookies) -> str:
    """Browser cookies in the cookies.txt format the downloader reads. Kept only in a temporary file."""
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        lines.append("\t".join([c["domain"], "TRUE" if c["domain"].startswith(".") else "FALSE", c["path"],
                                "TRUE" if c["secure"] else "FALSE", str(max(0, int(c["expires"]))),
                                c["name"], c["value"]]))
    return "\n".join(lines) + "\n"
