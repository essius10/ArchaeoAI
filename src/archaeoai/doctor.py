"""Data-free, cross-platform environment diagnostics for ArchaeoAI."""

from __future__ import annotations

import importlib
import json
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

SUPPORTED_PYTHON_MIN = (3, 12)
SUPPORTED_PYTHON_MAX = (3, 15)
RUNTIME_DISTRIBUTIONS = {
    "archaeoai": "archaeoai",
    "numpy": "numpy",
    "pyproj": "pyproj",
    "rasterio": "rasterio",
    "scipy": "scipy",
    "sklearn": "scikit-learn",
    "torch": "torch",
}
DEVELOPMENT_DISTRIBUTIONS = {"pytest": "pytest", "ruff": "ruff"}


def is_supported_runtime(
    version: tuple[int, int, int] | tuple[int, int],
    implementation: str,
) -> bool:
    """Return whether a runtime satisfies the project's declared Python policy."""
    major_minor = version[:2]
    return (
        implementation.casefold() == "cpython"
        and SUPPORTED_PYTHON_MIN <= major_minor < SUPPORTED_PYTHON_MAX
    )


def _run(command: list[str], *, cwd: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "output": "", "error": str(exc)}
    output = (result.stdout or result.stderr).strip()
    return {"ok": result.returncode == 0, "output": output, "returncode": result.returncode}


def _package_versions(errors: list[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for import_name, distribution_name in {
        **RUNTIME_DISTRIBUTIONS,
        **DEVELOPMENT_DISTRIBUTIONS,
    }.items():
        try:
            importlib.import_module(import_name)
            versions[distribution_name] = metadata.version(distribution_name)
        except (ImportError, metadata.PackageNotFoundError, OSError, RuntimeError) as exc:
            errors.append(f"{distribution_name} is unavailable: {exc}")
    return versions


def collect_environment_report(project_root: str | Path) -> dict[str, Any]:
    """Collect a coordinate-free report and record every failed requirement."""
    root = Path(project_root).resolve()
    errors: list[str] = []
    version = tuple(sys.version_info[:3])
    implementation = sys.implementation.name
    if not (root / "pyproject.toml").is_file():
        errors.append(f"not an ArchaeoAI project directory: {root}")
    if not is_supported_runtime(version, implementation):
        errors.append("unsupported Python runtime; ArchaeoAI requires CPython >=3.12,<3.15")

    packages = _package_versions(errors)
    geospatial: dict[str, Any] = {}
    try:
        pyproj = importlib.import_module("pyproj")
        rasterio = importlib.import_module("rasterio")
        geospatial = {
            "epsg_27700": pyproj.CRS.from_epsg(27700).name,
            "gdal": rasterio.__gdal_version__,
            "proj": pyproj.proj_version_str,
        }
    except (AttributeError, ImportError, RuntimeError) as exc:
        errors.append(f"geospatial smoke test failed: {exc}")

    torch_runtime: dict[str, Any] = {}
    try:
        torch = importlib.import_module("torch")
        cuda_available = bool(torch.cuda.is_available())
        torch_runtime = {
            "cuda_available": cuda_available,
            "cuda_runtime": torch.version.cuda,
            "device_count": torch.cuda.device_count(),
            "device_name": torch.cuda.get_device_name(0) if cuda_available else None,
        }
    except (AttributeError, ImportError, RuntimeError) as exc:
        errors.append(f"PyTorch smoke test failed: {exc}")

    git_version = _run(["git", "--version"], cwd=root)
    git_status = _run(["git", "status", "--short", "--branch"], cwd=root)
    pip_check = _run([sys.executable, "-m", "pip", "check"], cwd=root)
    if not git_version["ok"]:
        errors.append("Git is unavailable")
    if not git_status["ok"]:
        errors.append("Git could not inspect this repository")
    if not pip_check["ok"]:
        errors.append(f"pip check failed: {pip_check['output']}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "project_root": str(root),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": {
            "implementation": implementation,
            "version": ".".join(map(str, version)),
            "executable": sys.executable,
        },
        "packages": packages,
        "geospatial": geospatial,
        "torch": torch_runtime,
        "git": {"version": git_version, "status": git_status},
        "pip_check": pip_check,
        "errors": errors,
    }


def format_text_report(report: dict[str, Any]) -> str:
    """Render a concise human-readable report without exposing private research data."""
    lines = [
        f"ArchaeoAI cross-platform environment check: {report['status']}",
        f"Platform: {report['platform']['system']} {report['platform']['release']} "
        f"({report['platform']['machine']})",
        f"Python: {report['python']['implementation']} {report['python']['version']}",
        f"Python executable: {report['python']['executable']}",
    ]
    lines.extend(f"{name}: {version}" for name, version in sorted(report["packages"].items()))
    if report["geospatial"]:
        lines.append(
            "Raster stack: "
            f"GDAL {report['geospatial']['gdal']} / PROJ {report['geospatial']['proj']}"
        )
        lines.append(f"CRS smoke test: EPSG:27700 = {report['geospatial']['epsg_27700']}")
    if report["torch"]:
        lines.append(
            "Torch CUDA available/runtime: "
            f"{report['torch']['cuda_available']} / {report['torch']['cuda_runtime']}"
        )
    lines.append(f"Git: {report['git']['version']['output']}")
    lines.append(f"Git status: {report['git']['status']['output'].replace(chr(10), ' | ')}")
    lines.append(f"pip check: {'PASS' if report['pip_check']['ok'] else 'FAIL'}")
    lines.extend(f"ERROR: {error}" for error in report["errors"])
    return "\n".join(lines)


def main(argv: list[str] | None = None, *, default_root: str | Path | None = None) -> int:
    """Run the doctor from any operating system and return a shell-friendly status."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    json_output = False
    if "--json" in arguments:
        arguments.remove("--json")
        json_output = True
    if len(arguments) > 1:
        print("usage: python scripts/doctor.py [PROJECT_ROOT] [--json]", file=sys.stderr)
        return 2
    root = Path(arguments[0]) if arguments else Path(default_root or Path.cwd())
    report = collect_environment_report(root)
    print(
        json.dumps(report, indent=2, sort_keys=True) if json_output else format_text_report(report)
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
