"""Convenience script for GitLab Handbook-style deterministic evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.storage.app_state import GITLAB_HANDBOOK
from scripts.run_eval import print_eval_summary, run_eval_for_source


def main() -> int:
    summary, result_path = run_eval_for_source(GITLAB_HANDBOOK)
    print_eval_summary(GITLAB_HANDBOOK, summary, result_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
