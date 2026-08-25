#!/usr/bin/env python3
# Assumption: this helper never commits to main automatically; it only writes commit instructions and an optional patch file under version0_14/results.
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


VERSION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = VERSION_ROOT.parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.pipeline_common import RESULTS_DIR, dump_json, ensure_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write safe git commit instructions for version0_14 artifacts.")
    parser.add_argument("--branch", default="codex/version0_14-results")
    parser.add_argument("--message", default="Add version0_14 pipeline artifacts and results")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ensure_workspace()
    patch_path = RESULTS_DIR / "version0_14.patch"
    instructions_path = RESULTS_DIR / "commit_instructions.md"

    diff_proc = subprocess.run(
        ["git", "diff", "--", "gpt_mg/version0_14"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    patch_path.write_text(diff_proc.stdout, encoding="utf-8")

    instructions = "\n".join(
        [
            "# Commit Instructions",
            "",
            f"Suggested branch: `{args.branch}`",
            f"Suggested commit message: `{args.message}`",
            "",
            "Suggested commands:",
            "```bash",
            f"cd {REPO_ROOT}",
            f"git checkout -b {args.branch}",
            "git add gpt_mg/version0_14",
            f"git commit -m \"{args.message}\"",
            "git show --stat --oneline HEAD",
            "```",
            "",
            f"Patch file written to `{patch_path}`.",
            "This helper does not commit automatically.",
        ]
    )
    instructions_path.write_text(instructions + "\n", encoding="utf-8")
    dump_json(
        RESULTS_DIR / "commit_summary.json",
        {
            "branch": args.branch,
            "message": args.message,
            "patch_path": str(patch_path),
            "instructions_path": str(instructions_path),
        },
    )
    print(f"- patch_path: {patch_path}")
    print(f"- instructions_path: {instructions_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
