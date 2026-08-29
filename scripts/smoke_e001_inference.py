"""Run a coordinate-free synthetic CPU smoke benchmark for frozen Phase 2F-A."""

from __future__ import annotations

import ctypes
import json
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

import numpy as np

from archaeoai.inference import (
    STRIDE_M,
    PixelWindow,
    PrivateScoredWindow,
    deduplicate_ranked,
    features_from_elevation,
    load_private_model,
    safe_public_summary,
    score_feature_matrix,
    select_review_queues,
    validate_inference_protocol,
)


def _windows_peak_working_set_bytes() -> int | None:
    if not hasattr(ctypes, "windll"):
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    process = kernel32.GetCurrentProcess()
    success = psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb)
    return int(counters.PeakWorkingSetSize) if success else None


def _synthetic_patch(index: int) -> tuple[np.ndarray, np.ndarray]:
    y, x = np.mgrid[-64:64, -64:64]
    radius = 180.0 + index * 3.0
    mound = (0.2 + index / 80) * np.exp(-((x**2 + y**2) / radius))
    plane = x * (index % 5 - 2) * 0.0005 + y * (index % 3 - 1) * 0.0004
    ripple = 0.01 * np.sin((x + index) / 9.0) * np.cos((y - index) / 11.0)
    return np.asarray(mound + plane + ripple, dtype=np.float32), np.zeros((128, 128), bool)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol_path = root / "configs/e001-phase-2f-a-inference-protocol.json"
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(protocol_path.relative_to(root))],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if tracked.returncode != 0:
        raise ValueError("refusing synthetic smoke test until the Phase 2F-A protocol is committed")
    protocol = validate_inference_protocol(protocol_path)
    model_path = root / "data/private/e001/inference/e001_phase2f_random_forest.pkl"
    load_started = time.perf_counter()
    model = load_private_model(
        root,
        model_path,
        expected_artifact_sha256=protocol["model"]["private_model_artifact_sha256"],
        expected_state_sha256=protocol["model"]["model_state_sha256"],
    )
    model_load_seconds = time.perf_counter() - load_started

    patch_count = 32
    preprocessing_started = time.perf_counter()
    features = np.asarray(
        [features_from_elevation(*_synthetic_patch(index)) for index in range(patch_count)],
        dtype=np.float32,
    )
    preprocessing_seconds = time.perf_counter() - preprocessing_started

    repetitions = 100
    scoring_started = time.perf_counter()
    for _repeat in range(repetitions):
        scores = score_feature_matrix(model, features)
    scoring_seconds = time.perf_counter() - scoring_started
    scored = tuple(
        PrivateScoredWindow(PixelWindow(f"synthetic-{index:03d}", index * 256, 0), float(score))
        for index, score in enumerate(scores)
    )
    representatives = deduplicate_ranked(scored)
    queues = select_review_queues(representatives)
    aggregate = safe_public_summary(
        total_windows=patch_count,
        valid_scores=scores,
        rejected_windows=0,
        no_data_windows=0,
        representative_count=len(representatives),
        queues=queues,
        model_state_checksum=protocol["model"]["model_state_sha256"],
    )
    model_patches_per_second = patch_count * repetitions / scoring_seconds
    preprocessing_patches_per_second = patch_count / preprocessing_seconds
    end_to_end_seconds = preprocessing_seconds + scoring_seconds / repetitions
    end_to_end_patches_per_second = patch_count / end_to_end_seconds
    output = {
        "phase": "2F-A",
        "status": "READY_NO_REAL_SCAN",
        "protocol_sha256": protocol["protocol_sha256"],
        "benchmark_scope": "synthetic_coordinate_free_CPU_smoke_only",
        "synthetic_patch_count": patch_count,
        "model_load_seconds": model_load_seconds,
        "terrain_preprocessing_seconds": preprocessing_seconds,
        "terrain_preprocessing_patches_per_second": preprocessing_patches_per_second,
        "model_scoring_repetitions": repetitions,
        "model_scoring_seconds": scoring_seconds,
        "model_patches_per_second": model_patches_per_second,
        "model_latency_ms_per_patch": 1000 / model_patches_per_second,
        "end_to_end_patches_per_second": end_to_end_patches_per_second,
        "estimated_incremental_grid_area_km2_per_hour_in_memory_synthetic_upper_bound": (
            end_to_end_patches_per_second * STRIDE_M**2 * 3600 / 1_000_000
        ),
        "private_model_size_bytes": model_path.stat().st_size,
        "process_peak_working_set_bytes": _windows_peak_working_set_bytes(),
        "bottleneck": "terrain_representation_and_pooling",
        "benchmark_excludes": ["terrain_download", "GeoTIFF_IO", "mosaicking"],
        "backend_feasibility": "FEASIBLE_FOR_BOUNDED_RESEARCH_DEMO",
        "CPU_feasibility": True,
        "GPU_required": False,
        "safe_API_fields": protocol["safe_API"]["allowed_fields"],
        "never_public_API_fields": protocol["safe_API"]["never_expose"],
        "aggregate_synthetic_smoke": aggregate,
        "privacy": {
            "real_terrain_loaded": False,
            "real_candidate_scan_completed": False,
            "candidate_locations_created": False,
            "candidate_locations_exposed": False,
            "synthetic_per_patch_scores_written": False,
            "aggregate_only": True,
        },
    }
    destination = root / "outputs/inference/e001_phase2f_a_readiness.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
