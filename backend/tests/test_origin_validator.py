from ytdlx_backend.security.origin_validator import (
    ALLOWED_FIREFOX_EXTENSION_IDS,
    is_allowed_caller,
)


def test_rejects_call_with_no_argv_identity():
    assert is_allowed_caller(["ytdlx_backend.exe"]) is False


def test_accepts_known_firefox_extension_id():
    known_id = next(iter(ALLOWED_FIREFOX_EXTENSION_IDS))
    assert is_allowed_caller(["ytdlx_backend.exe", known_id]) is True


def test_rejects_unknown_firefox_extension_id():
    assert is_allowed_caller(["ytdlx_backend.exe", "someone-elses-extension@example.com"]) is False


def test_rejects_chrome_origin_when_allow_list_is_empty():
    # ALLOWED_CHROME_ORIGINS ships empty until the real Chrome Web Store id
    # is added — this must fail closed, not implicitly allow every caller
    # (specs/03-security-spec.md: never wildcard, never implicitly permissive).
    assert is_allowed_caller(["ytdlx_backend.exe", "chrome-extension://any-id-at-all/"]) is False
