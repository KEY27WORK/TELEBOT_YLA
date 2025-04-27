"""
🧪 test_music_sender.py — unit-тести для MusicSender

Перевіряє:
- Форматування списку треків у HTML-вид
- Парсинг списку треків
- Групування по розміру
- Завантаження треків з YouTube (mock)
- Повну відправку (mock Telegram)
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from bot.music.music_sender import MusicSender


sender = MusicSender()
sample_tracks = ["Eminem - Lose Yourself", "2Pac - Changes"]


def test_format_track_list_structure():
    result = sender.format_track_list(sample_tracks)
    assert result.startswith("🎵 <b>Музика для поста:</b>")


def test_format_track_list_contains_tracks():
    result = sender.format_track_list(sample_tracks)
    assert "1. Eminem - Lose Yourself" in result
    assert "2. 2Pac - Changes" in result


def test_parse_song_list():
    music_text = "1. Drake - God's Plan\n2. Travis Scott - SICKO MODE"
    expected = ["Drake - God's Plan", "Travis Scott - SICKO MODE"]
    result = sender.parse_song_list(music_text)
    assert result == expected


@patch("os.path.getsize")
def test_group_by_size(mock_getsize):
    # кожен трек 10MB
    mock_getsize.return_value = 10 * 1024 * 1024
    fake_tracks = [(f"Track {i}", f"track{i}.mp3") for i in range(7)]

    grouped = sender.group_by_size(fake_tracks)

    assert len(grouped) == 2  # 5 + 2
    assert sum(len(g) for g in grouped) == 7


@patch.object(sender.manager, "find_or_download_track")
@pytest.mark.asyncio
async def test_download_all_tracks_success(mock_download):
    mock_download.side_effect = lambda name: f"{name}.mp3"
    result = await sender.download_all_tracks(["One", "Two"])
    assert result == [("One", "One.mp3"), ("Two", "Two.mp3")]


@patch.object(sender.manager, "find_or_download_track")
@pytest.mark.asyncio
async def test_download_all_tracks_partial_fail(mock_download):
    def fake_download(name):
        if name == "Bad":
            raise Exception("fail")
        return f"{name}.mp3"

    mock_download.side_effect = fake_download
    result = await sender.download_all_tracks(["Good", "Bad"])
    assert result == [("Good", "Good.mp3"), ("Bad", None)]


@patch("os.path.getsize", return_value=5 * 1024 * 1024)
@patch("bot.music.music_sender.InputMediaAudio")
@patch.object(sender, "download_all_tracks")
@pytest.mark.asyncio
async def test_send_all_tracks_success(mock_download, mock_media, mock_size):
    mock_download.return_value = [("Track1", "mock1.mp3")]
    mock_media.side_effect = lambda **kwargs: f"audio: {kwargs['caption']}"

    update = MagicMock()
    update.message.chat.send_action = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.message.reply_media_group = AsyncMock()

    context = MagicMock()

    with patch("builtins.open", mock_open(read_data=b"fakeaudio")):
        await sender.send_all_tracks(update, context, ["Track1"])

    update.message.reply_text.assert_any_await("✅ Успішно надіслано 1 треків 🎧", parse_mode="HTML")



@patch.object(sender.manager, "clear_cache")
def test_clear_cache_called(mock_clear):
    sender.clear_cache()
    mock_clear.assert_called_once()
