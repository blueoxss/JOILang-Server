#!/usr/bin/env python3
# Assumption: this reporter reads generation result CSVs that already live under gpt_mg/version0_14/results/.
from __future__ import annotations

import argparse
import csv
import html
import statistics
import sys
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = VERSION_ROOT / "results"
DEFAULT_RESULTS = [
    RESULTS_DIR / "full_280_rerank.csv",
    RESULTS_DIR / "full_280_rerank_v2.csv",
    RESULTS_DIR / "full_280_rerank_v3.csv",
    RESULTS_DIR / "full_280_rerank_v4.csv",
    RESULTS_DIR / "full_280_rerank_best_of_v2_v3_v4.csv",
]
GENERATION_LABELS = {
    "full_280_rerank.csv": "v1",
    "full_280_rerank_v2.csv": "v2",
    "full_280_rerank_v3.csv": "v3",
    "full_280_rerank_v4.csv": "v4",
    "full_280_rerank_best_of_v2_v3_v4.csv": "best_of_v2_v3_v4",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize DET pass rates across generations and categories.")
    parser.add_argument(
        "--results",
        nargs="*",
        default=None,
        help="Explicit result CSV paths. Defaults to known full-run CSVs under results/.",
    )
    parser.add_argument(
        "--pass-threshold",
        type=float,
        default=50.0,
        help="Rows with det_score >= threshold count as pass. Default: 50.0",
    )
    parser.add_argument(
        "--output-markdown",
        default="results/generation_report.md",
        help="Path for the markdown report. Default: results/generation_report.md",
    )
    parser.add_argument(
        "--output-html",
        default="results/generation_report.html",
        help="Path for the heatmap HTML report. Default: results/generation_report.html",
    )
    parser.add_argument(
        "--output-png",
        default="results/generation_report.png",
        help="Path for the heatmap PNG report. Default: results/generation_report.png",
    )
    parser.add_argument(
        "--output-csv-prefix",
        default="results/generation_report",
        help="Prefix for overall/category CSV tables. Default: results/generation_report",
    )
    return parser


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def detect_results(paths: list[str] | None) -> list[Path]:
    if paths:
        candidates = [Path(item).resolve() if not Path(item).is_absolute() else Path(item) for item in paths]
    else:
        candidates = DEFAULT_RESULTS
    return [path for path in candidates if path.exists()]


def generation_name(path: Path) -> str:
    return GENERATION_LABELS.get(path.name, path.stem)


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def as_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator * 100.0 / denominator


def summarize_generation(rows: list[dict[str, str]], threshold: float) -> dict[str, Any]:
    scores = [as_float(row.get("det_score")) for row in rows]
    pass_rows = [row for row in rows if as_float(row.get("det_score")) >= threshold]
    exact_rows = [row for row in rows if as_bool(row.get("det_gt_exact"))]
    repaired_rows = [row for row in rows if as_bool(row.get("repair_applied"))]
    selected_counts: dict[str, int] = {}
    if any("selected_from" in row for row in rows):
        for row in rows:
            label = row.get("selected_from", "")
            if label:
                selected_counts[label] = selected_counts.get(label, 0) + 1
    return {
        "rows": len(rows),
        "avg_det": statistics.fmean(scores) if scores else 0.0,
        "pass_rate": percent(len(pass_rows), len(rows)),
        "exact_rate": percent(len(exact_rows), len(rows)),
        "exact_count": len(exact_rows),
        "repaired_count": len(repaired_rows),
        "selected_counts": selected_counts,
    }


def summarize_by_category(rows: list[dict[str, str]], threshold: float) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row.get("category", ""), []).append(row)
    summary: dict[str, dict[str, Any]] = {}
    for category, subset in grouped.items():
        scores = [as_float(row.get("det_score")) for row in subset]
        passes = [row for row in subset if as_float(row.get("det_score")) >= threshold]
        exacts = [row for row in subset if as_bool(row.get("det_gt_exact"))]
        summary[category] = {
            "rows": len(subset),
            "avg_det": statistics.fmean(scores) if scores else 0.0,
            "pass_rate": percent(len(passes), len(subset)),
            "exact_rate": percent(len(exacts), len(subset)),
            "exact_count": len(exacts),
        }
    return summary


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    line1 = "| " + " | ".join(headers) + " |"
    line2 = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([line1, line2, *body])


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def threshold_tag(threshold: float) -> str:
    raw = format(threshold, "g").replace(".", "p")
    return f"_t{raw}"


def with_threshold_suffix(path: Path, threshold: float) -> Path:
    suffix = threshold_tag(threshold)
    if path.suffix:
        if path.stem.endswith(suffix):
            return path
        return path.with_name(f"{path.stem}{suffix}{path.suffix}")
    if path.name.endswith(suffix):
        return path
    return path.with_name(f"{path.name}{suffix}")


def resolve_output_path(raw: str | None, threshold: float) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (VERSION_ROOT / path).resolve()
    path = with_threshold_suffix(path, threshold)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def metric_to_color(value: float, *, threshold: float = 50.0) -> str:
    value = max(0.0, min(100.0, value))
    if value <= threshold:
        ratio = 0.0 if threshold <= 0 else value / threshold
        red = 248
        green = int(111 + (226 - 111) * ratio)
        blue = int(111 + (163 - 111) * ratio)
    else:
        ratio = 1.0 if threshold >= 100 else (value - threshold) / (100.0 - threshold)
        red = int(248 + (74 - 248) * ratio)
        green = int(226 + (184 - 226) * ratio)
        blue = int(163 + (108 - 163) * ratio)
    return f"rgb({red}, {green}, {blue})"


def html_table(
    title: str,
    headers: list[str],
    rows: list[list[str]],
    *,
    heatmap_columns: list[int],
    row_best: bool = False,
    threshold: float = 50.0,
) -> str:
    numeric_rows: list[list[float | None]] = []
    for row in rows:
        numeric_row: list[float | None] = []
        for index, cell in enumerate(row):
            if index not in heatmap_columns:
                numeric_row.append(None)
                continue
            cell_value = cell.replace("%", "").strip()
            try:
                numeric_row.append(float(cell_value))
            except Exception:
                numeric_row.append(None)
        numeric_rows.append(numeric_row)

    best_values: list[float | None] = []
    if row_best:
        for numeric_row in numeric_rows:
            values = [value for value in numeric_row if value is not None]
            best_values.append(max(values) if values else None)
    else:
        best_values = [None] * len(numeric_rows)

    output = [f"<section><h2>{html.escape(title)}</h2>", "<table>", "<thead><tr>"]
    for header in headers:
        output.append(f"<th>{html.escape(header)}</th>")
    output.append("</tr></thead><tbody>")
    for row_index, row in enumerate(rows):
        output.append("<tr>")
        for col_index, cell in enumerate(row):
            attrs = ""
            if col_index in heatmap_columns:
                value = numeric_rows[row_index][col_index]
                if value is not None:
                    styles = [f"background:{metric_to_color(value, threshold=threshold)}"]
                    if row_best and best_values[row_index] is not None and abs(value - best_values[row_index]) < 1e-9:
                        styles.append("box-shadow: inset 0 0 0 2px #1f2937")
                        styles.append("font-weight: 700")
                    attrs = f' style="{"; ".join(styles)}"'
            tag = "th" if col_index in {0, 1} else "td"
            output.append(f"<{tag}{attrs}>{html.escape(cell)}</{tag}>")
        output.append("</tr>")
    output.append("</tbody></table></section>")
    return "\n".join(output)


def build_html_report(
    *,
    threshold: float,
    overall_headers: list[str],
    overall_rows: list[list[str]],
    pass_headers: list[str],
    pass_rows: list[list[str]],
    exact_headers: list[str],
    exact_rows: list[list[str]],
    avg_headers: list[str],
    avg_rows: list[list[str]],
) -> str:
    card_html: list[str] = []
    for row in overall_rows:
        card_html.append(
            "\n".join(
                [
                    '<div class="card">',
                    f"<h3>{html.escape(row[0])}</h3>",
                    f'<div class="metric"><span>Avg DET</span><strong>{html.escape(row[3])}</strong></div>',
                    f'<div class="metric"><span>Pass Rate</span><strong>{html.escape(row[4])}</strong></div>',
                    f'<div class="metric"><span>Exact Rate</span><strong>{html.escape(row[5])}</strong></div>',
                    f'<div class="metric"><span>Rows</span><strong>{html.escape(row[2])}</strong></div>',
                    "</div>",
                ]
            )
        )

    overall_metric_headers = ["metric"] + [row[0] for row in overall_rows]
    overall_metric_rows = [
        ["avg_det", *[row[3] for row in overall_rows]],
        [f"pass_rate@{threshold:g}", *[row[4] for row in overall_rows]],
        ["exact_rate", *[row[5] for row in overall_rows]],
    ]

    sections = [
        html_table(
            "Overall Metric Heatmap",
            overall_metric_headers,
            overall_metric_rows,
            heatmap_columns=list(range(1, len(overall_metric_headers))),
            row_best=True,
            threshold=threshold,
        ),
        html_table(
            "Overall Detail",
            overall_headers,
            overall_rows,
            heatmap_columns=[3, 4, 5],
            row_best=False,
            threshold=threshold,
        ),
        html_table(
            "Category Pass Rate",
            pass_headers,
            pass_rows,
            heatmap_columns=list(range(2, len(pass_headers))),
            row_best=True,
            threshold=threshold,
        ),
        html_table(
            "Category Exact Rate",
            exact_headers,
            exact_rows,
            heatmap_columns=list(range(2, len(exact_headers))),
            row_best=True,
            threshold=threshold,
        ),
        html_table(
            "Category Avg DET",
            avg_headers,
            avg_rows,
            heatmap_columns=list(range(2, len(avg_headers))),
            row_best=True,
            threshold=threshold,
        ),
    ]

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en"><head><meta charset="utf-8">',
            "<title>Generation Report</title>",
            "<style>",
            "body { font-family: 'Segoe UI', Helvetica, Arial, sans-serif; margin: 24px; color: #17202a; background: linear-gradient(180deg, #f7fbff 0%, #eef4f8 100%); }",
            "h1 { margin: 0 0 8px; font-size: 28px; }",
            "h2 { margin: 28px 0 12px; font-size: 20px; }",
            ".subtitle { color: #4b5563; margin-bottom: 20px; }",
            ".cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 18px 0 24px; }",
            ".card { background: white; border-radius: 14px; padding: 16px; box-shadow: 0 8px 20px rgba(27, 39, 51, 0.08); border: 1px solid #dce6ef; }",
            ".card h3 { margin: 0 0 12px; font-size: 18px; }",
            ".metric { display: flex; justify-content: space-between; gap: 12px; margin: 8px 0; }",
            ".metric span { color: #64748b; }",
            ".metric strong { font-size: 16px; }",
            "section { margin-bottom: 28px; }",
            "table { border-collapse: separate; border-spacing: 0; width: 100%; background: white; border-radius: 14px; overflow: hidden; box-shadow: 0 8px 20px rgba(27, 39, 51, 0.08); border: 1px solid #dce6ef; }",
            "th, td { padding: 10px 12px; text-align: center; border-bottom: 1px solid #edf2f7; }",
            "thead th { background: #0f172a; color: white; position: sticky; top: 0; }",
            "tbody tr:nth-child(even) { background: #f8fbfd; }",
            "tbody tr:hover { background: #eef6ff; }",
            "tbody th { text-align: left; background: #f3f7fb; }",
            "code { background: #e2ecf5; padding: 2px 6px; border-radius: 6px; }",
            "</style></head><body>",
            "<h1>Generation Report</h1>",
            f'<div class="subtitle">DET pass threshold = <code>{threshold:g}</code>. Higher values trend greener. Row-best cells are outlined.</div>',
            '<div class="cards">' + "\n".join(card_html) + "</div>",
            *sections,
            "</body></html>",
        ]
    )


def maybe_write_png(
    output_path: Path | None,
    *,
    threshold: float,
    overall_rows: list[list[str]],
    pass_headers: list[str],
    pass_rows: list[list[str]],
    exact_headers: list[str],
    exact_rows: list[list[str]],
    avg_headers: list[str],
    avg_rows: list[list[str]],
) -> str | None:
    if output_path is None:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as exc:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as pil_exc:
            return f"PNG skipped: matplotlib unavailable ({exc}); pillow unavailable ({pil_exc})"

        def load_font(size: int) -> Any:
            for name in ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
                try:
                    return ImageFont.truetype(name, size)
                except Exception:
                    continue
            return ImageFont.load_default()

        title_font = load_font(24)
        section_font = load_font(18)
        cell_font = load_font(14)

        overall_metric_headers = ["metric"] + [row[0] for row in overall_rows]
        overall_metric_rows = [
            ["avg_det", *[row[3] for row in overall_rows]],
            [f"pass_rate@{threshold:g}", *[row[4] for row in overall_rows]],
            ["exact_rate", *[row[5] for row in overall_rows]],
        ]
        sections = [
            ("Overall Heatmap", overall_metric_headers, overall_metric_rows, list(range(1, len(overall_metric_headers))), True),
            (f"Category Pass Rate >= {threshold:g}", pass_headers, pass_rows, list(range(2, len(pass_headers))), True),
            ("Category Exact Rate", exact_headers, exact_rows, list(range(2, len(exact_headers))), True),
            ("Category Avg DET", avg_headers, avg_rows, list(range(2, len(avg_headers))), True),
        ]

        cell_height = 34
        title_height = 42
        section_gap = 22
        section_title_gap = 28

        def column_widths(headers: list[str]) -> list[int]:
            widths = []
            for index, header in enumerate(headers):
                if index == 0:
                    widths.append(110)
                elif index == 1:
                    widths.append(70)
                else:
                    widths.append(128)
            return widths

        table_width = max(sum(column_widths(section[1])) for section in sections) + 48
        total_height = 30
        for _title, headers, rows, _heat_cols, _row_best in sections:
            total_height += section_title_gap + cell_height * (len(rows) + 1) + section_gap
        total_height += title_height + 40
        image = Image.new("RGB", (table_width, total_height), "#f7fbff")
        draw = ImageDraw.Draw(image)
        draw.text((24, 18), "Generation Report Heatmap", fill="#17202a", font=title_font)
        draw.text((24, 52), f"DET pass threshold = {threshold:g}", fill="#52606d", font=cell_font)
        y = 88

        def draw_centered_text(box: tuple[int, int, int, int], text: str, *, font: Any, fill: str) -> None:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = box[0] + ((box[2] - box[0]) - text_width) / 2
            y_pos = box[1] + ((box[3] - box[1]) - text_height) / 2 - 1
            draw.text((x, y_pos), text, font=font, fill=fill)

        for title, headers, rows, heat_cols, row_best in sections:
            draw.text((24, y), title, fill="#17202a", font=section_font)
            y += section_title_gap
            widths = column_widths(headers)
            x = 24
            header_y = y
            for index, header in enumerate(headers):
                box = (x, header_y, x + widths[index], header_y + cell_height)
                draw.rounded_rectangle(box, radius=6, fill="#0f172a")
                draw_centered_text(box, header, font=cell_font, fill="white")
                x += widths[index]
            y += cell_height

            best_values: list[float | None] = []
            for row in rows:
                values = []
                for col_index in heat_cols:
                    cell_value = row[col_index].replace("%", "").strip()
                    try:
                        values.append(float(cell_value))
                    except Exception:
                        continue
                best_values.append(max(values) if values else None)

            for row_index, row in enumerate(rows):
                x = 24
                for col_index, cell in enumerate(row):
                    box = (x, y, x + widths[col_index], y + cell_height)
                    fill = "#ffffff" if row_index % 2 == 0 else "#f8fbfd"
                    outline = "#d7e3ee"
                    if col_index in heat_cols:
                        try:
                            numeric_value = float(cell.replace("%", "").strip())
                            fill = metric_to_color(numeric_value, threshold=threshold)
                            if row_best and best_values[row_index] is not None and abs(numeric_value - best_values[row_index]) < 1e-9:
                                outline = "#1f2937"
                        except Exception:
                            pass
                    draw.rounded_rectangle(box, radius=6, fill=fill, outline=outline, width=2 if outline == "#1f2937" else 1)
                    draw_centered_text(box, cell, font=cell_font, fill="#17202a")
                    x += widths[col_index]
                y += cell_height
            y += section_gap

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        return None

    def to_matrix(rows: list[list[str]], start_col: int) -> Any:
        matrix = []
        for row in rows:
            values = []
            for cell in row[start_col:]:
                cell_value = cell.replace("%", "").strip()
                try:
                    values.append(float(cell_value))
                except Exception:
                    values.append(0.0)
            matrix.append(values)
        return np.array(matrix, dtype=float)

    def draw_heatmap(ax: Any, matrix: Any, row_labels: list[str], col_labels: list[str], title: str) -> None:
        image = ax.imshow(matrix, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
        ax.set_title(title, fontsize=12, pad=10)
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=30, ha="right", fontsize=9)
        ax.set_yticks(range(len(row_labels)))
        ax.set_yticklabels(row_labels, fontsize=9)
        for row_index in range(matrix.shape[0]):
            for col_index in range(matrix.shape[1]):
                value = matrix[row_index, col_index]
                color = "black" if value < 82 else "white"
                ax.text(col_index, row_index, f"{value:.1f}", ha="center", va="center", fontsize=8, color=color)
        ax.figure.colorbar(image, ax=ax, fraction=0.04, pad=0.02)

    overall_metric_labels = ["avg_det", f"pass_rate@{threshold:g}", "exact_rate"]
    overall_metric_matrix = to_matrix(
        [
            ["avg_det", *[row[3] for row in overall_rows]],
            [f"pass_rate@{threshold:g}", *[row[4] for row in overall_rows]],
            ["exact_rate", *[row[5] for row in overall_rows]],
        ],
        1,
    )
    overall_col_labels = [row[0] for row in overall_rows]
    pass_matrix = to_matrix(pass_rows, 2)
    exact_matrix = to_matrix(exact_rows, 2)
    avg_matrix = to_matrix(avg_rows, 2)
    category_labels = [row[0] for row in pass_rows]
    generation_labels = pass_headers[2:]

    figure, axes = plt.subplots(4, 1, figsize=(max(12, len(generation_labels) * 2.2), 22), constrained_layout=True)
    draw_heatmap(axes[0], overall_metric_matrix, overall_metric_labels, overall_col_labels, "Overall Heatmap")
    draw_heatmap(axes[1], pass_matrix, category_labels, generation_labels, f"Category Pass Rate >= {threshold:g}")
    draw_heatmap(axes[2], exact_matrix, category_labels, generation_labels, "Category Exact Rate")
    draw_heatmap(axes[3], avg_matrix, category_labels, generation_labels, "Category Avg DET")
    figure.suptitle("Generation Report Heatmap", fontsize=16)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)
    return None


def main() -> int:
    args = build_parser().parse_args()
    result_paths = detect_results(args.results)
    if not result_paths:
        print("No generation result CSVs found.", file=sys.stderr)
        return 1

    overall_rows: list[list[str]] = []
    category_summaries: dict[str, dict[str, dict[str, Any]]] = {}

    for path in result_paths:
        name = generation_name(path)
        rows = load_rows(path)
        generation_summary = summarize_generation(rows, args.pass_threshold)
        overall_rows.append(
            [
                name,
                str(path.relative_to(VERSION_ROOT)),
                str(generation_summary["rows"]),
                f"{generation_summary['avg_det']:.4f}",
                f"{generation_summary['pass_rate']:.2f}%",
                f"{generation_summary['exact_rate']:.2f}%",
                str(generation_summary["exact_count"]),
                str(generation_summary["repaired_count"]),
                ", ".join(
                    f"{label}:{count}"
                    for label, count in sorted(generation_summary["selected_counts"].items())
                )
                or "-",
            ]
        )
        category_summaries[name] = summarize_by_category(rows, args.pass_threshold)

    categories = sorted(
        {
            category
            for generation_summary in category_summaries.values()
            for category in generation_summary.keys()
        },
        key=lambda value: (int(value) if str(value).isdigit() else str(value)),
    )

    pass_headers = ["category", "rows"] + [generation_name(path) for path in result_paths]
    exact_headers = ["category", "rows"] + [generation_name(path) for path in result_paths]
    avg_headers = ["category", "rows"] + [generation_name(path) for path in result_paths]
    pass_rows: list[list[str]] = []
    exact_rows: list[list[str]] = []
    avg_rows: list[list[str]] = []
    reference_generation = generation_name(result_paths[0])

    for category in categories:
        row_count = category_summaries[reference_generation].get(category, {}).get("rows", 0)
        pass_row = [category, str(row_count)]
        exact_row = [category, str(row_count)]
        avg_row = [category, str(row_count)]
        for path in result_paths:
            name = generation_name(path)
            entry = category_summaries[name].get(category, {})
            pass_row.append(f"{entry.get('pass_rate', 0.0):.2f}%")
            exact_row.append(f"{entry.get('exact_rate', 0.0):.2f}%")
            avg_row.append(f"{entry.get('avg_det', 0.0):.4f}")
        pass_rows.append(pass_row)
        exact_rows.append(exact_row)
        avg_rows.append(avg_row)

    overall_headers = [
        "generation",
        "csv",
        "rows",
        "avg_det",
        f"pass_rate@{args.pass_threshold:g}",
        "exact_rate",
        "exact_count",
        "repaired_count",
        "selected_from",
    ]

    report_lines = [
        f"# Generation Report (pass threshold = {args.pass_threshold:g})",
        "",
        "## Overall",
        markdown_table(overall_headers, overall_rows),
        "",
        "## Category Pass Rate",
        markdown_table(pass_headers, pass_rows),
        "",
        "## Category Exact Rate",
        markdown_table(exact_headers, exact_rows),
        "",
        "## Category Avg DET",
        markdown_table(avg_headers, avg_rows),
        "",
    ]
    report_text = "\n".join(report_lines)
    print(report_text)

    markdown_path = resolve_output_path(args.output_markdown, args.pass_threshold)
    html_path = resolve_output_path(args.output_html, args.pass_threshold)
    png_path = resolve_output_path(args.output_png, args.pass_threshold)
    csv_prefix = resolve_output_path(args.output_csv_prefix, args.pass_threshold)

    if markdown_path:
        markdown_path.write_text(report_text, encoding="utf-8")

    if html_path:
        html_text = build_html_report(
            threshold=args.pass_threshold,
            overall_headers=overall_headers,
            overall_rows=overall_rows,
            pass_headers=pass_headers,
            pass_rows=pass_rows,
            exact_headers=exact_headers,
            exact_rows=exact_rows,
            avg_headers=avg_headers,
            avg_rows=avg_rows,
        )
        html_path.write_text(html_text, encoding="utf-8")

    if csv_prefix:
        write_csv(csv_prefix.with_name(csv_prefix.name + "_overall.csv"), overall_headers, overall_rows)
        write_csv(csv_prefix.with_name(csv_prefix.name + "_category_pass.csv"), pass_headers, pass_rows)
        write_csv(csv_prefix.with_name(csv_prefix.name + "_category_exact.csv"), exact_headers, exact_rows)
        write_csv(csv_prefix.with_name(csv_prefix.name + "_category_avg.csv"), avg_headers, avg_rows)

    png_warning = maybe_write_png(
        png_path,
        threshold=args.pass_threshold,
        overall_rows=overall_rows,
        pass_headers=pass_headers,
        pass_rows=pass_rows,
        exact_headers=exact_headers,
        exact_rows=exact_rows,
        avg_headers=avg_headers,
        avg_rows=avg_rows,
    )

    print("")
    if markdown_path:
        print(f"saved_markdown: {markdown_path.relative_to(VERSION_ROOT)}")
    if html_path:
        print(f"saved_html: {html_path.relative_to(VERSION_ROOT)}")
    if png_path and png_warning is None:
        print(f"saved_png: {png_path.relative_to(VERSION_ROOT)}")
    if csv_prefix:
        print(f"saved_csv_prefix: {csv_prefix.relative_to(VERSION_ROOT)}")
    if png_warning:
        print(png_warning, file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
