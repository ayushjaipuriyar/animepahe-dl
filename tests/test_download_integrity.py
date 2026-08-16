"""
Regression tests for the download-completeness fixes.

These guard the bug where a 23-minute episode downloaded "successfully" as a
1-3 minute file: segments failing silently, corrupt segments being written, and
compilation reporting success without verifying the segments were all present.

No network and no ffmpeg are required — the pieces exercised here are pure logic.
"""

import os
from unittest.mock import Mock

from Crypto.Cipher import AES

KEY = b"0123456789abcdef"  # 16-byte AES key
IV = (0).to_bytes(16, "big")


def _fake_response(body: bytes):
    resp = Mock()
    resp.data = body
    return resp


# --- download_segment: never persist corrupt/empty/truncated data ---


def test_download_segment_rejects_empty_body(mock_downloader, temp_dir):
    mock_downloader.api._request.return_value = _fake_response(b"")
    out = os.path.join(temp_dir, "seg.ts")
    assert mock_downloader.download_segment("https://x/seg.ts", KEY, IV, out) == 0
    assert not os.path.exists(out), "empty body must not be written to disk"


def test_download_segment_rejects_unaligned_body(mock_downloader, temp_dir):
    # 20 bytes is not a multiple of the 16-byte AES block => truncated transfer.
    mock_downloader.api._request.return_value = _fake_response(b"x" * 20)
    out = os.path.join(temp_dir, "seg.ts")
    assert mock_downloader.download_segment("https://x/seg.ts", KEY, IV, out) == 0
    assert not os.path.exists(out), "unaligned body must not be written to disk"


def test_download_segment_accepts_aligned_body(mock_downloader, temp_dir):
    ciphertext = AES.new(KEY, AES.MODE_CBC, IV).encrypt(b"A" * 32)  # 32 = 2 blocks
    mock_downloader.api._request.return_value = _fake_response(ciphertext)
    out = os.path.join(temp_dir, "seg.ts")
    assert mock_downloader.download_segment("https://x/seg.ts", KEY, IV, out) == 32
    assert os.path.getsize(out) == 32


def test_download_segment_refetches_zero_byte_leftover(mock_downloader, temp_dir):
    out = os.path.join(temp_dir, "seg.ts")
    open(out, "wb").close()  # 0-byte leftover from a prior failed run
    ciphertext = AES.new(KEY, AES.MODE_CBC, IV).encrypt(b"B" * 16)
    mock_downloader.api._request.return_value = _fake_response(ciphertext)
    assert mock_downloader.download_segment("https://x/seg.ts", KEY, IV, out) == 16
    mock_downloader.api._request.assert_called_once()  # it did NOT skip the 0-byte file


# --- download_segments: retry failures, report incompleteness ---


def _details(n):
    return {
        "segments": [f"https://x/seg{i}.ts" for i in range(n)],
        "media_sequence": 0,
        "key_url": "https://x/key",
        "duration": float(n),
    }


def test_download_segments_retries_then_succeeds(mock_downloader, temp_dir, monkeypatch):
    calls = {"n": 0}

    def flaky(url, key, iv, output_path):
        calls["n"] += 1
        # First segment fails on its first attempt, succeeds on retry.
        if url.endswith("seg0.ts") and calls["n"] == 1:
            return 0
        open(output_path, "wb").write(b"data")
        return 4

    monkeypatch.setattr(mock_downloader, "download_segment", flaky)
    ok, failed = mock_downloader.download_segments(_details(3), KEY, temp_dir, num_threads=2)
    assert ok is True
    assert failed == []


def test_download_segments_reports_failure_after_retries(mock_downloader, temp_dir, monkeypatch):
    def always_fail_seg1(url, key, iv, output_path):
        if url.endswith("seg1.ts"):
            return 0
        open(output_path, "wb").write(b"data")
        return 4

    monkeypatch.setattr(mock_downloader, "download_segment", always_fail_seg1)
    ok, failed = mock_downloader.download_segments(
        _details(3), KEY, temp_dir, num_threads=2, max_rounds=2
    )
    assert ok is False
    assert failed == ["seg1.ts"]


# --- compile_video: refuse to merge an incomplete set (the linchpin) ---


def test_compile_video_refuses_missing_segment(mock_downloader, temp_dir):
    seg_dir = os.path.join(temp_dir, "ep")
    os.makedirs(seg_dir)
    # Playlist lists 3 segments; only 2 exist on disk.
    with open(os.path.join(seg_dir, "playlist.m3u8"), "w") as f:
        f.write("#EXTM3U\n")
        f.write('#EXT-X-KEY:METHOD=AES-128,URI="https://x/key"\n')
        for i in range(3):
            f.write("#EXTINF:10.0,\n")
            f.write(f"https://x/seg{i}.ts\n")
    open(os.path.join(seg_dir, "seg0.ts"), "wb").write(b"data")
    open(os.path.join(seg_dir, "seg1.ts"), "wb").write(b"data")
    # seg2.ts intentionally missing

    out = os.path.join(temp_dir, "out.mp4")
    assert mock_downloader.compile_video(seg_dir, out) is False
    assert not os.path.exists(out), "no output should be produced from an incomplete set"
    assert os.path.isdir(seg_dir), "segments must be preserved for resume, not deleted"


def test_compile_video_refuses_empty_segment(mock_downloader, temp_dir):
    seg_dir = os.path.join(temp_dir, "ep")
    os.makedirs(seg_dir)
    with open(os.path.join(seg_dir, "playlist.m3u8"), "w") as f:
        f.write("#EXTM3U\n")
        f.write('#EXT-X-KEY:METHOD=AES-128,URI="https://x/key"\n')
        for i in range(2):
            f.write("#EXTINF:10.0,\n")
            f.write(f"https://x/seg{i}.ts\n")
    open(os.path.join(seg_dir, "seg0.ts"), "wb").write(b"data")
    open(os.path.join(seg_dir, "seg1.ts"), "wb").close()  # present but 0 bytes

    out = os.path.join(temp_dir, "out.mp4")
    assert mock_downloader.compile_video(seg_dir, out) is False
    assert os.path.isdir(seg_dir)
