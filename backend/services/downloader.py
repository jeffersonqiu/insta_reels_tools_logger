import datetime as dt
import os
import tempfile

from yt_dlp import YoutubeDL


class DownloadError(Exception):
    pass


def download_reel_audio(instagram_url: str) -> tuple[str, dt.date | None]:
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
            filepath = ydl.prepare_filename(info)

        if not os.path.exists(filepath):
            raise DownloadError("Audio file was not created by yt-dlp.")

        upload_date = info.get("upload_date")
        parsed_date: dt.date | None = None
        if upload_date:
            parsed_date = dt.datetime.strptime(upload_date, "%Y%m%d").date()

        return filepath, parsed_date
    except Exception as exc:
        message = str(exc).lower()
        if "private" in message:
            raise DownloadError("Instagram Reel is private or inaccessible.") from exc
        if "unsupported url" in message:
            raise DownloadError("Invalid Instagram Reel URL.") from exc
        raise DownloadError(f"Failed to download reel audio: {exc}") from exc
