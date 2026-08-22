from pathlib import Path

import pytest

from ytdlx_backend.security.path_sanitizer import (
    UnsafePathError,
    sanitize_filename,
    validate_save_path,
)


def test_sanitize_filename_strips_path_separators():
    assert sanitize_filename("My/Video\\Title") == "MyVideoTitle"


def test_sanitize_filename_falls_back_when_empty_after_cleaning():
    assert sanitize_filename("///:::") == "video"


def test_validate_save_path_accepts_path_inside_root(tmp_path: Path):
    root = tmp_path
    result = validate_save_path(root / "video.mp4", root)
    assert result == (root / "video.mp4").resolve()


def test_validate_save_path_rejects_dotdot_segment(tmp_path: Path):
    with pytest.raises(UnsafePathError):
        validate_save_path(tmp_path / ".." / "escaped.mp4", tmp_path)


def test_validate_save_path_rejects_path_outside_root(tmp_path: Path):
    outside = tmp_path.parent / "outside.mp4"
    with pytest.raises(UnsafePathError):
        validate_save_path(outside, tmp_path)


def test_validate_save_path_rejects_unc_path_by_default(tmp_path: Path):
    with pytest.raises(UnsafePathError):
        validate_save_path(r"\\server\share\video.mp4", tmp_path)
