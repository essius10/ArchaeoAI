"""Refuse any second E001 Phase 3C external scoring run.

The one authorized run completed on 2026-08-30. This retained entry point makes
the spent-test state explicit and machine-enforced.
"""

from pathlib import Path

from archaeoai.external_evaluation import assert_external_test_spent

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    assert_external_test_spent(
        ROOT / "outputs/external_validation/e001_phase3c_external_evaluation.json"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
