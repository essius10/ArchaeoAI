"""Run ArchaeoAI's data-free environment doctor on any supported platform."""

from pathlib import Path

from archaeoai.doctor import main

if __name__ == "__main__":
    raise SystemExit(main(default_root=Path(__file__).resolve().parents[1]))
