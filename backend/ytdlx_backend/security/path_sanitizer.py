"""Validates every filesystem path this app writes to.

Per specs/03-security-spec.md item 4 and the non-negotiable rules at the
bottom of that spec: every path written to disk must pass through this
module first. The user-chosen save folder (from the native folder-picker
dialog, see specs/02-native-host-spec.md) is trusted as the *root*; anything
derived from web-page-controlled data (the video title, used to build the
output filename) is not trusted and is checked against that root.
"""

from __future__ import annotations

from pathlib import Path, PureWindowsPath


class UnsafePathError(ValueError):
    """Raised when a candidate path fails validation."""


def _looks_like_unc_path(path: Path) -> bool:
    # PureWindowsPath handles UNC (\\server\share\...) detection correctly
    # regardless of the OS this happens to run on.
    return PureWindowsPath(str(path)).drive.startswith("\\\\")


def sanitize_filename(name: str, fallback: str = "video") -> str:
    """Strips path separators and other filesystem-hostile characters from a
    filename derived from untrusted page metadata (e.g. the video title).
    Never returns an empty string.
    """
    forbidden = set('<>:"/\\|?*') | {chr(c) for c in range(0, 32)}
    cleaned = "".join(c for c in name if c not in forbidden).strip(" .")
    return cleaned or fallback


def validate_save_path(candidate: Path | str, allowed_root: Path | str, *, allow_unc: bool = False) -> Path:
    """Confirms `candidate` resolves to a real path inside `allowed_root`.

    Raises UnsafePathError if:
      - `candidate` contains a literal ".." segment (rejected outright,
        not just resolved away — a resolved path that happens to still
        land inside the root is not good enough evidence of intent),
      - the resolved absolute path is not inside `allowed_root`,
      - the path is a UNC/network path and `allow_unc` is False.
    """
    candidate = Path(candidate)
    allowed_root = Path(allowed_root).resolve()

    if ".." in candidate.parts:
        raise UnsafePathError(f"path contains a '..' segment: {candidate}")

    if not allow_unc and _looks_like_unc_path(candidate):
        raise UnsafePathError(f"UNC/network paths are not allowed: {candidate}")

    resolved = (allowed_root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()

    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise UnsafePathError(
            f"resolved path {resolved} escapes the user-chosen root {allowed_root}"
        ) from exc

    return resolved
