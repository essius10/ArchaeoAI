from pathlib import Path

from archaeoai.doctor import format_text_report, is_supported_runtime


def test_supported_runtime_policy_boundaries() -> None:
    assert is_supported_runtime((3, 12, 0), "cpython")
    assert is_supported_runtime((3, 14, 99), "CPython")
    assert not is_supported_runtime((3, 11, 9), "cpython")
    assert not is_supported_runtime((3, 15, 0), "cpython")
    assert not is_supported_runtime((3, 12, 0), "pypy")


def test_text_report_surfaces_failures() -> None:
    report = {
        "status": "FAIL",
        "project_root": str(Path("project")),
        "platform": {"system": "TestOS", "release": "1", "machine": "test64"},
        "python": {"implementation": "cpython", "version": "3.12.0", "executable": "python"},
        "packages": {"archaeoai": "0.1.0"},
        "geospatial": {},
        "torch": {},
        "git": {
            "version": {"ok": True, "output": "git version test"},
            "status": {"ok": True, "output": "## main"},
        },
        "pip_check": {"ok": False, "output": "broken dependency"},
        "errors": ["pip check failed: broken dependency"],
    }

    text = format_text_report(report)

    assert "environment check: FAIL" in text
    assert "pip check: FAIL" in text
    assert "ERROR: pip check failed: broken dependency" in text
