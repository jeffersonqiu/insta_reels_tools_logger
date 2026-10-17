import base64
import binascii
import datetime as dt
import http.cookiejar
import logging
import os
from pathlib import Path
import shutil
import tempfile
import warnings

from yt_dlp import YoutubeDL

from config import settings

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    pass


def _caption_from_ytdlp_info(info: dict | None) -> str | None:
    """Instagram Reel caption from yt-dlp metadata (usually `description`)."""
    if not isinstance(info, dict):
        return None
    desc = (info.get("description") or "").strip()
    if desc:
        return desc
    title = (info.get("title") or "").strip()
    # Some extractors only populate title; avoid useless generic titles
    if title and title.lower() not in ("instagram", "instagram reel", "reel", "video"):
        return title
    return None


def _cookiefile_from_b64(cookie_dir: str) -> str | None:
    """Validate cookies without exposing their values; keep only Instagram cookies."""
    raw = settings.instagram_cookies_b64.strip()
    if not raw:
        return None
    try:
        content = base64.b64decode(raw, validate=True).decode("utf-8").replace("\r\n", "\n")
    except (binascii.Error, ValueError, UnicodeError):
        raise DownloadError("INSTAGRAM_COOKIES_B64 must contain base64-encoded Netscape cookies.") from None
    # yt-dlp accepts expiry 0 as a session cookie; stdlib cookiejar expects an
    # empty field. Normalize it before filtering genuinely expired cookies.
    lines = []
    for line in content.splitlines():
        fields = line.split("\t")
        if len(fields) == 7 and fields[4] == "0":
            fields[4] = ""
            line = "\t".join(fields)
        lines.append(line)
    content = "\n".join(lines) + "\n"
    path = os.path.join(cookie_dir, "instagram_cookies.txt")
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as stream:
        stream.write(content)
    jar = http.cookiejar.MozillaCookieJar(path)
    try:
        # cookiejar may otherwise emit a parser traceback containing cookie data.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            jar.load(ignore_discard=True, ignore_expires=False)
    except (http.cookiejar.LoadError, ValueError, OSError):
        raise DownloadError("Instagram cookies are not a valid Netscape cookies file. Re-export them.") from None
    for cookie in list(jar):
        domain = cookie.domain.lstrip(".").lower()
        if domain != "instagram.com" and not domain.endswith(".instagram.com"):
            jar.clear(cookie.domain, cookie.path, cookie.name)
    if not list(jar):
        logger.warning("No unexpired Instagram cookies found; trying public access. Refresh INSTAGRAM_COOKIES_B64 if login is required.")
        return None
    jar.save(ignore_discard=True, ignore_expires=False)
    return path


def cleanup_reel_audio(audio_path: str) -> None:
    """Remove only a downloader-owned directory directly inside the temp root."""
    parent = Path(audio_path).resolve().parent
    if parent.name.startswith("reel_audio_") and parent.parent == Path(tempfile.gettempdir()).resolve():
        shutil.rmtree(parent, ignore_errors=True)


def download_reel_audio(instagram_url: str) -> tuple[str, dt.date | None, str | None]:
    temp_dir = tempfile.mkdtemp(prefix="reel_audio_")
    output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")
    options = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "writeinfojson": False,
        "outtmpl": output_template,
        "socket_timeout": 30,
        "retries": 2,
        "extractor_retries": 1,
        "noplaylist": True,
    }

    try:
        # Cookies have a separate lifetime and directory: media-file fallback
        # selection can never mistake a credentials file for downloaded audio.
        with tempfile.TemporaryDirectory(prefix="reel_cookies_") as cookie_dir:
            cookiefile = _cookiefile_from_b64(cookie_dir)
            if cookiefile:
                options["cookiefile"] = cookiefile
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(instagram_url, download=True)
            # After download, real path is often in info["filepath"], not prepare_filename(info)
            filepath = info.get("filepath") if isinstance(info, dict) else None
            if not filepath or not os.path.exists(filepath):
                filepath = ydl.prepare_filename(info)
            if not os.path.exists(filepath):
                # Fallback: largest non-temp file under temp_dir
                candidates: list[str] = []
                for root, _, files in os.walk(temp_dir):
                    for name in files:
                        if name.endswith((".part", ".ytdl")):
                            continue
                        full = os.path.join(root, name)
                        if os.path.isfile(full):
                            candidates.append(full)
                if not candidates:
                    raise DownloadError("Audio file was not created by yt-dlp.")
                filepath = max(candidates, key=lambda p: os.path.getsize(p))

        if not os.path.exists(filepath):
            raise DownloadError("Audio file was not created by yt-dlp.")

        upload_date = info.get("upload_date")
        parsed_date: dt.date | None = None
        if upload_date:
            parsed_date = dt.datetime.strptime(upload_date, "%Y%m%d").date()

        caption = _caption_from_ytdlp_info(info if isinstance(info, dict) else None)

        return filepath, parsed_date, caption
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if isinstance(exc, DownloadError):
            raise
        message = str(exc).lower()
        if any(word in message for word in ("login required", "log in", "rate-limit", "rate limit", "cookies", "requested content is not available")):
            raise DownloadError("Instagram requires login or is rate-limiting downloads. Refresh INSTAGRAM_COOKIES_B64 and resubmit the Reel.") from None
        if "private" in message:
            raise DownloadError("Instagram Reel is private or inaccessible.") from exc
        if "unsupported url" in message:
            raise DownloadError("Invalid Instagram Reel URL.") from exc
        raise DownloadError(f"Failed to download reel audio: {exc}") from exc
