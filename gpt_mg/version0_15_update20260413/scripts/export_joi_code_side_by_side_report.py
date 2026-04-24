#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import shutil
import statistics
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _jsonish_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    text = _safe_text(value)
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return [token.strip() for token in text.split(",") if token.strip()]


def _format_float(value: Any, digits: int = 4) -> str:
    number = _safe_float(value, float("nan"))
    if math.isnan(number):
        return "-"
    return f"{number:.{digits}f}"


def _format_bool(value: Any) -> str:
    text = _safe_text(value).lower()
    return "Yes" if text in {"1", "true", "yes"} else "No"


def _p50(values: list[float]) -> float:
    numeric = [value for value in values if isinstance(value, (int, float))]
    if not numeric:
        return 0.0
    numeric = sorted(numeric)
    middle = len(numeric) // 2
    if len(numeric) % 2:
        return float(numeric[middle])
    return float((numeric[middle - 1] + numeric[middle]) / 2.0)


def _mean(values: list[float]) -> float:
    numeric = [value for value in values if isinstance(value, (int, float))]
    return float(sum(numeric) / len(numeric)) if numeric else 0.0


def _category_sort_key(value: str) -> tuple[int, Any]:
    text = _safe_text(value)
    if text.isdigit():
        return (0, int(text))
    return (1, text.casefold())


def _html_badge(label: str, value: str, *, kind: str = "neutral") -> str:
    return (
        f'<div class="badge badge-{html.escape(kind)}">'
        f'<span class="badge-label">{html.escape(label)}</span>'
        f'<span class="badge-value">{html.escape(value)}</span>'
        f"</div>"
    )


def _diff_html(gt_code: str, pred_code: str) -> str:
    gt_lines = gt_code.splitlines() or [gt_code]
    pred_lines = pred_code.splitlines() or [pred_code]
    rows: list[str] = []
    max_len = max(len(gt_lines), len(pred_lines))
    for index in range(max_len):
        left = gt_lines[index] if index < len(gt_lines) else ""
        right = pred_lines[index] if index < len(pred_lines) else ""
        row_class = "same" if left == right else "diff"
        rows.append(
            "<tr class='diff-row %s'><td><code>%s</code></td><td><code>%s</code></td></tr>"
            % (row_class, html.escape(left), html.escape(right))
        )
    return (
        "<table class='diff-table'>"
        "<thead><tr><th>GT</th><th>Generated</th></tr></thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _default_output_dir(results_dir: Path, model_key: str) -> Path:
    return results_dir / f"side_by_side_report_{model_key}"


def _find_suite_row(suite_rows: list[dict[str, str]], model_key: str) -> dict[str, str]:
    for row in suite_rows:
        if _safe_text(row.get("model_key")) == model_key:
            return row
    return {}


def _build_summary(selected_rows: list[dict[str, str]], model_key: str) -> dict[str, Any]:
    prefix = f"{model_key}__"
    det_scores = [_safe_float(row.get(prefix + "det_score")) for row in selected_rows]
    prompt_tokens = [_safe_float(row.get(prefix + "prompt_tokens")) for row in selected_rows]
    completion_tokens = [_safe_float(row.get(prefix + "completion_tokens")) for row in selected_rows]
    total_tokens = [_safe_float(row.get(prefix + "total_tokens")) for row in selected_rows]
    latency = [_safe_float(row.get(prefix + "llm_latency_sec")) for row in selected_rows]
    pipeline = [_safe_float(row.get(prefix + "total_pipeline_sec")) for row in selected_rows]
    vram = [_safe_float(row.get(prefix + "peak_vram_gb")) for row in selected_rows]
    similarity = [_safe_float(row.get(prefix + "det_gt_similarity")) for row in selected_rows]
    failures = Counter()
    snippet_sources = Counter()
    categories = Counter()
    det_pass = 0
    gt_exact = 0
    oom_count = 0
    gen_errors = Counter()

    for row in selected_rows:
        if _safe_text(row.get(prefix + "det_pass")).lower() in {"1", "true", "yes"}:
            det_pass += 1
        if _safe_text(row.get(prefix + "det_gt_exact")).lower() in {"1", "true", "yes"}:
            gt_exact += 1
        if _safe_text(row.get(prefix + "oom_flag")).lower() in {"1", "true", "yes"}:
            oom_count += 1
        for failure in _jsonish_list(row.get(prefix + "failure_reasons")):
            failures[str(failure)] += 1
        snippet_sources[_safe_text(row.get(prefix + "service_list_snippet_source"), "-")] += 1
        categories[_safe_text(row.get("category"), "-")] += 1
        error_type = _safe_text(row.get(prefix + "generation_error_type"))
        if error_type:
            gen_errors[error_type] += 1

    return {
        "row_count": len(selected_rows),
        "avg_det_score": _mean(det_scores),
        "det_pass_rate": det_pass / len(selected_rows) if selected_rows else 0.0,
        "gt_exact_rate": gt_exact / len(selected_rows) if selected_rows else 0.0,
        "avg_similarity": _mean(similarity),
        "avg_prompt_tokens": _mean(prompt_tokens),
        "avg_completion_tokens": _mean(completion_tokens),
        "avg_total_tokens": _mean(total_tokens),
        "avg_latency_sec": _mean(latency),
        "p50_latency_sec": _p50(latency),
        "avg_pipeline_sec": _mean(pipeline),
        "peak_vram_gb_max": max(vram) if vram else 0.0,
        "oom_count": oom_count,
        "top_failures": failures.most_common(8),
        "snippet_sources": dict(snippet_sources),
        "categories": dict(sorted(categories.items(), key=lambda item: _category_sort_key(item[0]))),
        "generation_errors": dict(gen_errors),
    }


def _render_html(
    *,
    title: str,
    results_dir: Path,
    output_dir: Path,
    model_key: str,
    manifest: dict[str, Any],
    suite_row: dict[str, str],
    selected_rows: list[dict[str, str]],
    summary: dict[str, Any],
) -> str:
    prefix = f"{model_key}__"
    summary_badges = [
        _html_badge("Rows", str(summary["row_count"]), kind="neutral"),
        _html_badge("Avg DET", _format_float(summary["avg_det_score"]), kind="primary"),
        _html_badge("DET Pass", f"{summary['det_pass_rate'] * 100:.1f}%", kind="primary"),
        _html_badge("GT Exact", f"{summary['gt_exact_rate'] * 100:.1f}%", kind="neutral"),
        _html_badge("Avg Prompt Tokens", f"{summary['avg_prompt_tokens']:.1f}", kind="accent"),
        _html_badge("Avg Completion Tokens", f"{summary['avg_completion_tokens']:.1f}", kind="accent"),
        _html_badge("Avg LLM Latency", f"{summary['avg_latency_sec']:.3f}s", kind="accent"),
        _html_badge("p50 LLM Latency", f"{summary['p50_latency_sec']:.3f}s", kind="accent"),
        _html_badge("Peak VRAM", f"{summary['peak_vram_gb_max']:.3f} GB", kind="warn"),
        _html_badge("OOM Count", str(summary["oom_count"]), kind="warn" if summary["oom_count"] else "neutral"),
    ]

    suite_badges: list[str] = []
    if suite_row:
        suite_badges.extend(
            [
                _html_badge("Model", _safe_text(suite_row.get("model_label"), model_key), kind="primary"),
                _html_badge("Resolved Model", _safe_text(suite_row.get("resolved_model_path"), "-"), kind="neutral"),
                _html_badge("Worker Python", _safe_text(suite_row.get("worker_python"), "-"), kind="neutral"),
                _html_badge("Candidate k", _safe_text(suite_row.get("candidate_k"), "-"), kind="neutral"),
                _html_badge("Repair Attempts", _safe_text(suite_row.get("repair_attempts"), "-"), kind="neutral"),
                _html_badge("DET Profile", _safe_text(suite_row.get("mode"), manifest.get("det_profile", "-")), kind="neutral"),
            ]
        )

    run_meta = [
        ("Results Dir", str(results_dir)),
        ("Output Dir", str(output_dir)),
        ("Suite", _safe_text(manifest.get("suite"), "-")),
        ("Genome", _safe_text(manifest.get("genome_json"), "-")),
        ("Created At", _safe_text(manifest.get("created_at"), "-")),
        ("Categories", ", ".join(_safe_text(v) for v in manifest.get("category_filters", []) if _safe_text(v)) or "-"),
        ("Limit/Category", _safe_text(manifest.get("limit_per_category"), "-")),
        ("Rows", ", ".join(str(v) for v in manifest.get("row_nos", [])) or "-"),
    ]

    failure_list = "".join(
        f"<li><span>{html.escape(reason)}</span><strong>{count}</strong></li>"
        for reason, count in summary["top_failures"]
    ) or "<li><span>None</span><strong>0</strong></li>"
    snippet_list = "".join(
        f"<li><span>{html.escape(key)}</span><strong>{value}</strong></li>"
        for key, value in summary["snippet_sources"].items()
    ) or "<li><span>None</span><strong>0</strong></li>"
    category_list = "".join(
        f"<li><span>Category {html.escape(key)}</span><strong>{value}</strong></li>"
        for key, value in summary["categories"].items()
    ) or "<li><span>None</span><strong>0</strong></li>"

    row_sections: list[str] = []
    for row in selected_rows:
        gt_code = _safe_text(row.get("gt_code"), "<empty>")
        generated_code = _safe_text(row.get(prefix + "output_code"), "<empty>")
        failure_reasons = [str(item) for item in _jsonish_list(row.get(prefix + "failure_reasons"))]
        failure_chips = "".join(
            f"<span class='chip chip-failure'>{html.escape(reason)}</span>" for reason in failure_reasons
        ) or "<span class='chip chip-ok'>none</span>"
        retrieval_categories = [str(item) for item in _jsonish_list(row.get(prefix + "service_list_retrieval_categories"))]
        retrieval_chip = ", ".join(retrieval_categories) if retrieval_categories else "-"

        metrics = [
            ("DET", _format_float(row.get(prefix + "det_score")), "primary"),
            ("Pass", _format_bool(row.get(prefix + "det_pass")), "primary"),
            ("GT Exact", _format_bool(row.get(prefix + "det_gt_exact")), "neutral"),
            ("Similarity", _format_float(row.get(prefix + "det_gt_similarity")), "neutral"),
            ("GT Service Cov.", _format_float(row.get(prefix + "det_gt_service_coverage")), "neutral"),
            ("Receiver Cov.", _format_float(row.get(prefix + "det_gt_receiver_coverage")), "neutral"),
            ("Dataflow", _format_float(row.get(prefix + "det_dataflow_score")), "neutral"),
            ("Numeric", _format_float(row.get(prefix + "det_numeric_grounding")), "neutral"),
            ("Enum", _format_float(row.get(prefix + "det_enum_grounding")), "neutral"),
            ("Prompt Tokens", _safe_text(row.get(prefix + "prompt_tokens"), "0"), "accent"),
            ("Completion Tokens", _safe_text(row.get(prefix + "completion_tokens"), "0"), "accent"),
            ("Total Tokens", _safe_text(row.get(prefix + "total_tokens"), "0"), "accent"),
            ("LLM Latency", f"{_safe_float(row.get(prefix + 'llm_latency_sec')):.3f}s", "accent"),
            ("Pipeline", f"{_safe_float(row.get(prefix + 'total_pipeline_sec')):.3f}s", "accent"),
            ("Tok/s", _format_float(row.get(prefix + "tokens_per_sec")), "accent"),
            ("Peak VRAM", f"{_safe_float(row.get(prefix + 'peak_vram_gb')):.3f} GB", "warn"),
            ("OOM", _format_bool(row.get(prefix + "oom_flag")), "warn" if _format_bool(row.get(prefix + "oom_flag")) == "Yes" else "neutral"),
            ("Snippet Source", _safe_text(row.get(prefix + "service_list_snippet_source"), "-"), "neutral"),
            ("Device Count", _safe_text(row.get(prefix + "service_list_device_count"), "-"), "neutral"),
            ("Retrieval", _safe_text(row.get(prefix + "service_list_retrieval_status"), "-"), "neutral"),
            ("Top-k", _safe_text(row.get(prefix + "service_list_retrieval_topk"), "-"), "neutral"),
        ]
        metrics_html = "".join(_html_badge(label, value, kind=kind) for label, value, kind in metrics)

        section = f"""
        <section class="row-card">
          <div class="row-header">
            <div>
              <h2>Row {html.escape(_safe_text(row.get("row_no"), "-"))} · Category {html.escape(_safe_text(row.get("category"), "-"))}</h2>
              <p class="command-eng">{html.escape(_safe_text(row.get("command_eng"), "-"))}</p>
              <p class="command-kor">{html.escape(_safe_text(row.get("command_kor"), "-"))}</p>
            </div>
            <div class="row-meta">
              <span class="chip chip-neutral">GT name: {html.escape(_safe_text(row.get("gt_name"), "-"))}</span>
              <span class="chip chip-neutral">Output name: {html.escape(_safe_text(row.get(prefix + "output_name"), "-"))}</span>
              <span class="chip chip-neutral">Retrieval cats: {html.escape(retrieval_chip)}</span>
            </div>
          </div>
          <div class="badge-grid">{metrics_html}</div>
          <div class="code-grid">
            <div class="code-panel">
              <h3>GT JOICode</h3>
              <div class="code-meta">cron={html.escape(_safe_text(row.get("gt_cron"), '""'))} · period={html.escape(_safe_text(row.get("gt_period"), "0"))}</div>
              <pre><code>{html.escape(gt_code)}</code></pre>
            </div>
            <div class="code-panel">
              <h3>Generated JOICode</h3>
              <div class="code-meta">cron={html.escape(_safe_text(row.get(prefix + "output_cron"), '""'))} · period={html.escape(_safe_text(row.get(prefix + "output_period"), "0"))}</div>
              <pre><code>{html.escape(generated_code)}</code></pre>
            </div>
          </div>
          <div class="subgrid">
            <div class="subpanel">
              <h4>Failure Reasons</h4>
              <div class="chip-wrap">{failure_chips}</div>
            </div>
            <div class="subpanel">
              <h4>Line Diff</h4>
              {_diff_html(gt_code, generated_code)}
            </div>
          </div>
        </section>
        """
        row_sections.append(section)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    @page {{
      size: A4 landscape;
      margin: 10mm;
    }}
    :root {{
      --bg: #f6f4ec;
      --paper: #fffdf8;
      --ink: #1e2329;
      --muted: #69707a;
      --line: #d8d1c0;
      --panel: #f2efe3;
      --accent: #0d5c63;
      --primary: #8f2d56;
      --warn: #b26a00;
      --failure: #8f1d1d;
      --ok: #2f7d32;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Noto Sans KR", system-ui, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.45;
    }}
    main {{
      width: 100%;
      margin: 0 auto;
      padding: 14px 18px 24px;
    }}
    .hero {{
      background: linear-gradient(135deg, #fef9ea 0%, #eef4f7 55%, #f8eee8 100%);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px 22px;
      margin-bottom: 16px;
    }}
    .hero h1 {{
      margin: 0 0 6px;
      font-size: 28px;
      line-height: 1.1;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .meta-grid, .badge-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }}
    .meta-card, .summary-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      break-inside: avoid;
    }}
    .meta-card h3, .summary-card h3 {{
      margin: 0 0 8px;
      font-size: 13px;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .meta-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 6px;
    }}
    .meta-list li {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 13px;
    }}
    .meta-list strong {{
      text-align: right;
      font-weight: 600;
    }}
    .summary-block {{
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .badge-grid {{
      grid-template-columns: repeat(5, minmax(0, 1fr));
    }}
    .badge {{
      display: flex;
      flex-direction: column;
      gap: 3px;
      min-height: 68px;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: var(--paper);
    }}
    .badge-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
    }}
    .badge-value {{
      font-size: 16px;
      font-weight: 700;
      line-height: 1.15;
      word-break: break-word;
    }}
    .badge-primary .badge-value {{ color: var(--primary); }}
    .badge-accent .badge-value {{ color: var(--accent); }}
    .badge-warn .badge-value {{ color: var(--warn); }}
    .section-title {{
      margin: 18px 0 10px;
      font-size: 15px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}
    .row-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      margin-bottom: 14px;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .row-header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 12px;
    }}
    .row-header h2 {{
      margin: 0 0 6px;
      font-size: 20px;
    }}
    .command-eng {{
      margin: 0 0 4px;
      font-size: 15px;
      font-weight: 600;
    }}
    .command-kor {{
      margin: 0;
      font-size: 14px;
      color: var(--muted);
    }}
    .row-meta {{
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 6px;
      max-width: 36%;
    }}
    .chip-wrap {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      background: #f4efe2;
      border: 1px solid var(--line);
    }}
    .chip-failure {{
      color: var(--failure);
      background: #f9eceb;
      border-color: #edc9c5;
    }}
    .chip-ok {{
      color: var(--ok);
      background: #edf7ed;
      border-color: #c6e1c8;
    }}
    .chip-neutral {{
      color: var(--ink);
    }}
    .code-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin: 12px 0;
    }}
    .code-panel, .subpanel {{
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      padding: 12px;
      min-width: 0;
    }}
    .code-panel h3, .subpanel h4 {{
      margin: 0 0 8px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
    }}
    .code-meta {{
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 12px;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      overflow-wrap: anywhere;
      font-family: "IBM Plex Mono", "JetBrains Mono", ui-monospace, monospace;
      font-size: 12px;
      line-height: 1.55;
      background: #fffdfa;
      border: 1px solid rgba(0,0,0,0.06);
      border-radius: 12px;
      padding: 12px;
      min-height: 120px;
    }}
    .subgrid {{
      display: grid;
      grid-template-columns: 0.8fr 1.2fr;
      gap: 12px;
      margin-top: 12px;
    }}
    .diff-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      table-layout: fixed;
    }}
    .diff-table th, .diff-table td {{
      border: 1px solid var(--line);
      padding: 6px 8px;
      vertical-align: top;
      width: 50%;
      background: #fffdfa;
    }}
    .diff-table code {{
      white-space: pre-wrap;
      word-break: break-word;
      font-family: "IBM Plex Mono", "JetBrains Mono", ui-monospace, monospace;
    }}
    .diff-row.diff td {{
      background: #fff0ec;
    }}
    .footer-note {{
      margin-top: 14px;
      color: var(--muted);
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>{html.escape(title)}</h1>
      <p>Side-by-side GT vs Generated JOICode report for <strong>{html.escape(model_key)}</strong>. This report is rendered from row-level benchmark outputs and is print-friendly for PDF export.</p>
      <div class="badge-grid">
        {''.join(summary_badges)}
      </div>
    </section>

    <div class="summary-block">
      <div class="summary-card">
        <h3>Run Metadata</h3>
        <ul class="meta-list">
          {''.join(f'<li><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></li>' for label, value in run_meta)}
        </ul>
      </div>
      <div class="summary-card">
        <h3>Top Failure Reasons</h3>
        <ul class="meta-list">{failure_list}</ul>
      </div>
      <div class="summary-card">
        <h3>Context + Categories</h3>
        <ul class="meta-list">{snippet_list}{category_list}</ul>
      </div>
    </div>

    <div class="summary-card" style="margin-bottom: 16px;">
      <h3>Model Runtime Snapshot</h3>
      <div class="badge-grid">
        {''.join(suite_badges)}
      </div>
    </div>

    <p class="section-title">Row Details</p>
    {''.join(row_sections)}
    <p class="footer-note">Generated from {html.escape(str(results_dir / 'row_comparison.csv'))}. PDF export uses headless Chrome when available.</p>
  </main>
</body>
</html>
"""


def _select_rows(
    rows: list[dict[str, str]],
    *,
    categories: list[str],
    row_nos: list[int],
    start_row: int,
    end_row: int,
    failures_only: bool,
    det_below: float | None,
    limit: int,
    model_key: str,
) -> list[dict[str, str]]:
    prefix = f"{model_key}__"
    selected: list[dict[str, str]] = []
    category_set = {str(value).strip() for value in categories if str(value).strip()}
    row_no_set = {int(value) for value in row_nos}
    for row in rows:
        row_no = _safe_int(row.get("row_no"))
        category = _safe_text(row.get("category"))
        if category_set and category not in category_set:
            continue
        if row_no_set and row_no not in row_no_set:
            continue
        if start_row and row_no < start_row:
            continue
        if end_row and row_no > end_row:
            continue
        if failures_only and _safe_text(row.get(prefix + "det_pass")).lower() in {"1", "true", "yes"}:
            continue
        if det_below is not None and _safe_float(row.get(prefix + "det_score")) >= det_below:
            continue
        selected.append(row)
    selected.sort(key=lambda row: (_category_sort_key(_safe_text(row.get("category"))), _safe_int(row.get("row_no"))))
    if limit > 0:
        selected = selected[:limit]
    return selected


def _write_selected_rows_csv(path: Path, rows: list[dict[str, str]], model_key: str) -> None:
    prefix = f"{model_key}__"
    fieldnames = [
        "row_no",
        "category",
        "command_eng",
        "command_kor",
        "gt_code",
        "generated_code",
        "det_score",
        "det_pass",
        "det_profile",
        "det_gt_exact",
        "det_gt_similarity",
        "det_gt_service_coverage",
        "det_gt_receiver_coverage",
        "det_dataflow_score",
        "det_numeric_grounding",
        "det_enum_grounding",
        "failure_reasons",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "llm_latency_sec",
        "total_pipeline_sec",
        "tokens_per_sec",
        "peak_vram_gb",
        "service_list_snippet_source",
        "service_list_device_count",
        "service_list_retrieval_status",
        "service_list_retrieval_mode",
        "service_list_retrieval_topk",
        "service_list_retrieval_categories",
        "generation_error_type",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "row_no": row.get("row_no", ""),
                    "category": row.get("category", ""),
                    "command_eng": row.get("command_eng", ""),
                    "command_kor": row.get("command_kor", ""),
                    "gt_code": row.get("gt_code", ""),
                    "generated_code": row.get(prefix + "output_code", ""),
                    "det_score": row.get(prefix + "det_score", ""),
                    "det_pass": row.get(prefix + "det_pass", ""),
                    "det_profile": row.get(prefix + "det_profile", ""),
                    "det_gt_exact": row.get(prefix + "det_gt_exact", ""),
                    "det_gt_similarity": row.get(prefix + "det_gt_similarity", ""),
                    "det_gt_service_coverage": row.get(prefix + "det_gt_service_coverage", ""),
                    "det_gt_receiver_coverage": row.get(prefix + "det_gt_receiver_coverage", ""),
                    "det_dataflow_score": row.get(prefix + "det_dataflow_score", ""),
                    "det_numeric_grounding": row.get(prefix + "det_numeric_grounding", ""),
                    "det_enum_grounding": row.get(prefix + "det_enum_grounding", ""),
                    "failure_reasons": row.get(prefix + "failure_reasons", ""),
                    "prompt_tokens": row.get(prefix + "prompt_tokens", ""),
                    "completion_tokens": row.get(prefix + "completion_tokens", ""),
                    "total_tokens": row.get(prefix + "total_tokens", ""),
                    "llm_latency_sec": row.get(prefix + "llm_latency_sec", ""),
                    "total_pipeline_sec": row.get(prefix + "total_pipeline_sec", ""),
                    "tokens_per_sec": row.get(prefix + "tokens_per_sec", ""),
                    "peak_vram_gb": row.get(prefix + "peak_vram_gb", ""),
                    "service_list_snippet_source": row.get(prefix + "service_list_snippet_source", ""),
                    "service_list_device_count": row.get(prefix + "service_list_device_count", ""),
                    "service_list_retrieval_status": row.get(prefix + "service_list_retrieval_status", ""),
                    "service_list_retrieval_mode": row.get(prefix + "service_list_retrieval_mode", ""),
                    "service_list_retrieval_topk": row.get(prefix + "service_list_retrieval_topk", ""),
                    "service_list_retrieval_categories": row.get(prefix + "service_list_retrieval_categories", ""),
                    "generation_error_type": row.get(prefix + "generation_error_type", ""),
                }
            )


def _chrome_path(user_value: str) -> str:
    if user_value:
        return user_value
    for candidate in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return ""


def _render_pdf(html_path: Path, pdf_path: Path, chrome_path: str) -> dict[str, Any]:
    chrome = _chrome_path(chrome_path)
    if not chrome:
        return {"ok": False, "reason": "chrome_not_found", "pdf_path": str(pdf_path)}
    command = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=12000",
        f"--print-to-pdf={pdf_path}",
        f"file://{html_path}",
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except Exception as exc:
        return {"ok": False, "reason": f"chrome_exec_failed:{exc}", "pdf_path": str(pdf_path)}
    if completed.returncode != 0:
        return {
            "ok": False,
            "reason": "chrome_returncode_nonzero",
            "stderr": completed.stderr[-4000:],
            "stdout": completed.stdout[-2000:],
            "pdf_path": str(pdf_path),
        }
    if not pdf_path.exists():
        return {
            "ok": False,
            "reason": "pdf_not_created",
            "stderr": completed.stderr[-4000:],
            "stdout": completed.stdout[-2000:],
            "pdf_path": str(pdf_path),
        }
    return {"ok": True, "pdf_path": str(pdf_path), "chrome_path": chrome}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a side-by-side GT vs Generated JOICode HTML/PDF report from row_comparison.csv.")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--row-no", type=int, action="append", default=[])
    parser.add_argument("--start-row", type=int, default=0)
    parser.add_argument("--end-row", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--failures-only", action="store_true")
    parser.add_argument("--det-below", type=float, default=None)
    parser.add_argument("--skip-pdf", action="store_true")
    parser.add_argument("--chrome-path", default="")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results_dir = Path(args.results_dir).resolve()
    row_csv = results_dir / "row_comparison.csv"
    suite_csv = results_dir / "suite_summary.csv"
    manifest_path = results_dir / "suite_manifest.json"
    if not row_csv.exists():
        raise SystemExit(f"row_comparison.csv not found: {row_csv}")

    rows = _read_csv(row_csv)
    suite_rows = _read_csv(suite_csv)
    manifest = _read_json(manifest_path)

    model_key = _safe_text(args.model_key)
    prefix = f"{model_key}__"
    if rows and prefix + "det_score" not in rows[0]:
        available = sorted({key[:-11] for key in rows[0].keys() if key.endswith("__det_score")})
        raise SystemExit(f"Model key '{model_key}' not found in row_comparison.csv. Available: {available}")

    selected_rows = _select_rows(
        rows,
        categories=list(args.category),
        row_nos=list(args.row_no),
        start_row=args.start_row,
        end_row=args.end_row,
        failures_only=bool(args.failures_only),
        det_below=args.det_below,
        limit=args.limit,
        model_key=model_key,
    )
    if not selected_rows:
        raise SystemExit("No rows matched the requested filters.")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_output_dir(results_dir, model_key)
    output_dir.mkdir(parents=True, exist_ok=True)

    suite_row = _find_suite_row(suite_rows, model_key)
    summary = _build_summary(selected_rows, model_key)
    title = args.title or f"JOICode Side-by-Side Report · {model_key}"

    html_text = _render_html(
        title=title,
        results_dir=results_dir,
        output_dir=output_dir,
        model_key=model_key,
        manifest=manifest,
        suite_row=suite_row,
        selected_rows=selected_rows,
        summary=summary,
    )

    html_path = output_dir / "report.html"
    html_path.write_text(html_text, encoding="utf-8")

    selected_rows_csv = output_dir / "selected_rows.csv"
    _write_selected_rows_csv(selected_rows_csv, selected_rows, model_key)

    report_summary = {
        "results_dir": str(results_dir),
        "output_dir": str(output_dir),
        "model_key": model_key,
        "title": title,
        "row_count": len(selected_rows),
        "html_path": str(html_path),
        "selected_rows_csv": str(selected_rows_csv),
        "filters": {
            "category": list(args.category),
            "row_no": list(args.row_no),
            "start_row": args.start_row,
            "end_row": args.end_row,
            "limit": args.limit,
            "failures_only": bool(args.failures_only),
            "det_below": args.det_below,
        },
        "summary": summary,
    }

    if args.skip_pdf:
        report_summary["pdf"] = {"ok": False, "reason": "skip_pdf"}
    else:
        report_summary["pdf"] = _render_pdf(html_path, output_dir / "report.pdf", args.chrome_path)

    with (output_dir / "report_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(report_summary, handle, ensure_ascii=False, indent=2)

    if args.print_json:
        print(json.dumps(report_summary, ensure_ascii=False, indent=2))
    else:
        print(f"HTML report: {html_path}")
        if report_summary["pdf"].get("ok"):
            print(f"PDF report: {report_summary['pdf']['pdf_path']}")
        else:
            print(f"PDF report unavailable: {report_summary['pdf'].get('reason', 'unknown')}")
        print(f"Report summary JSON: {output_dir / 'report_summary.json'}")
        print(f"Selected rows CSV: {selected_rows_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
