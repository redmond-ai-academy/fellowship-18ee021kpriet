"""Offline tests for your setup. Run: python -m pytest week00

They pass on a working machine with no network. A missing .env is only a warning here,
because you may not have your API key yet.
"""

import warnings

import pytest

import check_setup as cs


def test_no_offline_check_fails():
    failures = [r for r in cs.offline_checks() if r.status == cs.FAIL]
    assert not failures, "\n".join(f"{r.name}: {r.detail}. {r.hint}" for r in failures)


def test_warnings_are_reported_not_failed():
    for r in cs.offline_checks():
        if r.status == cs.WARN:
            warnings.warn(f"{r.name}: {r.detail}", stacklevel=1)


def test_missing_env_file_is_a_warning(tmp_path):
    assert cs.check_env_key(tmp_path).status == cs.WARN


def test_empty_key_is_a_warning(tmp_path):
    (tmp_path / ".env").write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    assert cs.check_env_key(tmp_path).status == cs.WARN


def test_key_is_never_printed(tmp_path):
    secret = "not-a-real-key-123456"
    (tmp_path / ".env").write_text(f"GEMINI_API_KEY={secret}\n", encoding="utf-8")

    result = cs.check_env_key(tmp_path)

    assert result.status == cs.PASS
    assert secret not in f"{result.name} {result.detail} {result.hint}"


@pytest.mark.parametrize("version", [(3, 11, 0), (3, 12, 0), (3, 14, 1)])
def test_python_version_rule(monkeypatch, version):
    monkeypatch.setattr(cs.sys, "version_info", version + ("final", 0))
    expected = cs.FAIL if version < (3, 12) else cs.PASS
    assert cs.check_python().status == expected
