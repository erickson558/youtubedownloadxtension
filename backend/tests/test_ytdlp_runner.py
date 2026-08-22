from pathlib import Path
from unittest.mock import patch

import pytest

from ytdlx_backend.downloader.ytdlp_runner import DownloadError, download


class _FakeProcess:
    """Stands in for subprocess.Popen: yields pre-scripted stdout lines."""

    def __init__(self, lines: list[str], return_code: int = 0):
        self.stdout = iter(lines)
        self._return_code = return_code
        self._killed = False

    def wait(self) -> int:
        return self._return_code

    def poll(self):
        return self._return_code if not self._killed else -9

    def kill(self) -> None:
        self._killed = True


def test_download_invokes_subprocess_without_shell_and_with_double_dash(tmp_path: Path):
    fake_process = _FakeProcess(["download:50%|1MiB/s|00:10\n", "/tmp/video.mp4\n"])

    with patch("ytdlx_backend.downloader.ytdlp_runner.subprocess.Popen", return_value=fake_process) as mock_popen:
        result = download("https://example.com/watch?v=1", tmp_path)

    assert result == Path("/tmp/video.mp4")

    call_kwargs = mock_popen.call_args.kwargs
    call_args = mock_popen.call_args.args[0]

    # specs/03-security-spec.md item 1 / rule 1: never shell=True.
    assert call_kwargs["shell"] is False

    # A literal "--" must immediately precede the URL, so a URL crafted to
    # start with "-" can never be parsed as a yt-dlp flag.
    assert call_args[-2] == "--"
    assert call_args[-1] == "https://example.com/watch?v=1"


def test_download_reports_progress_via_callback(tmp_path: Path):
    fake_process = _FakeProcess(["download:10%|500KiB/s|00:30\n", "/tmp/video.mp4\n"])
    seen = []

    with patch("ytdlx_backend.downloader.ytdlp_runner.subprocess.Popen", return_value=fake_process):
        download("https://example.com/watch?v=1", tmp_path, on_progress=lambda p, s, e: seen.append((p, s, e)))

    assert seen == [("10%", "500KiB/s", "00:30")]


def test_download_raises_on_nonzero_exit(tmp_path: Path):
    fake_process = _FakeProcess(["some error output\n"], return_code=1)

    with patch("ytdlx_backend.downloader.ytdlp_runner.subprocess.Popen", return_value=fake_process):
        with pytest.raises(DownloadError):
            download("https://example.com/watch?v=1", tmp_path)


def test_download_raises_when_no_final_path_reported(tmp_path: Path):
    fake_process = _FakeProcess(["download:100%|0KiB/s|00:00\n"], return_code=0)

    with patch("ytdlx_backend.downloader.ytdlp_runner.subprocess.Popen", return_value=fake_process):
        with pytest.raises(DownloadError):
            download("https://example.com/watch?v=1", tmp_path)
