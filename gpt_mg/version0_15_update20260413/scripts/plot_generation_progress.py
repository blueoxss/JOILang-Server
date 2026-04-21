#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROGRESS_CSV = VERSION_ROOT / "results" / "ga_generation_progress.csv"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot GA generation progress from ga_generation_progress.csv.")
    parser.add_argument(
        "--progress-csv",
        default=str(DEFAULT_PROGRESS_CSV),
        help="Progress CSV exported by run_ga_search.py. Default: results/ga_generation_progress.csv",
    )
    parser.add_argument(
        "--output-json",
        default=str(VERSION_ROOT / "results" / "ga_generation_progress_plot.json"),
        help="Structured summary output path.",
    )
    parser.add_argument(
        "--output-png",
        default=str(VERSION_ROOT / "results" / "ga_generation_progress_plot.png"),
        help="Optional PNG chart path. A note is written into the JSON when matplotlib is unavailable.",
    )
    return parser


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _plot_png(rows: list[dict[str, Any]], output_png: Path) -> str:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        return f"PNG skipped: matplotlib unavailable ({exc})"

    generations = [_to_float(row.get("generation")) for row in rows]
    train_det = [_to_float(row.get("train_avg_det_score")) for row in rows]
    valid_det = [_to_float(row.get("validation_avg_det_score")) for row in rows]
    det_pass = [_to_float(row.get("validation_det_pass_rate")) for row in rows]
    replay_proxy = [_to_float(row.get("replay_acc_rate_proxy")) for row in rows]
    fitness = [_to_float(row.get("fitness")) for row in rows]

    figure, axes = plt.subplots(3, 1, figsize=(10, 12), constrained_layout=True)
    axes[0].plot(generations, train_det, marker="o", label="train_avg_det_score")
    axes[0].plot(generations, valid_det, marker="s", label="validation_avg_det_score")
    axes[0].set_title("DET score by generation")
    axes[0].set_xlabel("generation")
    axes[0].legend()

    axes[1].plot(generations, det_pass, marker="o", label="validation_det_pass_rate")
    axes[1].plot(generations, replay_proxy, marker="s", label="replay_acc_rate_proxy")
    axes[1].set_title("Validation pass/exact proxy by generation")
    axes[1].set_xlabel("generation")
    axes[1].legend()

    axes[2].plot(generations, fitness, marker="o", label="fitness")
    axes[2].set_title("Fitness by generation")
    axes[2].set_xlabel("generation")
    axes[2].legend()

    output_png.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_png, dpi=180)
    plt.close(figure)
    return f"PNG saved to {output_png}"


def main() -> int:
    args = build_parser().parse_args()
    progress_csv = Path(args.progress_csv).expanduser().resolve()
    if not progress_csv.exists():
        raise SystemExit(f"Progress CSV not found: {progress_csv}")
    rows = _load_rows(progress_csv)
    if not rows:
        raise SystemExit(f"No rows found in progress CSV: {progress_csv}")

    output_json = Path(args.output_json).expanduser().resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_png = Path(args.output_png).expanduser().resolve()
    png_status = _plot_png(rows, output_png)

    summary = {
        "progress_csv": str(progress_csv),
        "output_png": str(output_png),
        "png_status": png_status,
        "row_count": len(rows),
        "first_generation": rows[0],
        "last_generation": rows[-1],
    }
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
