"""Tests for Instagram caption extraction from yt-dlp-style metadata."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.downloader import _caption_from_ytdlp_info
from services.extractor import _build_extraction_user_prompt


def test_caption_prefers_description():
    assert _caption_from_ytdlp_info({"description": "  ruflo is cool  ", "title": "x"}) == "ruflo is cool"


def test_caption_falls_back_to_title():
    assert _caption_from_ytdlp_info({"description": "", "title": "My product launch"}) == "My product launch"


def test_caption_none_for_empty():
    assert _caption_from_ytdlp_info({"description": "", "title": "Instagram"}) is None


def test_build_prompt_includes_caption():
    p = _build_extraction_user_prompt("audio says ruflow", "ruflo")
    assert "ruflow" in p
    assert "ruflo" in p
    assert "INSTAGRAM CAPTION" in p


def test_build_prompt_without_caption():
    p = _build_extraction_user_prompt("only audio", None)
    assert "only audio" in p
    assert "not available or empty" in p
