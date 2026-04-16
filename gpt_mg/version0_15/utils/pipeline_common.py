#!/usr/bin/env python3
# Assumption: this file lives under gpt_mg/version0_15/utils/ and the repo root is three levels up.
from __future__ import annotations

import ast
import csv
import json
import os
import random
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


VERSION_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = VERSION_ROOT.parents[1]
BLOCKS_DIR = VERSION_ROOT / "blocks"
GENOMES_DIR = VERSION_ROOT / "genomes"
RESULTS_DIR = VERSION_ROOT / "results"
LOGS_DIR = VERSION_ROOT / "logs"
CHECKPOINTS_DIR = VERSION_ROOT / "checkpoints"
DATASET_DEFAULT = REPO_ROOT / "datasets" / "JOICommands-280.csv"
SERVICE_SCHEMA_DEFAULT = REPO_ROOT / "datasets" / "service_list_ver2.0.1.json"


BLOCK_FILE_MAP = {
    "01": "01_preamble.txt",
    "02": "02_generator_prompt.txt",
    "03": "03_postprocessor.txt",
    "04": "04_reranker_prompt.txt",
    "05": "05_repair_prompt.txt",
    "06": "06_det_helper.txt",
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "if", "in", "into",
    "is", "it", "its", "me", "of", "on", "or", "than", "that", "the", "then", "this",
    "to", "up", "with", "whenever", "when", "while", "through", "after", "before", "every",
    "all", "any", "tell", "please", "make", "set", "change", "turn", "switch", "start",
}

DEFAULT_CANDIDATE_STRATEGIES = [
    "direct",
    "minimal",
    "canonical_names_first",
    "explicit_preconditions",
    "compact_json",
]

MEMBER_AFTER_RECEIVER_RE = re.compile(
    r"(?P<receiver>all\([^\n\r()]+\)|\([^\n\r()]+\))\.(?P<member>[A-Za-z_][A-Za-z0-9_]*)"
)


def ensure_workspace() -> None:
    for path in (BLOCKS_DIR, GENOMES_DIR, RESULTS_DIR, LOGS_DIR, CHECKPOINTS_DIR, BLOCKS_DIR / "generated"):
        path.mkdir(parents=True, exist_ok=True)


def load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: str | Path, payload: Any, *, indent: int = 2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=indent)
        f.write("\n")


def append_jsonl(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def atomic_write_csv(path: str | Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.stem + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with tmp_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in fieldnames})
        shutil.move(str(tmp_path), str(path))
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def load_dataset_rows(dataset_path: str | Path = DATASET_DEFAULT) -> list[dict[str, str]]:
    with Path(dataset_path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def normalize_categories(values: list[str] | tuple[str, ...] | None) -> set[str]:
    normalized: set[str] = set()
    for raw in values or []:
        for item in str(raw).split(","):
            token = item.strip()
            if token:
                normalized.add(token)
    return normalized


def select_rows(
    rows: list[dict[str, str]],
    *,
    start_row: int = 1,
    end_row: int | None = None,
    limit: int | None = None,
    categories: list[str] | tuple[str, ...] | None = None,
) -> list[tuple[int, dict[str, str]]]:
    selected: list[tuple[int, dict[str, str]]] = []
    if start_row < 1:
        start_row = 1
    last = end_row if end_row is not None else len(rows)
    category_filter = normalize_categories(categories)
    for idx, row in enumerate(rows, start=1):
        if idx < start_row or idx > last:
            continue
        if category_filter and str(row.get("category", "")).strip() not in category_filter:
            continue
        selected.append((idx, row))
        if limit is not None and len(selected) >= limit:
            break
    return selected


def parse_connected_devices(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if not text:
        return {}
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    return {}


def slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "item"


def split_camel_tokens(value: str) -> list[str]:
    if not value:
        return []
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = spaced.replace("_", " ").replace("-", " ")
    return [token.lower() for token in spaced.split() if token]


def tokenize_command(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9]+", (text or "").lower())
    return [token for token in tokens if token not in STOPWORDS]


def extract_command_numbers(text: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", text or "")


def canonical_service_name(device: str, service_name: str) -> str:
    return f"{device}_{service_name}"


def lowercase_output_member_name(member: str) -> str:
    return str(member or "").lower()


def lowercase_service_members_in_code(code: str) -> str:
    text = str(code or "")
    if not text:
        return text

    def repl(match: re.Match[str]) -> str:
        return f"{match.group('receiver')}.{lowercase_output_member_name(match.group('member'))}"

    return MEMBER_AFTER_RECEIVER_RE.sub(repl, text)


def load_service_schema(service_schema_path: str | Path = SERVICE_SCHEMA_DEFAULT) -> dict[str, dict[str, Any]]:
    return load_json(service_schema_path)


def unique_preserve_order(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token:
            continue
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(token)
    return ordered


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = [value]

    normalized: list[str] = []
    for raw in raw_items:
        if raw is None:
            continue
        for token in str(raw).split(","):
            cleaned = token.strip()
            if cleaned:
                normalized.append(cleaned)
    return unique_preserve_order(normalized)


def resolve_schema_category(raw_category: Any, service_schema: dict[str, dict[str, Any]]) -> str:
    token = str(raw_category or "").strip()
    if not token:
        return ""
    if token in service_schema:
        return token
    lowered = token.casefold()
    for candidate in service_schema.keys():
        if candidate.casefold() == lowered:
            return candidate
    return ""


def build_service_record(category: str, service_name: str, meta: dict[str, Any]) -> dict[str, Any]:
    record = {
        "service": service_name,
        "canonical_name": canonical_service_name(category, service_name),
        "canonical_name_lower": lowercase_output_member_name(canonical_service_name(category, service_name)),
        "type": meta.get("type", ""),
    }
    for key in (
        "argument_type",
        "argument_bounds",
        "argument_format",
        "argument_descriptor",
        "return_type",
        "return_bounds",
        "return_descriptor",
        "descriptor",
    ):
        value = meta.get(key)
        if value not in (None, "", []):
            record[key] = value

    enums_descriptor = meta.get("enums_descriptor") or []
    if enums_descriptor:
        enums: list[str] = []
        for raw in enums_descriptor:
            enum_text = str(raw).split(" - ", 1)[0].strip()
            if enum_text:
                enums.append(enum_text)
        if enums:
            record["enums"] = enums
    return record


def build_receiver_examples(category: str, selector_tags: list[str]) -> list[str]:
    examples = [f"(#{category})"]
    for tag in selector_tags:
        examples.append(f"(#{tag} #{category})")
    if len(selector_tags) > 1:
        examples.append("(" + " ".join(f"#{tag}" for tag in selector_tags + [category]) + ")")
    if selector_tags:
        examples.append("all(" + " ".join(f"#{tag}" for tag in selector_tags + [category]) + ")")
    else:
        examples.append(f"all(#{category})")
    return unique_preserve_order(examples)


def build_capability_binding(
    category: str,
    *,
    user_defined_tags: list[str],
    locations: list[str],
    service_schema: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    selector_tags = unique_preserve_order(locations + user_defined_tags)
    services = service_schema.get(category, {})
    return {
        "category": category,
        "category_tag": f"#{category}",
        "user_defined_tags": user_defined_tags,
        "locations": locations,
        "selector_tags": selector_tags,
        "receiver_templates": [
            "(#<Category>)",
            "(#<selector_tag> #<Category>)",
            "(#<location> #<selector_tag> #<Category>)",
            "all(#<location> #<selector_tag> #<Category>)",
        ],
        "receiver_examples": build_receiver_examples(category, selector_tags),
        "services": [
            build_service_record(category, service_name, meta)
            for service_name, meta in sorted(services.items())
        ],
    }


def build_connected_device_groups(
    connected_devices: dict[str, Any],
    service_schema: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for group_id, meta in sorted(connected_devices.items(), key=lambda item: str(item[0])):
        raw_categories = normalize_string_list(meta.get("category"))
        resolved_categories: list[str] = []
        ignored_categories: list[str] = []
        for raw_category in raw_categories:
            category = resolve_schema_category(raw_category, service_schema)
            if category:
                resolved_categories.append(category)
            elif raw_category:
                ignored_categories.append(raw_category)
        resolved_categories = unique_preserve_order(resolved_categories)
        category_keys = {category.casefold() for category in resolved_categories}

        user_defined_tags = [
            tag
            for tag in normalize_string_list(meta.get("tags"))
            if tag.casefold() not in category_keys
        ]
        locations = [
            location
            for location in normalize_string_list(meta.get("locations"))
            if location.casefold() not in category_keys
        ]

        group_entry = {
            "group_id": str(group_id),
            "source": "connected_devices",
            "categories": resolved_categories,
            "user_defined_tags": user_defined_tags,
            "locations": locations,
            "capability_bindings": [
                build_capability_binding(
                    category,
                    user_defined_tags=user_defined_tags,
                    locations=locations,
                    service_schema=service_schema,
                )
                for category in resolved_categories
            ],
        }
        if ignored_categories:
            group_entry["ignored_categories"] = ignored_categories
        groups.append(group_entry)
    return groups


def build_schema_fallback_groups(service_schema: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "group_id": f"schema::{category}",
            "source": "service_schema_fallback",
            "categories": [category],
            "user_defined_tags": [],
            "locations": [],
            "capability_bindings": [
                build_capability_binding(
                    category,
                    user_defined_tags=[],
                    locations=[],
                    service_schema=service_schema,
                )
            ],
        }
        for category in sorted(service_schema.keys())
    ]


def build_service_snippet(
    command_eng: str,
    connected_devices: dict[str, Any],
    service_schema: dict[str, dict[str, Any]],
    *,
    max_devices: int = 8,
) -> str:
    del command_eng, max_devices
    if connected_devices:
        device_groups = build_connected_device_groups(connected_devices, service_schema)
        snippet_source = "connected_devices_only"
    else:
        device_groups = build_schema_fallback_groups(service_schema)
        snippet_source = "service_schema_fallback"

    snippet: dict[str, Any] = {
        "snippet_source": snippet_source,
        "canonical_rule": (
            "Resolve schema matches against canonical_name. "
            "In final JOILang code, keep receiver tags after # exactly as written, "
            "but lowercase the member token after ). or all(...). . "
            "For example, Switch_On becomes switch_on."
        ),
        "binding_rule": [
            "Each device_group is one connected-device group or one schema fallback group.",
            "Each capability_binding pairs one category with the full authoritative service list for that category.",
            "user_defined_tags come from tags after removing category duplicates.",
            "locations are additional selector tags that can also be combined with the category.",
            "selector_tags are the usable extra tags that may be prepended before the category in a receiver.",
            "If the command does not mention any selector tag, the base receiver (#Category) is valid.",
            "If the command mentions locations or custom tags, preserve only the relevant selector tags before the category.",
        ],
        "device_groups": device_groups,
    }
    return json.dumps(snippet, ensure_ascii=False, indent=2)


def parse_block_file(path: str | Path) -> tuple[dict[str, str], str]:
    metadata: dict[str, str] = {}
    body_lines: list[str] = []
    in_header = True
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if in_header and line.startswith("# ") and ":" in line:
                key, value = line[2:].split(":", 1)
                metadata[key.strip()] = value.strip()
                continue
            in_header = False
            body_lines.append(line)
    return metadata, "".join(body_lines).lstrip("\n")


def resolve_block_path(block_id: str, block_params: dict[str, Any] | None = None) -> Path:
    block_params = block_params or {}
    source_file = block_params.get("source_file")
    if source_file:
        path = Path(source_file)
        if not path.is_absolute():
            path = BLOCKS_DIR / source_file
        return path
    filename = BLOCK_FILE_MAP[block_id]
    return BLOCKS_DIR / filename


def limit_exemplars(block_text: str, *, few_shot_count: int | None) -> str:
    if few_shot_count is None or few_shot_count >= 3:
        return block_text
    pattern = re.compile(r"(?=^### EXEMPLAR \d+\b)", re.MULTILINE)
    pieces = pattern.split(block_text)
    if len(pieces) <= 1:
        return block_text
    prefix = pieces[0]
    exemplars = [piece for piece in pieces[1:] if piece.strip()]
    kept = exemplars[: max(0, few_shot_count)]
    return prefix + "".join(kept)


def render_placeholders(template: str, values: dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered


def _extract_json_block(text: str) -> str:
    stripped = (text or "").strip()
    if not stripped:
        return stripped
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            stripped = "\n".join(lines[1:-1]).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    if stripped.startswith("[") and stripped.endswith("]"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def normalize_candidate_json_text(
    text: str,
    *,
    default_cron: str = "",
    default_period: int = 0,
) -> str:
    raw = (text or "").strip()
    if not raw:
        return raw
    candidate = _extract_json_block(raw)
    try:
        parsed = json.loads(candidate)
    except Exception:
        return raw
    if isinstance(parsed, list):
        if not parsed or not isinstance(parsed[0], dict):
            return raw
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        return raw

    normalized = {
        "name": str(parsed.get("name", "") or ""),
        "cron": str(parsed.get("cron", "") or ""),
        "period": parsed.get("period", default_period),
        "code": lowercase_service_members_in_code(str(parsed.get("code", "") or "")),
    }
    try:
        normalized["period"] = int(normalized["period"])
    except Exception:
        normalized["period"] = default_period
    if not normalized["cron"] and normalized["period"] < 0:
        normalized["period"] = default_period
    if normalized["cron"] == "":
        normalized["period"] = default_period if normalized["period"] < 0 else normalized["period"]
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))


def render_block(
    block_id: str,
    *,
    values: dict[str, Any],
    block_params: dict[str, Any] | None = None,
) -> tuple[dict[str, str], str, Path]:
    block_params = block_params or {}
    path = resolve_block_path(block_id, block_params)
    metadata, body = parse_block_file(path)
    few_shot_count = block_params.get("few_shot_count")
    if few_shot_count is None and metadata.get("params"):
        few_shot_count = None
    body = limit_exemplars(body, few_shot_count=few_shot_count)
    micro_rules = block_params.get("micro_rules") or []
    if micro_rules:
        micro_rule_text = "\n".join(f"- {rule}" for rule in micro_rules)
        body += f"\n\nACTIVE MICRO-RULES\n{micro_rule_text}\n"
    body = render_placeholders(body, values)
    return metadata, body, path


def render_blocks_for_genome(
    genome: dict[str, Any],
    *,
    values: dict[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
    blocks = genome.get("blocks") or []
    block_params_map = genome.get("block_params") or {}
    rendered_blocks: list[str] = []
    manifest: list[dict[str, Any]] = []
    for block_id in blocks:
        metadata, body, path = render_block(
            block_id,
            values=values,
            block_params=block_params_map.get(block_id, {}),
        )
        rendered_blocks.append(body.rstrip())
        manifest.append({
            "id": block_id,
            "path": str(path),
            "metadata": metadata,
        })
    return "\n\n".join(block for block in rendered_blocks if block.strip()), manifest


def load_genome(genome_path: str | Path) -> dict[str, Any]:
    genome = load_json(genome_path)
    genome.setdefault("blocks", ["01", "02", "03", "06"])
    genome.setdefault("params", {})
    genome.setdefault("block_params", {})
    genome.setdefault("seed", 0)
    return genome


def make_run_id(prefix: str, seed: int) -> str:
    return f"{slugify(prefix)}_{seed}"


def sample_rows(
    rows: list[tuple[int, dict[str, str]]],
    *,
    sample_size: int,
    seed: int,
    exclude_row_nos: set[int] | None = None,
) -> list[tuple[int, dict[str, str]]]:
    exclude_row_nos = exclude_row_nos or set()
    eligible = [item for item in rows if item[0] not in exclude_row_nos]
    if sample_size >= len(eligible):
        return list(eligible)
    rng = random.Random(seed)
    selected = list(eligible)
    rng.shuffle(selected)
    return sorted(selected[:sample_size], key=lambda item: item[0])


def extract_optional_schedule(row: dict[str, str]) -> tuple[str, str]:
    cron = row.get("cron", "")
    period = row.get("period", "0")
    if cron is None or cron == "":
        cron = ""
    if period in (None, ""):
        period = "0"
    return str(cron), str(period)


def build_prompt_values(
    row_no: int,
    row: dict[str, str],
    service_schema: dict[str, dict[str, Any]],
    *,
    candidate_strategy: str,
    det_diagnostics: str = "",
    best_candidate: str = "",
    failure_summary: str = "",
) -> dict[str, Any]:
    connected_devices = parse_connected_devices(row.get("connected_devices", ""))
    cron, period = extract_optional_schedule(row)
    service_snippet = build_service_snippet(row.get("command_eng", ""), connected_devices, service_schema)
    return {
        "row_no": row_no,
        "command_eng": row.get("command_eng", ""),
        "connected_devices": json.dumps(connected_devices, ensure_ascii=False, indent=2),
        "service_list_snippet": service_snippet,
        "optional_cron": cron,
        "optional_period": period,
        "cron": cron,
        "period": period,
        "candidate_strategy": candidate_strategy,
        "det_diagnostics": det_diagnostics,
        "best_candidate": best_candidate,
        "failure_summary": failure_summary,
    }


def unique_fieldnames(rows: list[dict[str, Any]], extra_fields: list[str]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.append(key)
    for key in extra_fields:
        if key not in seen:
            seen.append(key)
    return seen


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def seeded_uuid(rng: random.Random) -> str:
    alphabet = "0123456789abcdef"
    chunks = [8, 4, 4, 4, 12]
    return "-".join("".join(rng.choice(alphabet) for _ in range(size)) for size in chunks)
