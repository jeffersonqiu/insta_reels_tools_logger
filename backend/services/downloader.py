import datetime as dt
import os
import tempfile

from yt_dlp import YoutubeDL


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
    }

    try:
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
        message = str(exc).lower()
        if "private" in message:
            raise DownloadError("Instagram Reel is private or inaccessible.") from exc
        if "unsupported url" in message:
            raise DownloadError("Invalid Instagram Reel URL.") from exc
        raise DownloadError(f"Failed to download reel audio: {exc}") from exc
