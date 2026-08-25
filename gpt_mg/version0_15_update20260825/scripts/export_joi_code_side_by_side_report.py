#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import shutil
import statistics
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = VERSION_ROOT.parents[1]
DEFAULT_SERVICE_SCHEMA = REPO_ROOT / "datasets" / "service_list_ver2.0.1.json"
DEFAULT_DATASET = REPO_ROOT / "datasets" / "JOICommands-280.csv"
SERVICE_TAG_RE = re.compile(r"#([A-Za-z_][A-Za-z0-9_]*)")
GT_NAME_RE = re.compile(r'"name"\s*:\s*"(.*?)"', re.S)
GT_CRON_RE = re.compile(r'"cron"\s*:\s*"(.*?)"', re.S)
GT_PERIOD_RE = re.compile(r'"period"\s*:\s*([0-9]+)', re.S)
GT_SCRIPT_RE = re.compile(r'"script"\s*:\s*"(.*)"\s*}\s*$', re.S)


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


def _jsonish_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    text = _safe_text(value)
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


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


def _available_model_keys(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    return sorted({key[:-11] for key in rows[0].keys() if key.endswith("__det_score")})


def _derive_name_from_command(command: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", command)
    if not tokens:
        return "-"
    filtered: list[str] = []
    for token in tokens[:10]:
        lower = token.lower()
        if lower in {"the", "a", "an", "and"}:
            continue
        filtered.append(token[:1].upper() + token[1:])
    name = "".join(filtered) or "".join(token[:1].upper() + token[1:] for token in tokens[:6])
    name = re.sub(r"[^A-Za-z0-9]", "", name)
    if not name:
        return "-"
    if name[0].isdigit():
        name = f"Task{name}"
    return name[:50]


def _display_gt_name(row: dict[str, str]) -> str:
    direct = _safe_text(row.get("gt_name"))
    if direct:
        return direct
    gt_payload = _jsonish_object(row.get("gt"))
    payload_name = _safe_text(gt_payload.get("name"))
    if payload_name:
        return payload_name
    derived = _derive_name_from_command(_safe_text(row.get("command_eng")))
    if derived != "-":
        return derived
    return _derive_name_from_command(_safe_text(row.get("command_kor")))


def _gt_payload(row: dict[str, str]) -> dict[str, Any]:
    text = _safe_text(row.get("gt"))
    payload = _jsonish_object(text)
    if payload:
        return payload
    if not text:
        return {}
    fallback: dict[str, Any] = {}
    name_match = GT_NAME_RE.search(text)
    cron_match = GT_CRON_RE.search(text)
    period_match = GT_PERIOD_RE.search(text)
    script_match = GT_SCRIPT_RE.search(text)
    if name_match:
        fallback["name"] = name_match.group(1)
    if cron_match:
        fallback["cron"] = cron_match.group(1)
    if period_match:
        fallback["period"] = period_match.group(1)
    if script_match:
        fallback["script"] = script_match.group(1)
    return fallback


def _extract_gt_code(row: dict[str, str]) -> str:
    direct = _safe_text(row.get("gt_code"))
    if direct:
        return direct
    payload = _gt_payload(row)
    fallback = _safe_text(payload.get("script")) or _safe_text(payload.get("code"))
    return fallback.lstrip()


def _extract_gt_cron(row: dict[str, str]) -> str:
    direct = _safe_text(row.get("gt_cron"))
    if direct:
        return direct
    payload = _gt_payload(row)
    return _safe_text(payload.get("cron"), '""')


def _extract_gt_period(row: dict[str, str]) -> str:
    direct = _safe_text(row.get("gt_period"))
    if direct:
        return direct
    payload = _gt_payload(row)
    period = payload.get("period")
    if period is None or str(period).strip() == "":
        return "0"
    return str(period)


def _service_list_label(manifest: dict[str, Any], suite_row: dict[str, str]) -> str:
    candidate = _safe_text(manifest.get("service_schema")) or _safe_text(suite_row.get("service_schema"))
    if candidate:
        return Path(candidate).name
    return DEFAULT_SERVICE_SCHEMA.name


def _service_schema_path(manifest: dict[str, Any], suite_row: dict[str, str]) -> Path:
    candidate = _safe_text(manifest.get("service_schema")) or _safe_text(suite_row.get("service_schema"))
    if candidate:
        return Path(candidate).resolve()
    return DEFAULT_SERVICE_SCHEMA.resolve()


def _dataset_path(manifest: dict[str, Any]) -> Path:
    candidate = _safe_text(manifest.get("dataset"))
    if candidate:
        return Path(candidate).resolve()
    return DEFAULT_DATASET.resolve()


def _load_dataset_rows_by_no(manifest: dict[str, Any]) -> dict[str, dict[str, str]]:
    dataset_path = _dataset_path(manifest)
    rows = _read_csv(dataset_path)
    return {_safe_text(str(idx)): row for idx, row in enumerate(rows, start=1)}


def _parse_connected_devices(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    text = _safe_text(value)
    if not text:
        return {}
    for parser in (json.loads,):
        try:
            parsed = parser(text)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    try:
        import ast

        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def _resolve_schema_category(raw_category: Any, service_schema: dict[str, Any]) -> str:
    token = _safe_text(raw_category)
    if not token:
        return ""
    if token in service_schema:
        return token
    lowered = token.casefold()
    for candidate in service_schema.keys():
        if candidate.casefold() == lowered:
            return candidate
    return ""


def _connected_device_categories(dataset_row: dict[str, str], service_schema: dict[str, Any]) -> list[str]:
    connected_devices = _parse_connected_devices(dataset_row.get("connected_devices"))
    categories: list[str] = []
    seen: set[str] = set()
    for meta in connected_devices.values():
        raw = meta.get("category") if isinstance(meta, dict) else None
        raw_items = raw if isinstance(raw, list) else [raw]
        for item in raw_items:
            resolved = _resolve_schema_category(item, service_schema)
            if resolved and resolved.casefold() not in seen:
                seen.add(resolved.casefold())
                categories.append(resolved)
    return categories


def _extract_schema_tags_from_texts(texts: list[str], service_schema: dict[str, Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for raw_tag in SERVICE_TAG_RE.findall(text or ""):
            resolved = _resolve_schema_category(raw_tag, service_schema)
            if resolved and resolved.casefold() not in seen:
                seen.add(resolved.casefold())
                ordered.append(resolved)
    return ordered


def _service_item(category: str, service_name: str, meta: dict[str, Any]) -> dict[str, Any]:
    service_type = _safe_text(meta.get("type")).lower() or "unknown"
    argument_type = _safe_text(meta.get("argument_type"), "-")
    return_type = _safe_text(meta.get("return_type"), "-")
    descriptor = _safe_text(meta.get("descriptor"))
    canonical_name = f"{category}_{service_name}"
    return {
        "service": canonical_name,
        "raw_service": service_name,
        "canonical_name": canonical_name,
        "type": service_type,
        "argument_type": argument_type,
        "return_type": return_type,
        "descriptor": descriptor,
    }


def _build_category_card(category: str, service_schema: dict[str, Any], *, role: str, rank: int | None = None) -> dict[str, Any]:
    raw_services = service_schema.get(category, {})
    values: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    for service_name in sorted(raw_services.keys()):
        item = _service_item(category, service_name, raw_services.get(service_name) or {})
        if item["type"] == "value":
            values.append(item)
        else:
            functions.append(item)
    return {
        "category": category,
        "role": role,
        "rank": rank,
        "service_count": len(values) + len(functions),
        "value_count": len(values),
        "function_count": len(functions),
        "values": values,
        "functions": functions,
    }


def _build_context_snapshot(
    row: dict[str, str],
    *,
    model_key: str,
    manifest: dict[str, Any],
    suite_row: dict[str, str],
    service_schema: dict[str, Any],
    dataset_rows_by_no: dict[str, dict[str, str]],
) -> dict[str, Any]:
    prefix = f"{model_key}__"
    row_no = _safe_text(row.get("row_no"))
    dataset_row = dataset_rows_by_no.get(row_no, {})
    snippet_source = _safe_text(row.get(prefix + "service_list_snippet_source"))
    retrieval_status = _safe_text(row.get(prefix + "service_list_retrieval_status"))
    retrieval_mode = _safe_text(row.get(prefix + "service_list_retrieval_mode"))
    requested_topk = _safe_int(row.get(prefix + "service_list_retrieval_topk"), 0)
    retrieval_categories = [
        _resolve_schema_category(item, service_schema)
        for item in _jsonish_list(row.get(prefix + "service_list_retrieval_categories"))
    ]
    retrieval_categories = [item for item in retrieval_categories if item]
    connected_categories = _connected_device_categories(dataset_row, service_schema)
    relevant_categories = _extract_schema_tags_from_texts(
        [
            _extract_gt_code(row),
            _safe_text(row.get(prefix + "output_code")),
            _safe_text(row.get("gt")),
            _safe_text(row.get(prefix + "output")),
        ],
        service_schema,
    )

    all_injected_categories: list[str]
    displayed_categories: list[str]
    note: str
    mode_label: str

    if "service_retrieval_fallback" in snippet_source:
        all_injected_categories = retrieval_categories
        displayed_categories = retrieval_categories
        mode_label = "retrieval premapping"
        effective = len(all_injected_categories)
        note = (
            f"Retrieval premapping was used for this row. Requested top-{requested_topk or '-'} "
            f"and injected {effective} category group(s) into the prompt."
        )
    elif "connected_devices" in snippet_source:
        all_injected_categories = connected_categories
        displayed_categories = connected_categories or relevant_categories
        mode_label = "connected_devices scope"
        note = (
            f"Prompt context came from connected_devices, so retrieval was skipped. "
            f"{len(all_injected_categories)} connected-device category group(s) were injected."
        )
    else:
        all_injected_categories = sorted(service_schema.keys())
        displayed_categories = relevant_categories or connected_categories
        mode_label = "full schema fallback"
        note = (
            f"Premapping was not used for this row. The prompt received the full schema fallback "
            f"({len(all_injected_categories)} categories) from {_service_list_label(manifest, suite_row)}. "
            f"For readability, the report shows only the schema categories directly relevant to the GT/generated code."
        )

    seen_displayed: set[str] = set()
    cards: list[dict[str, Any]] = []
    for index, category in enumerate(displayed_categories, start=1):
        key = category.casefold()
        if key in seen_displayed or category not in service_schema:
            continue
        seen_displayed.add(key)
        role = "retrieved" if category in retrieval_categories else ("connected" if category in connected_categories else "relevant")
        rank = retrieval_categories.index(category) + 1 if category in retrieval_categories else None
        cards.append(_build_category_card(category, service_schema, role=role, rank=rank))

    return {
        "row_no": row_no,
        "service_schema_path": str(_service_schema_path(manifest, suite_row)),
        "service_schema_label": _service_list_label(manifest, suite_row),
        "snippet_source": snippet_source,
        "mode_label": mode_label,
        "retrieval_status": retrieval_status,
        "retrieval_mode": retrieval_mode,
        "requested_topk": requested_topk,
        "effective_topk": len(retrieval_categories),
        "device_count": _safe_int(row.get(prefix + "service_list_device_count"), 0),
        "all_injected_category_count": len(all_injected_categories),
        "all_injected_categories": all_injected_categories,
        "displayed_categories": displayed_categories,
        "retrieval_categories": retrieval_categories,
        "connected_categories": connected_categories,
        "relevant_categories": relevant_categories,
        "note": note,
        "category_cards": cards,
    }


def _context_badges(snapshot: dict[str, Any]) -> list[tuple[str, str, str]]:
    requested_topk = snapshot.get("requested_topk", 0)
    effective_topk = snapshot.get("effective_topk", 0)
    return [
        ("Context Mode", _safe_text(snapshot.get("mode_label"), "-"), "neutral"),
        ("Snippet Source", _safe_text(snapshot.get("snippet_source"), "-"), "neutral"),
        ("Retrieval", _safe_text(snapshot.get("retrieval_status"), "-"), "neutral"),
        ("Configured Top-k", str(requested_topk or "-"), "neutral"),
        ("Effective Top-k", str(effective_topk or "-"), "neutral"),
        ("Injected Categories", str(snapshot.get("all_injected_category_count", 0)), "accent"),
    ]


def _render_service_items(items: list[dict[str, Any]], empty_label: str) -> str:
    if not items:
        return f"<li class='service-empty'>{html.escape(empty_label)}</li>"
    rows: list[str] = []
    for item in items:
        subtitle = f"raw {item['raw_service']} · arg {item['argument_type']} · ret {item['return_type']}"
        if item.get("descriptor"):
            subtitle += f" · {item['descriptor']}"
        rows.append(
            "<li class='service-item'>"
            f"<span class='service-item-name'>{html.escape(item['service'])}</span>"
            f"<span class='service-item-meta'>{html.escape(subtitle)}</span>"
            "</li>"
        )
    return "".join(rows)


def _render_context_snapshot(snapshot: dict[str, Any]) -> str:
    badges_html = "".join(_html_badge(label, value, kind=kind) for label, value, kind in _context_badges(snapshot))
    cards_html: list[str] = []
    for card in snapshot.get("category_cards", []):
        rank_text = f" · rank {card['rank']}" if card.get("rank") else ""
        role_text = _safe_text(card.get("role")).replace("_", " ")
        cards_html.append(
            f"""
            <article class="context-card">
              <div class="context-card-head">
                <h5>{html.escape(card['category'])}</h5>
                <span class="context-card-role">{html.escape(role_text)}{html.escape(rank_text)}</span>
              </div>
              <p class="context-card-meta">{card['service_count']} services · {card['value_count']} values · {card['function_count']} functions</p>
              <div class="service-columns">
                <div>
                  <h6>Values</h6>
                  <ul class="service-list">{_render_service_items(card['values'], 'None')}</ul>
                </div>
                <div>
                  <h6>Functions</h6>
                  <ul class="service-list">{_render_service_items(card['functions'], 'None')}</ul>
                </div>
              </div>
            </article>
            """
        )
    if not cards_html:
        cards_html.append(
            "<article class='context-card'><div class='context-card-head'><h5>No display categories</h5></div>"
            "<p class='context-card-meta'>The report could not infer a smaller category subset for display. "
            "Use prompt_context_rows.json to inspect the full injected category list.</p></article>"
        )

    return f"""
      <div class="subpanel context-panel">
        <h4>Prompt Context Snapshot</h4>
        <p class="context-note">{html.escape(_safe_text(snapshot.get("note"), "-"))}</p>
        <div class="badge-grid context-badges">{badges_html}</div>
        <div class="context-grid">{''.join(cards_html)}</div>
      </div>
    """


def _load_prior_selected_rows(
    output_dir: Path,
    *,
    results_dir: Path,
    model_key: str,
) -> dict[str, dict[str, str]]:
    prior_csv = output_dir / "selected_rows.csv"
    prior_summary = output_dir / "report_summary.json"
    if not prior_csv.exists():
        return {}
    if prior_summary.exists():
        summary = _read_json(prior_summary)
        if _safe_text(summary.get("results_dir")) != str(results_dir):
            return {}
        if _safe_text(summary.get("model_key")) != model_key:
            return {}
    rows = _read_csv(prior_csv)
    return {_safe_text(row.get("row_no")): row for row in rows if _safe_text(row.get("row_no"))}


def _display_retrieval_categories(
    row: dict[str, str],
    *,
    model_key: str,
    prior_row: dict[str, str] | None = None,
) -> str:
    prefix = f"{model_key}__"
    current = [str(item) for item in _jsonish_list(row.get(prefix + "service_list_retrieval_categories"))]
    if current:
        return ", ".join(current)
    snippet_source = _safe_text(row.get(prefix + "service_list_snippet_source")).lower()
    retrieval_status = _safe_text(row.get(prefix + "service_list_retrieval_status")).lower()
    should_recover = ("retrieval" in snippet_source) or retrieval_status not in {"", "-", "disabled", "not_requested", "n/a"}
    if should_recover and prior_row:
        previous = _safe_text(prior_row.get("service_list_retrieval_categories_display"))
        if previous:
            return previous
        previous = _safe_text(prior_row.get("service_list_retrieval_categories"))
        if previous:
            return previous
    if "schema_fallback" in snippet_source:
        return "not used (schema fallback)"
    if "connected_devices" in snippet_source:
        return "not used (connected_devices scope)"
    return "-"


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
    service_schema: dict[str, Any],
    dataset_rows_by_no: dict[str, dict[str, str]],
    prior_rows_by_no: dict[str, dict[str, str]] | None = None,
) -> str:
    prefix = f"{model_key}__"
    service_list_label = _service_list_label(manifest, suite_row)
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
                _html_badge("Service List", service_list_label, kind="neutral"),
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
        gt_code = _safe_text(_extract_gt_code(row), "<empty>")
        generated_code = _safe_text(row.get(prefix + "output_code"), "<empty>")
        failure_reasons = [str(item) for item in _jsonish_list(row.get(prefix + "failure_reasons"))]
        failure_chips = "".join(
            f"<span class='chip chip-failure'>{html.escape(reason)}</span>" for reason in failure_reasons
        ) or "<span class='chip chip-ok'>none</span>"
        prior_row = (prior_rows_by_no or {}).get(_safe_text(row.get("row_no")))
        retrieval_chip = _display_retrieval_categories(row, model_key=model_key, prior_row=prior_row)
        gt_display_name = _display_gt_name(row)
        context_snapshot = _build_context_snapshot(
            row,
            model_key=model_key,
            manifest=manifest,
            suite_row=suite_row,
            service_schema=service_schema,
            dataset_rows_by_no=dataset_rows_by_no,
        )

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
            ("Configured Top-k", _safe_text(row.get(prefix + "service_list_retrieval_topk"), "-"), "neutral"),
            ("Effective Top-k", str(context_snapshot.get("effective_topk") or "-"), "neutral"),
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
              <span class="chip chip-neutral">GT name: {html.escape(gt_display_name)}</span>
              <span class="chip chip-neutral">Service list: {html.escape(service_list_label)}</span>
              <span class="chip chip-neutral">Output name: {html.escape(_safe_text(row.get(prefix + "output_name"), "-"))}</span>
              <span class="chip chip-neutral chip-wide chip-multiline">Retrieval cats: {html.escape(retrieval_chip)}</span>
            </div>
          </div>
          <div class="badge-grid">{metrics_html}</div>
          {_render_context_snapshot(context_snapshot)}
          <div class="code-grid">
            <div class="code-panel">
              <h3>GT JOICode</h3>
              <div class="code-meta">cron={html.escape(_extract_gt_cron(row))} · period={html.escape(_extract_gt_period(row))}</div>
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
    .context-badges {{
      grid-template-columns: repeat(6, minmax(0, 1fr));
      margin-top: 10px;
      margin-bottom: 10px;
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
      display: grid;
      grid-template-columns: minmax(0, 1.18fr) minmax(420px, 1fr);
      gap: 16px;
      align-items: start;
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
      display: grid;
      grid-template-columns: repeat(2, minmax(220px, 1fr));
      gap: 6px;
      width: 100%;
      min-width: 0;
      align-content: start;
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
      justify-content: flex-start;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      background: #f4efe2;
      border: 1px solid var(--line);
      min-width: 0;
    }}
    .chip-wide {{
      grid-column: 1 / -1;
      width: 100%;
      border-radius: 16px;
    }}
    .chip-multiline {{
      white-space: normal;
      align-items: flex-start;
      line-height: 1.4;
      overflow-wrap: anywhere;
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
    .context-panel {{
      margin-top: 12px;
      background: #f7f4ea;
    }}
    .context-note {{
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 12px;
    }}
    .context-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    .context-card {{
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fffdfa;
      padding: 10px 12px;
      min-width: 0;
    }}
    .context-card-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 4px;
    }}
    .context-card-head h5 {{
      margin: 0;
      font-size: 16px;
    }}
    .context-card-role {{
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .context-card-meta {{
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 12px;
    }}
    .service-columns {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    .service-columns h6 {{
      margin: 0 0 6px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
    }}
    .service-list {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 6px;
    }}
    .service-item {{
      display: grid;
      gap: 2px;
      padding: 6px 8px;
      border-radius: 10px;
      background: #f6f2e8;
      border: 1px solid rgba(0,0,0,0.04);
    }}
    .service-item-name {{
      font-size: 12px;
      font-weight: 700;
      color: var(--ink);
    }}
    .service-item-meta, .service-empty {{
      font-size: 11px;
      color: var(--muted);
      line-height: 1.4;
      overflow-wrap: anywhere;
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
    @media (max-width: 1100px) {{
      .row-header {{
        grid-template-columns: 1fr;
      }}
      .row-meta {{
        width: 100%;
        min-width: 0;
        grid-template-columns: 1fr;
      }}
      .chip-wide {{
        grid-column: auto;
      }}
      .context-grid,
      .service-columns {{
        grid-template-columns: 1fr;
      }}
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


def _write_selected_rows_csv(
    path: Path,
    rows: list[dict[str, str]],
    model_key: str,
    *,
    service_list_schema: str,
    service_schema: dict[str, Any],
    manifest: dict[str, Any],
    suite_row: dict[str, str],
    dataset_rows_by_no: dict[str, dict[str, str]],
    prior_rows_by_no: dict[str, dict[str, str]] | None = None,
) -> None:
    prefix = f"{model_key}__"
    fieldnames = [
        "row_no",
        "category",
        "command_eng",
        "command_kor",
        "gt_name_display",
        "service_list_schema",
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
        "service_list_retrieval_categories_display",
        "prompt_context_mode",
        "prompt_context_note",
        "prompt_context_effective_topk",
        "prompt_context_injected_categories",
        "prompt_context_displayed_categories",
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
            prior_row = (prior_rows_by_no or {}).get(_safe_text(row.get("row_no")))
            context_snapshot = _build_context_snapshot(
                row,
                model_key=model_key,
                manifest=manifest,
                suite_row=suite_row,
                service_schema=service_schema,
                dataset_rows_by_no=dataset_rows_by_no,
            )
            writer.writerow(
                {
                    "row_no": row.get("row_no", ""),
                    "category": row.get("category", ""),
                    "command_eng": row.get("command_eng", ""),
                    "command_kor": row.get("command_kor", ""),
                    "gt_name_display": _display_gt_name(row),
                    "service_list_schema": service_list_schema,
                    "gt_code": _extract_gt_code(row),
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
                    "service_list_retrieval_categories_display": _display_retrieval_categories(row, model_key=model_key, prior_row=prior_row),
                    "prompt_context_mode": context_snapshot.get("mode_label", ""),
                    "prompt_context_note": context_snapshot.get("note", ""),
                    "prompt_context_effective_topk": context_snapshot.get("effective_topk", 0),
                    "prompt_context_injected_categories": json.dumps(context_snapshot.get("all_injected_categories", []), ensure_ascii=False),
                    "prompt_context_displayed_categories": json.dumps(context_snapshot.get("displayed_categories", []), ensure_ascii=False),
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
    parser.add_argument("--model-key", default="", help="Optional for single-model results dirs. Required when multiple model keys exist.")
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
    parser.add_argument("--list-model-keys", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def export_row_report(
    *,
    results_dir: str | Path,
    model_key: str = "",
    output_dir: str | Path | None = None,
    title: str = "",
    categories: list[str] | None = None,
    row_nos: list[int] | None = None,
    start_row: int = 0,
    end_row: int = 0,
    limit: int = 0,
    failures_only: bool = False,
    det_below: float | None = None,
    skip_pdf: bool = False,
    chrome_path: str = "",
) -> dict[str, Any]:
    results_dir = Path(results_dir).resolve()
    row_csv = results_dir / "row_comparison.csv"
    suite_csv = results_dir / "suite_summary.csv"
    manifest_path = results_dir / "suite_manifest.json"
    if not row_csv.exists():
        raise SystemExit(f"row_comparison.csv not found: {row_csv}")

    rows = _read_csv(row_csv)
    suite_rows = _read_csv(suite_csv)
    manifest = _read_json(manifest_path)

    available = _available_model_keys(rows)
    model_key = _safe_text(model_key)
    if not available:
        raise SystemExit(f"No model keys found in row_comparison.csv: {row_csv}")
    if not model_key:
        if len(available) == 1:
            model_key = available[0]
        else:
            raise SystemExit(
                f"Multiple model keys found in row_comparison.csv. "
                f"Please set --model-key explicitly. Available: {available}"
            )
    elif model_key not in available:
        raise SystemExit(f"Model key '{model_key}' not found in row_comparison.csv. Available: {available}")

    prefix = f"{model_key}__"

    selected_rows = _select_rows(
        rows,
        categories=list(categories or []),
        row_nos=list(row_nos or []),
        start_row=start_row,
        end_row=end_row,
        failures_only=bool(failures_only),
        det_below=det_below,
        limit=limit,
        model_key=model_key,
    )
    if not selected_rows:
        raise SystemExit("No rows matched the requested filters.")

    output_dir = Path(output_dir).resolve() if output_dir else _default_output_dir(results_dir, model_key)
    output_dir.mkdir(parents=True, exist_ok=True)
    prior_rows_by_no = _load_prior_selected_rows(output_dir, results_dir=results_dir, model_key=model_key)

    suite_row = _find_suite_row(suite_rows, model_key)
    summary = _build_summary(selected_rows, model_key)
    title = title or f"JOICode Side-by-Side Report · {model_key}"
    service_list_schema = _service_list_label(manifest, suite_row)
    service_schema = _read_json(_service_schema_path(manifest, suite_row))
    dataset_rows_by_no = _load_dataset_rows_by_no(manifest)

    prompt_context_rows = [
        _build_context_snapshot(
            row,
            model_key=model_key,
            manifest=manifest,
            suite_row=suite_row,
            service_schema=service_schema,
            dataset_rows_by_no=dataset_rows_by_no,
        )
        for row in selected_rows
    ]

    html_text = _render_html(
        title=title,
        results_dir=results_dir,
        output_dir=output_dir,
        model_key=model_key,
        manifest=manifest,
        suite_row=suite_row,
        selected_rows=selected_rows,
        summary=summary,
        service_schema=service_schema,
        dataset_rows_by_no=dataset_rows_by_no,
        prior_rows_by_no=prior_rows_by_no,
    )

    html_path = output_dir / "report.html"
    html_path.write_text(html_text, encoding="utf-8")

    selected_rows_csv = output_dir / "selected_rows.csv"
    _write_selected_rows_csv(
        selected_rows_csv,
        selected_rows,
        model_key,
        service_list_schema=service_list_schema,
        service_schema=service_schema,
        manifest=manifest,
        suite_row=suite_row,
        dataset_rows_by_no=dataset_rows_by_no,
        prior_rows_by_no=prior_rows_by_no,
    )

    prompt_context_json = output_dir / "prompt_context_rows.json"
    with prompt_context_json.open("w", encoding="utf-8") as handle:
        json.dump(prompt_context_rows, handle, ensure_ascii=False, indent=2)

    report_summary = {
        "results_dir": str(results_dir),
        "output_dir": str(output_dir),
        "model_key": model_key,
        "title": title,
        "row_count": len(selected_rows),
        "service_list_schema": service_list_schema,
        "service_list_schema_path": str(_service_schema_path(manifest, suite_row)),
        "html_path": str(html_path),
        "selected_rows_csv": str(selected_rows_csv),
        "prompt_context_rows_json": str(prompt_context_json),
        "filters": {
            "category": list(categories or []),
            "row_no": list(row_nos or []),
            "start_row": start_row,
            "end_row": end_row,
            "limit": limit,
            "failures_only": bool(failures_only),
            "det_below": det_below,
        },
        "summary": summary,
    }

    if skip_pdf:
        report_summary["pdf"] = {"ok": False, "reason": "skip_pdf"}
    else:
        report_summary["pdf"] = _render_pdf(html_path, output_dir / "report.pdf", chrome_path)

    with (output_dir / "report_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(report_summary, handle, ensure_ascii=False, indent=2)
    return report_summary


def main() -> int:
    args = build_parser().parse_args()
    results_dir = Path(args.results_dir).resolve()
    if args.list_model_keys:
        row_csv = results_dir / "row_comparison.csv"
        if not row_csv.exists():
            raise SystemExit(f"row_comparison.csv not found: {row_csv}")
        rows = _read_csv(row_csv)
        available = _available_model_keys(rows)
        payload = {
            "results_dir": str(results_dir),
            "available_model_keys": available,
            "count": len(available),
        }
        if args.print_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Results dir: {results_dir}")
            print(f"Available model keys ({len(available)}): {available}")
        return 0

    report_summary = export_row_report(
        results_dir=results_dir,
        model_key=args.model_key,
        output_dir=args.output_dir or None,
        title=args.title,
        categories=list(args.category),
        row_nos=list(args.row_no),
        start_row=args.start_row,
        end_row=args.end_row,
        limit=args.limit,
        failures_only=bool(args.failures_only),
        det_below=args.det_below,
        skip_pdf=bool(args.skip_pdf),
        chrome_path=args.chrome_path,
    )

    if args.print_json:
        print(json.dumps(report_summary, ensure_ascii=False, indent=2))
    else:
        print(f"HTML report: {report_summary['html_path']}")
        if report_summary["pdf"].get("ok"):
            print(f"PDF report: {report_summary['pdf']['pdf_path']}")
        else:
            print(f"PDF report unavailable: {report_summary['pdf'].get('reason', 'unknown')}")
        print(f"Report summary JSON: {Path(report_summary['output_dir']) / 'report_summary.json'}")
        print(f"Selected rows CSV: {report_summary['selected_rows_csv']}")
        print(f"Prompt context JSON: {report_summary['prompt_context_rows_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
