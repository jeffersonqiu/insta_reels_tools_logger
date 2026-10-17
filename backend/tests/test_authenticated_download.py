"""Cookie secrecy, media fallback and cleanup without any Instagram requests."""

import base64
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import downloader, processing, transcriber
from test_knowledge_items import FakeSupabase


def _cookies(expiry=4102444800):
    return ("# Netscape HTTP Cookie File\n"
            f".instagram.com\tTRUE\t/\tTRUE\t{expiry}\tsessionid\tPRIVATE_VALUE\n"
            ".unrelated.example\tTRUE\t/\tTRUE\t4102444800\ttoken\tOTHER_SECRET\n")


@pytest.fixture
def media(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(downloader.settings, "instagram_cookies_b64", "")
    options_seen = []

    class FakeDownloader:
        def __init__(self, options):
            self.options = options
            options_seen.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def extract_info(self, url, download):
            cookie = self.options.get("cookiefile")
            if cookie:
                cookie_path = Path(cookie)
                assert stat.S_IMODE(cookie_path.stat().st_mode) == 0o600
                assert "PRIVATE_VALUE" in cookie_path.read_text()
                assert "OTHER_SECRET" not in cookie_path.read_text()
            audio = Path(self.options["outtmpl"]).parent / "audio.m4a"
            audio.write_bytes(b"a")
            return {"upload_date": "20260102", "description": "caption"}

        def prepare_filename(self, info):
            return str(Path(self.options["outtmpl"]).parent / "missing.m4a")

    monkeypatch.setattr(downloader, "YoutubeDL", FakeDownloader)
    return options_seen, FakeDownloader


@pytest.mark.parametrize("expiry", [4102444800, 0])
def test_cookie_passed_to_ytdlp_then_deleted_and_never_selected_as_audio(media, monkeypatch, tmp_path, expiry):
    monkeypatch.setattr(downloader.settings, "instagram_cookies_b64", base64.b64encode(_cookies(expiry).encode()).decode())
    audio, day, caption = downloader.download_reel_audio("https://www.instagram.com/reel/A/")
    assert Path(audio).name == "audio.m4a" and day.isoformat() == "2026-01-02" and caption == "caption"
    assert not Path(media[0][0]["cookiefile"]).exists()
    assert list(tmp_path.glob("reel_cookies_*")) == []
    assert Path(audio).exists()
    downloader.cleanup_reel_audio(audio)
    assert list(tmp_path.iterdir()) == []


def test_absent_cookies_allow_public_access(media):
    audio, *_ = downloader.download_reel_audio("https://www.instagram.com/reel/A/")
    assert "cookiefile" not in media[0][0]
    downloader.cleanup_reel_audio(audio)


def test_expired_cookies_fall_back_without_leaking_values(media, monkeypatch, caplog):
    monkeypatch.setattr(downloader.settings, "instagram_cookies_b64", base64.b64encode(_cookies(expiry=1).encode()).decode())
    audio, *_ = downloader.download_reel_audio("https://www.instagram.com/reel/A/")
    assert "cookiefile" not in media[0][0]
    assert "Refresh INSTAGRAM_COOKIES_B64" in caplog.text
    assert "PRIVATE_VALUE" not in caplog.text and "OTHER_SECRET" not in caplog.text
    downloader.cleanup_reel_audio(audio)


@pytest.mark.parametrize("payload", ["not-base64 PRIVATE_VALUE", base64.b64encode(b"bad PRIVATE_VALUE").decode(),
                                      base64.b64encode(b"# Netscape HTTP Cookie File\nbad PRIVATE_VALUE\n").decode()])
def test_invalid_cookies_fail_cleanly_and_remove_temporary_files(media, monkeypatch, tmp_path, capsys, caplog, payload):
    monkeypatch.setattr(downloader.settings, "instagram_cookies_b64", payload)
    with pytest.raises(downloader.DownloadError) as error:
        downloader.download_reel_audio("https://www.instagram.com/reel/A/")
    captured = capsys.readouterr()
    assert "PRIVATE_VALUE" not in str(error.value) + captured.err + captured.out + caplog.text
    assert list(tmp_path.iterdir()) == []
    assert media[0] == []


def test_login_failure_is_actionable_and_deletes_cookies_and_audio(media, monkeypatch, tmp_path):
    monkeypatch.setattr(downloader.settings, "instagram_cookies_b64", base64.b64encode(_cookies().encode()).decode())

    def fail(self, *args, **kwargs):
        raise RuntimeError("login required PRIVATE_VALUE")

    monkeypatch.setattr(media[1], "extract_info", fail)
    with pytest.raises(downloader.DownloadError, match="Refresh INSTAGRAM_COOKIES_B64") as error:
        downloader.download_reel_audio("https://www.instagram.com/reel/A/")
    assert "PRIVATE_VALUE" not in str(error.value)
    assert list(tmp_path.iterdir()) == []


def test_cookie_file_cannot_satisfy_missing_audio(media, monkeypatch, tmp_path):
    monkeypatch.setattr(downloader.settings, "instagram_cookies_b64", base64.b64encode(_cookies().encode()).decode())
    monkeypatch.setattr(media[1], "extract_info", lambda *a, **kw: {})
    with pytest.raises(downloader.DownloadError, match="Audio file was not created"):
        downloader.download_reel_audio("https://www.instagram.com/reel/A/")
    assert list(tmp_path.iterdir()) == []


def test_missing_transcription_key_still_deletes_audio(monkeypatch, tmp_path):
    path = tmp_path / "audio.m4a"
    path.write_bytes(b"audio")
    monkeypatch.setattr(transcriber.settings, "assemblyai_api_key", "")
    with pytest.raises(transcriber.TranscriptionError, match="missing"):
        transcriber.transcribe_audio_file(str(path))
    assert not path.exists()


def test_cleanup_never_deletes_an_unowned_directory(tmp_path):
    path = tmp_path / "my-audio.m4a"
    path.write_bytes(b"keep")
    downloader.cleanup_reel_audio(str(path))
    assert path.read_bytes() == b"keep"


def test_processing_cleans_download_if_metadata_persistence_fails(media, monkeypatch, tmp_path):
    db = FakeSupabase()
    db.tables["videos"] = [{"id": "v", "status": "queued", "attempt_count": 0}]
    monkeypatch.setattr(processing, "get_supabase", lambda: db)
    actual_download = downloader.download_reel_audio

    def download(url):
        result = actual_download(url)
        original_table = db.table

        def table(name):
            query = original_table(name)
            update = query.update

            def fail_metadata(payload):
                if "video_created_at" in payload:
                    raise RuntimeError("metadata unavailable")
                return update(payload)

            query.update = fail_metadata
            return query

        monkeypatch.setattr(db, "table", table)
        return result

    monkeypatch.setattr(processing, "download_reel_audio", download)
    monkeypatch.setattr(processing, "transcribe_audio_file", lambda *a: pytest.fail("Metadata write must succeed first"))
    assert "error" in processing.process_reel("v", "https://www.instagram.com/reel/A/")
    assert list(tmp_path.iterdir()) == []
    assert db.tables["videos"][0]["status"] == "failed"
