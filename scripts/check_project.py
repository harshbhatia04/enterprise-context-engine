"""Lightweight repository health checks for CI and local development."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

KEY_MODULES = [
    "app.main",
    "app.generation.answer_generator",
    "app.evaluation.eval_runner",
    "app.storage.app_state",
]

REQUIRED_DOCS = [
    "README.md",
    "SECURITY.md",
    "docs/ARCHITECTURE.md",
    "docs/EVALUATION.md",
    "docs/SECURITY.md",
    "docs/DEMO_SCRIPT.md",
]

REQUIRED_SCRIPTS = [
    "scripts/run_eval.py",
    "scripts/create_sample_docs.py",
    "scripts/create_gitlab_fixture_docs.py",
]


def main() -> int:
    for module_name in KEY_MODULES:
        importlib.import_module(module_name)

    missing = [
        relative_path
        for relative_path in [*REQUIRED_DOCS, *REQUIRED_SCRIPTS]
        if not (PROJECT_ROOT / relative_path).exists()
    ]
    if missing:
        print("Project check failed. Missing required files:")
        for relative_path in missing:
            print(f"- {relative_path}")
        return 1

    print("Project check passed: imports, docs, and required scripts are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
