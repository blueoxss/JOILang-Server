#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VERSION_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = VERSION_ROOT / "results"

GT_SCRIPT_RE = re.compile(r'"script"\s*:\s*"(?P<script>(?:[^"\\]|\\.)*)"', re.DOTALL)
VALUE_CHAIN_RE = re.compile(r"\)\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+\(")
PIPE_ARGS_RE = re.compile(r"\([^)]*\|[^)]*\)")


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    return _safe_text(value).lower() in {"1", "true", "yes", "y"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except Exception:
        return default


def _load_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _extract_gt_code(row: dict[str, Any]) -> str:
    direct = _safe_text(row.get("gt_code"))
    if direct:
        return direct
    raw = _safe_text(row.get("gt"))
    if not raw:
        return ""
    match = GT_SCRIPT_RE.search(raw)
    if not match:
        return ""
    text = match.group("script")
    return bytes(text, "utf-8").decode("unicode_escape")


def _parse_failure_reasons(raw: Any) -> list[str]:
    text = _safe_text(raw)
    if not text:
        return []
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            return [_safe_text(item) for item in payload if _safe_text(item)]
    except Exception:
        pass
    return [part.strip() for part in text.strip("[]").split(",") if part.strip()]


def _recommend_files(failure_reasons: list[str], generated_code: str) -> list[str]:
    files: list[str] = []
    joined = " ".join(failure_reasons)
    if "dataflow" in joined or VALUE_CHAIN_RE.search(generated_code):
        files.extend(["caution_prompt_8.md", "grammar_ver1.5.10.md", "response_prompt_baseline_cot.md"])
    if "arg_type" in joined or PIPE_ARGS_RE.search(generated_code) or "unknown_service" in joined or "service_match" in joined:
        files.extend(["service_prompt_10.md", "caution_prompt_8.md"])
    if "gt_receiver_coverage" in joined or "gt_service_coverage" in joined:
        files.extend(["response_prompt_baseline_cot.md", "caution_prompt_8.md"])
    if "numeric_grounding" in joined:
        files.extend(["tempo_prompt_9.md", "grammar_ver1.5.10.md"])
    if "enum_grounding" in joined:
        files.extend(["service_prompt_10.md", "response_prompt_baseline_cot.md"])
    if "precondition" in joined or "semantic" in joined:
        files.extend(["caution_prompt_8.md", "response_prompt_baseline_cot.md"])
    deduped: list[str] = []
    for item in files:
        if item not in deduped:
            deduped.append(item)
    return deduped or ["response_prompt_baseline_cot.md"]


def _explain_failure(row: dict[str, Any], failure_reasons: list[str], gt_code: str, generated_code: str) -> str:
    notes: list[str] = []
    if VALUE_CHAIN_RE.search(generated_code):
        notes.append("value service access 뒤에 다른 function을 dot-chain으로 붙여 JOILang 구조가 무너졌습니다")
    if "dataflow" in failure_reasons:
        notes.append("읽은 센서값이 독립 변수 흐름으로 downstream call에 전달되지 않았습니다")
    if "gt_service_coverage" in failure_reasons:
        notes.append("GT에 필요한 서비스 호출 일부가 빠졌거나 evaluator가 독립 호출로 인식하지 못했습니다")
    if "gt_receiver_coverage" in failure_reasons:
        notes.append("GT가 요구한 receiver scope를 충분히 덮지 못했습니다")
    if "arg_type" in failure_reasons or PIPE_ARGS_RE.search(generated_code):
        notes.append("현재 서비스 시그니처와 맞지 않는 인자 구분자나 인자 형식을 사용했습니다")
    if "numeric_grounding" in failure_reasons:
        notes.append("명령의 숫자나 단위가 코드에 정확히 grounding되지 않았습니다")
    if "enum_grounding" in failure_reasons:
        notes.append("mode/enum 값이 GT와 다르게 선택됐습니다")
    if not notes:
        notes.append("GT와 generated code의 구조 차이로 strict DET에서 감점되었습니다")
    command = _safe_text(row.get("command_eng"))
    return f"{command}: " + "; ".join(notes)


def _discover_result_dirs(root_dir: Path, condition: str) -> list[Path]:
    dirs: list[Path] = []
    for child in sorted(root_dir.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "suite_manifest.json").exists():
            continue
        if condition and not child.name.startswith(f"{condition}_"):
            continue
        dirs.append(child)
    return dirs


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _build_category_rows(result_dir: Path, model_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    row_path = result_dir / "row_comparison.csv"
    rows = _load_csv(row_path)
    failures: list[dict[str, Any]] = []
    reason_counter: Counter[str] = Counter()
    summary_rows: list[dict[str, Any]] = []
    det_scores: list[float] = []
    pass_count = 0
    exact_count = 0
    prompt_tokens: list[float] = []
    latencies: list[float] = []
    retrieval_used = ""
    prompt_render_mode = ""
    category = ""

    for row in rows:
        category = _safe_text(row.get("category"))
        det_score = _safe_float(row.get(f"{model_key}__det_score"))
        det_scores.append(det_score)
        if _safe_bool(row.get(f"{model_key}__det_pass")):
            pass_count += 1
        if _safe_bool(row.get(f"{model_key}__det_gt_exact")):
            exact_count += 1
        prompt_tokens.append(_safe_float(row.get(f"{model_key}__prompt_tokens")))
        latencies.append(_safe_float(row.get(f"{model_key}__llm_latency_sec")))
        retrieval_used = _safe_text(row.get(f"{model_key}__service_list_retrieval_status"))
        prompt_render_mode = _safe_text(row.get(f"{model_key}__prompt_render_mode"))
        failure_reasons = _parse_failure_reasons(row.get(f"{model_key}__failure_reasons"))
        if not _safe_bool(row.get(f"{model_key}__det_pass")):
            gt_code = _extract_gt_code(row)
            generated_code = _safe_text(row.get(f"{model_key}__output_code"))
            recommended_files = _recommend_files(failure_reasons, generated_code)
            analysis = _explain_failure(row, failure_reasons, gt_code, generated_code)
            failures.append(
                {
                    "result_dir": str(result_dir),
                    "category": category,
                    "row_no": _safe_int(row.get("row_no")),
                    "command_eng": _safe_text(row.get("command_eng")),
                    "command_kor": _safe_text(row.get("command_kor")),
                    "det_score": det_score,
                    "failure_reasons": json.dumps(failure_reasons, ensure_ascii=False),
                    "gt_code": gt_code,
                    "generated_code": generated_code,
                    "recommended_prompt_files": ", ".join(recommended_files),
                    "analysis": analysis,
                    "retrieval_categories": _safe_text(row.get(f"{model_key}__service_list_retrieval_categories")),
                    "prompt_tokens": _safe_float(row.get(f"{model_key}__prompt_tokens")),
                    "llm_latency_sec": _safe_float(row.get(f"{model_key}__llm_latency_sec")),
                }
            )
            for reason in failure_reasons:
                reason_counter[reason] += 1

    row_count = len(rows)
    summary_rows.append(
        {
            "result_dir": str(result_dir),
            "category": category,
            "row_count": row_count,
            "failure_count": len(failures),
            "avg_det_score": round(sum(det_scores) / row_count, 4) if row_count else 0.0,
            "det_pass_rate": round(pass_count / row_count, 4) if row_count else 0.0,
            "gt_exact_rate": round(exact_count / row_count, 4) if row_count else 0.0,
            "avg_prompt_tokens": round(sum(prompt_tokens) / row_count, 2) if row_count else 0.0,
            "avg_llm_latency_sec": round(sum(latencies) / row_count, 4) if row_count else 0.0,
            "retrieval_status": retrieval_used,
            "prompt_render_mode": prompt_render_mode,
        }
    )
    return summary_rows, failures, reason_counter


def _render_markdown(
    condition: str,
    model_key: str,
    summary_rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    reason_counter: Counter[str],
) -> str:
    lines = [
        "# GPT-4.1-mini Category Failure Analysis",
        "",
        f"- Condition: `{condition}`",
        f"- Model: `{model_key}`",
        f"- Category runs: `{len(summary_rows)}`",
        f"- Total failed rows: `{len(failures)}`",
        "",
        "## Category Summary",
        "",
        "| Category | Rows | Failures | Avg DET | Pass Rate | Exact Rate | Avg Prompt Tokens | Avg LLM Latency (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(summary_rows, key=lambda item: _safe_int(item.get("category"))):
        lines.append(
            f"| {row['category']} | {row['row_count']} | {row['failure_count']} | "
            f"{row['avg_det_score']:.4f} | {row['det_pass_rate']:.4f} | {row['gt_exact_rate']:.4f} | "
            f"{row['avg_prompt_tokens']:.2f} | {row['avg_llm_latency_sec']:.4f} |"
        )
    lines.extend(["", "## Failure Reason Distribution", ""])
    if reason_counter:
        for reason, count in reason_counter.most_common():
            lines.append(f"- `{reason}`: {count}")
    else:
        lines.append("- No failures found.")
    lines.extend(["", "## Failure Case Analysis", ""])
    if not failures:
        lines.append("No failed rows were found.")
        return "\n".join(lines)
    for failure in sorted(failures, key=lambda item: (_safe_int(item.get("category")), _safe_int(item.get("row_no")))):
        lines.extend(
            [
                f"### Category {failure['category']} · Row {failure['row_no']}",
                "",
                f"- Command (EN): {failure['command_eng']}",
                f"- Command (KO): {failure['command_kor']}",
                f"- DET: `{failure['det_score']:.4f}`",
                f"- Failure reasons: `{failure['failure_reasons']}`",
                f"- Recommended prompt files: `{failure['recommended_prompt_files']}`",
                f"- Analysis: {failure['analysis']}",
                "",
                "```joi",
                "# GT",
                failure["gt_code"] or "<empty>",
                "",
                "# Generated",
                failure["generated_code"] or "<empty>",
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def _render_html(markdown_text: str) -> str:
    body: list[str] = []
    in_code = False
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            body.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- "):
            body.append(f"<p><strong>•</strong> {html.escape(line[2:])}</p>")
        elif line.startswith("| ") or line.startswith("|---"):
            body.append(f"<pre>{html.escape(line)}</pre>")
        elif line.startswith("```"):
            if in_code:
                body.append("</pre>")
                in_code = False
            else:
                body.append("<pre class='code'>")
                in_code = True
        elif in_code:
            body.append(html.escape(line))
        elif line.strip():
            body.append(f"<p>{html.escape(line)}</p>")
        else:
            body.append("<div class='spacer'></div>")
    if in_code:
        body.append("</pre>")
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>GPT-4.1-mini Category Failure Analysis</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 32px auto; max-width: 1100px; line-height: 1.55; color: #1f2937; }}
    h1, h2, h3 {{ color: #111827; }}
    pre {{ background: #f3f4f6; padding: 12px; overflow-x: auto; border-radius: 8px; }}
    .code {{ white-space: pre-wrap; }}
    .spacer {{ height: 10px; }}
  </style>
</head>
<body>
{''.join(body)}
</body>
</html>"""
    return html_doc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze per-category GPT-4.1-mini benchmark runs and export failure-by-failure summaries.")
    parser.add_argument("--root-dir", required=True)
    parser.add_argument("--condition", default="retrieval")
    parser.add_argument("--model-key", default="gpt41_mini")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root_dir = Path(args.root_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else root_dir / "analysis"
    result_dirs = _discover_result_dirs(root_dir, args.condition)
    if not result_dirs:
        raise SystemExit(f"No result directories found under {root_dir} for condition={args.condition!r}")

    all_summary_rows: list[dict[str, Any]] = []
    all_failures: list[dict[str, Any]] = []
    total_reasons: Counter[str] = Counter()
    manifests: list[dict[str, Any]] = []
    for result_dir in result_dirs:
        manifests.append(_load_manifest(result_dir / "suite_manifest.json"))
        summary_rows, failures, reason_counter = _build_category_rows(result_dir, args.model_key)
        all_summary_rows.extend(summary_rows)
        all_failures.extend(failures)
        total_reasons.update(reason_counter)

    markdown_text = _render_markdown(args.condition, args.model_key, all_summary_rows, all_failures, total_reasons)
    html_text = _render_html(markdown_text)

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_csv = out_dir / "category_run_summary.csv"
    failure_csv = out_dir / "category_failure_rows.csv"
    failure_json = out_dir / "category_failure_rows.json"
    markdown_path = out_dir / "failure_analysis.md"
    html_path = out_dir / "failure_analysis.html"
    summary_json = out_dir / "failure_analysis_summary.json"

    _write_csv(summary_csv, all_summary_rows)
    _write_csv(failure_csv, all_failures)
    _dump_json(failure_json, all_failures)
    markdown_path.write_text(markdown_text, encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")
    _dump_json(
        summary_json,
        {
            "root_dir": str(root_dir),
            "out_dir": str(out_dir),
            "condition": args.condition,
            "model_key": args.model_key,
            "result_dirs": [str(path) for path in result_dirs],
            "category_count": len(all_summary_rows),
            "failure_count": len(all_failures),
            "top_failure_reasons": total_reasons.most_common(),
            "summary_csv": str(summary_csv),
            "failure_csv": str(failure_csv),
            "failure_json": str(failure_json),
            "markdown": str(markdown_path),
            "html": str(html_path),
        },
    )

    if args.print_json:
        print(
            json.dumps(
                {
                    "category_count": len(all_summary_rows),
                    "failure_count": len(all_failures),
                    "summary_csv": str(summary_csv),
                    "failure_csv": str(failure_csv),
                    "failure_analysis_html": str(html_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
