""" 🧪 test_music_file_manager.py — unit-тести для MusicFileManager

Перевіряє:
- Генерацію шляху до mp3
- Перевірку існування треку в кеші
- Парсинг списку треків
- Очищення кешу
- Повернення з кешу або завантаження
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from bot.music.music_file_manager import MusicFileManager


manager = MusicFileManager()
test_track = "Test Track (Live Edition)"
expected_filename = manager.get_cached_filename(test_track)


def test_get_cached_filename():
    assert expected_filename.startswith("music_cache")
    assert expected_filename.endswith(".mp3")
    assert "Test_Track_(Live_Edition)" in expected_filename


def test_is_cached_false_initially():
    if os.path.exists(expected_filename):
        os.remove(expected_filename)
    assert manager.is_cached(test_track) is False


def test_parse_song_list():
    input_text = "1. Kanye West - Stronger\n2. 2Pac - Changes"
    expected = ["Kanye West - Stronger", "2Pac - Changes"]
    result = manager.parse_song_list(input_text)
    assert result == expected


def test_clear_cache_removes_files():
    os.makedirs(manager.CACHE_DIR, exist_ok=True)
    dummy_path = os.path.join(manager.CACHE_DIR, "dummy_test.mp3")
    with open(dummy_path, "w") as f:
        f.write("dummy")

    assert os.path.exists(dummy_path)
    manager.clear_cache()
    assert not os.path.exists(dummy_path)


@patch.object(MusicFileManager, "is_cached", return_value=True)
@patch.object(MusicFileManager, "get_cached_filename", return_value="music_cache/MockTrack.mp3")
def test_find_or_download_from_cache(mock_get, mock_check):
    result = manager.find_or_download_track("MockTrack")
    assert result == "music_cache/MockTrack.mp3"

@patch("bot.music.music_file_manager.yt_dlp.YoutubeDL")
@patch("os.path.exists", return_value=True)
def test_download_from_youtube_success(mock_exists, mock_yt):
    mock_ctx = MagicMock()
    mock_yt.return_value.__enter__.return_value = mock_ctx
    path = manager.download_from_youtube("Some Track")
    assert path.endswith(".mp3")
    mock_ctx.download.assert_called_once()


@patch("bot.music.music_file_manager.yt_dlp.YoutubeDL")
@patch("os.path.exists", return_value=False)
def test_download_from_youtube_file_missing(mock_exists, mock_yt):
    mock_ctx = MagicMock()
    mock_yt.return_value.__enter__.return_value = mock_ctx

    with pytest.raises(FileNotFoundError):
        manager.download_from_youtube("Missing Track")


@patch("bot.music.music_file_manager.yt_dlp.YoutubeDL")
@patch("os.path.exists", side_effect=Exception("fail"))
def test_download_from_youtube_other_exception(mock_exists, mock_yt):
    mock_ctx = MagicMock()
    mock_yt.return_value.__enter__.return_value = mock_ctx

    with pytest.raises(Exception):
        manager.download_from_youtube("Error Track")
