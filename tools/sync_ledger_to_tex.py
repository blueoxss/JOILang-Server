#!/usr/bin/env python3
"""WI-08: 결과 ledger ↔ result_values.tex 동기화.

- ledger: projected_results_ledger.csv
  (columns: metric_id, description, status, value, unit, source, updated_by)
  status: ANCHOR(§3 실측 앵커 — 수정 금지) / PROJECTED(예상 †) / MEASURED(repo 실측)
- †(dagger) 해제는 이 스크립트의 --ingest 만 할 수 있다. 사람이 ledger의
  status를 직접 MEASURED 로 바꾸는 것은 금지 규약이며, ingest 는
  결과 디렉토리의 meta.json 에서 llm_mode 가 mock 이 아님을 검증한 실측만 반영한다.
- --sync: MEASURED/ANCHOR 행만 tex 매크로 값으로 쓰고, PROJECTED 는 값+\dagger 로 쓴다.
  잔존 PROJECTED 행 수를 stdout 으로 보고한다. --dry-run 지원.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER = REPO / "projected_results_ledger.csv"
DEFAULT_TEX = REPO / "result_values.tex"

_DIGITS = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}


def macro_name(metric_id: str) -> str:
    parts = metric_id.replace("-", ".").replace("_", ".").split(".")
    out = "res"
    for part in parts:
        token = "".join(_DIGITS.get(ch, ch) for ch in part)
        out += token[:1].upper() + token[1:]
    return out


def load_ledger(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def save_ledger(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric_id", "description", "status", "value", "unit", "source", "updated_by"])
        writer.writeheader()
        writer.writerows(rows)


def sync_tex(rows: list[dict], tex_path: Path, *, dry_run: bool) -> dict:
    lines = [
        "% result_values.tex — tools/sync_ledger_to_tex.py 가 생성/갱신한다. 손으로 수정 금지.",
        "% PROJECTED 값은 \\dagger 가 붙는다. dagger 해제는 ingest 로 실측이 반영될 때만 일어난다.",
    ]
    projected = 0
    for row in rows:
        name = macro_name(row["metric_id"])
        value = str(row["value"]).strip()
        if row["status"] == "PROJECTED":
            projected += 1
            lines.append(f"\\newcommand{{\\{name}}}{{{value}$^\\dagger$}}")
        elif row["status"] in {"MEASURED", "ANCHOR"}:
            lines.append(f"\\newcommand{{\\{name}}}{{{value}}}")
        else:
            raise ValueError(f"unknown ledger status: {row['status']} ({row['metric_id']})")
    if not dry_run:
        tex_path.parent.mkdir(parents=True, exist_ok=True)
        tex_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"macros": len(rows), "projected_remaining": projected, "written": not dry_run}


def _real_run(meta_path: Path) -> bool:
    """ingest 자격: (a) mock 아님 (b) 실행자가 ledger_grade=true 로 표기한 본실험만.

    소규모 스모크/검증 실행이 논문 셀을 오염시키는 것을 막는다
    (실측 사례: 퇴화 스모크 런이 0.0 을 MEASURED 로 밀어넣을 뻔함).
    """
    if not meta_path.exists():
        return False
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if str((meta.get("args") or {}).get("llm_mode", "")).lower() in {"", "mock"}:
        return False
    return bool(meta.get("ledger_grade"))


def ingest(rows: list[dict], results_root: Path) -> list[str]:
    """results/* 실측을 ledger 에 반영한다. mock 실행은 절대 반영하지 않는다."""
    updated: list[str] = []
    by_id = {row["metric_id"]: row for row in rows}

    # 1) search_signal: binary vs graded
    for run in sorted((results_root / "search_signal").glob("*/binary_vs_graded_summary.csv")):
        if not _real_run(run.parent / "meta.json"):
            continue
        for record in csv.DictReader(run.open(encoding="utf-8-sig")):
            mode = record["mode"]
            for key, column, unit_scale in (
                (f"search_signal.{mode}.budget_best_detpass", "budget_best_det_pass_rate", 100.0),
                (f"search_signal.{mode}.reach_generation", "reach_generation", None),
            ):
                row = by_id.get(key)
                if row is None or row["status"] == "ANCHOR":
                    continue
                raw = record.get(column, "")
                value = round(float(raw) * unit_scale, 1) if unit_scale else raw
                row.update({"status": "MEASURED", "value": value, "source": str(run), "updated_by": "sync_ledger_to_tex.py:ingest"})
                updated.append(key)

    # 2) ablation ladder
    for run in sorted((results_root / "ablation").glob("*/ladder.csv")):
        if not _real_run(run.parent / "meta.json"):
            continue
        for record in csv.DictReader(run.open(encoding="utf-8-sig")):
            variant = record["variant"].split("_")[0]  # A0~A4
            mapping = {
                f"ablation.{variant}.detpass": (record.get("det_pass_rate"), 100.0),
                f"ablation.{variant}.replayfit_holdout": (record.get("holdout_replay_fit"), 100.0),
                f"ablation.{variant}.tokens": (record.get("avg_total_tokens"), None),
                f"ablation.{variant}.critical_regressions": (record.get("critical_regressions"), None),
            }
            for key, (raw, scale) in mapping.items():
                row = by_id.get(key)
                if row is None or row["status"] == "ANCHOR" or raw in (None, ""):
                    continue
                value = round(float(raw) * scale, 1) if scale else raw
                row.update({"status": "MEASURED", "value": value, "source": str(run), "updated_by": "sync_ledger_to_tex.py:ingest"})
                updated.append(key)

    # 3) cross transfer (paper_grade provenance 만)
    for run in sorted((results_root / "cross_transfer").glob("*/matrix.csv")):
        if not _real_run(run.parent / "meta.json"):
            continue
        for record in csv.DictReader(run.open(encoding="utf-8-sig")):
            if record.get("provenance") != "paper_grade":
                continue
            key = f"cross_transfer.{record['prompt_id']}.{record['target']}.detpass"
            row = by_id.get(key)
            if row is None or row["status"] == "ANCHOR":
                continue
            row.update(
                {
                    "status": "MEASURED",
                    "value": round(float(record["det_pass_rate"]) * 100.0, 1),
                    "source": str(run),
                    "updated_by": "sync_ledger_to_tex.py:ingest",
                }
            )
            updated.append(key)
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    parser.add_argument("--tex", default=str(DEFAULT_TEX))
    parser.add_argument("--results-root", default=str(REPO / "results"))
    parser.add_argument("--ingest", action="store_true", help="results/* 실측을 ledger 에 반영 (mock 실행 제외)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ledger_path = Path(args.ledger)
    rows = load_ledger(ledger_path)
    if args.ingest:
        updated = ingest(rows, Path(args.results_root))
        print(f"ingested (PROJECTED→MEASURED): {len(updated)} rows")
        for key in updated:
            print(f"  - {key}")
        if not args.dry_run and updated:
            save_ledger(ledger_path, rows)
    report = sync_tex(rows, Path(args.tex), dry_run=args.dry_run)
    print(f"tex macros: {report['macros']} | PROJECTED remaining: {report['projected_remaining']} | written: {report['written']}")


if __name__ == "__main__":
    main()
