#!/usr/bin/env python3
from __future__ import annotations

import copy
import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .artifacts import utc_now, write_json
except ImportError:
    from artifacts import utc_now, write_json  # type: ignore

try:
    from utils.prompt_advisor.schemas import FAMILY_TO_DEFAULT_BLOCK, normalize_patch
except Exception:  # pragma: no cover - fallback for standalone use
    FAMILY_TO_DEFAULT_BLOCK = {"Service_Mapping": "02", "Output_Schema": "03", "Repair_Clause": "05", "DET_Helper": "06"}

    def normalize_patch(raw: dict[str, Any], index: int = 0) -> dict[str, Any]:
        patch = dict(raw)
        patch.setdefault("patch_id", f"patch_{index:03d}")
        patch.setdefault("target_block_family", "DET_Helper")
        patch.setdefault("target_block_id", FAMILY_TO_DEFAULT_BLOCK.get(patch["target_block_family"], "06"))
        patch.setdefault("operation", "append_micro_rule")
        patch.setdefault("patch_text", "")
        return patch


CORE_BLOCKS = ("01", "02")
OPTIONAL_BLOCKS = ("03", "05", "06")
BLOCK_ORDER = ("01", "02", "03", "05", "06")

# --- WI-09: render the B/O/V/E genotype axes into the emitted prompt ----------
try:
    from .prompt_decomposer import decompose_prompt_to_blocks
except ImportError:  # pragma: no cover - fallback for standalone use
    from prompt_decomposer import decompose_prompt_to_blocks  # type: ignore

# Map each decomposed monolith family to a genome block id (01/02/03/05/06).
FAMILY_TO_GENOME_BLOCK = {
    "preamble": "01",
    "service_mapping": "02",
    "service_list": "02",
    "connected_devices": "02",
    "grammar": "03",
    "output_contract": "03",
    "temporal_rules": "05",
    "caution": "05",
    "examples": "06",
    "response_contract": "06",
    "reasoning_contract": "06",
    "misc": "06",
}
# Only these families may be dropped when their genome block is toggled off (B).
# Every other family is kept even if its block id is inactive, so B never removes
# schema, grammar, output-contract or temporal core content and breaks generation.
OPTIONAL_FAMILIES = {"caution", "examples", "response_contract", "reasoning_contract", "misc"}
DEFAULT_BLOCK_VERSION = "v1"


def _genome_block_for(family: str) -> str:
    return FAMILY_TO_GENOME_BLOCK.get(str(family or "misc"), "06")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fallback_genome() -> dict[str, Any]:
    return {"id": "patched_base", "blocks": ["01", "02", "03", "06"], "params": {}, "block_params": {}, "seed": 0}


def load_base_genome(path: str | Path | None = None) -> dict[str, Any]:
    if path and Path(path).exists():
        data = read_json(path)
        return ensure_genome(data if isinstance(data, dict) else {})
    return fallback_genome()


def normalize_blocks(blocks: Any) -> list[str]:
    requested = [str(block).zfill(2) for block in (blocks if isinstance(blocks, list) else [])]
    active = ["01", "02"]
    for block in BLOCK_ORDER:
        if block in CORE_BLOCKS:
            continue
        if block in requested and block not in active:
            active.append(block)
    return active


def ensure_genome(genome: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(genome)
    out["blocks"] = normalize_blocks(out.get("blocks") or ["01", "02", "03", "06"])
    out.setdefault("params", {})
    out.setdefault("block_params", {})
    out.setdefault("advisor_metadata", {})
    return out


def patch_list(patches_output: dict[str, Any]) -> list[dict[str, Any]]:
    raw_patches = patches_output.get("prompt_patches", []) if isinstance(patches_output, dict) else []
    return [normalize_patch(patch if isinstance(patch, dict) else {}, index) for index, patch in enumerate(raw_patches, start=1)]


def _add_block(genome: dict[str, Any], block_id: str) -> None:
    block_id = str(block_id).zfill(2)
    blocks = list(genome.get("blocks") or [])
    if block_id in OPTIONAL_BLOCKS and block_id not in blocks:
        blocks.append(block_id)
    genome["blocks"] = normalize_blocks(blocks)


def _append_micro_rule(genome: dict[str, Any], block_id: str, text: str) -> bool:
    if not text.strip():
        return False
    _add_block(genome, block_id)
    params = genome.setdefault("block_params", {}).setdefault(str(block_id).zfill(2), {})
    rules = list(params.get("micro_rules") or [])
    if text not in rules:
        rules.append(text)
        params["micro_rules"] = rules
        return True
    params["micro_rules"] = rules
    return False


def _replace_block_text(genome: dict[str, Any], block_id: str, text: str) -> bool:
    if not text.strip():
        return False
    _add_block(genome, block_id)
    params = genome.setdefault("block_params", {}).setdefault(str(block_id).zfill(2), {})
    previous = str(params.get("replacement_text") or "")
    params["replacement_text"] = text
    return previous != text


def _reduce_few_shot(genome: dict[str, Any], block_id: str) -> bool:
    _add_block(genome, block_id)
    params = genome.setdefault("block_params", {}).setdefault(str(block_id).zfill(2), {})
    before = params.get("few_shot_count")
    params["few_shot_count"] = 0 if before is None else max(0, int(before) - 1)
    return params["few_shot_count"] != before


def _compress_candidate_strategies(genome: dict[str, Any]) -> bool:
    params = genome.setdefault("params", {})
    before = list(params.get("candidate_strategies") or [])
    if not before:
        params["candidate_strategies"] = ["direct", "compact_json"]
        return True
    kept = []
    for item in before:
        if item not in kept:
            kept.append(item)
        if len(kept) >= 2:
            break
    params["candidate_strategies"] = kept
    return kept != before


def apply_patch_to_genome(genome: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    operation = str(patch.get("operation") or "append_micro_rule")
    family = str(patch.get("target_block_family") or "DET_Helper")
    block_id = str(patch.get("target_block_id") or FAMILY_TO_DEFAULT_BLOCK.get(family, "06")).zfill(2)
    text = str(patch.get("patch_text") or "")
    changed = False
    if operation in {"append_micro_rule", "strengthen_existing_rule", "diversify_micro_rules", "promote_gene_to_dynamic_core", "demote_gene_to_optional"}:
        changed = _append_micro_rule(genome, block_id, text)
    elif operation == "activate_optional_block":
        before = list(genome.get("blocks") or [])
        _add_block(genome, block_id)
        changed = before != genome.get("blocks")
    elif operation == "deactivate_optional_block":
        if block_id not in CORE_BLOCKS:
            before = list(genome.get("blocks") or [])
            genome["blocks"] = normalize_blocks([block for block in before if block != block_id])
            changed = before != genome["blocks"]
    elif operation in {"delete_conflicting_rule", "suppress_gene"}:
        genome.setdefault("advisor_metadata", {}).setdefault("suppressed_patch_ids", []).append(patch.get("patch_id"))
        changed = True
    elif operation in {"replace_sentence", "replace_block_text"}:
        changed = _replace_block_text(genome, block_id, text)
    elif operation == "reduce_few_shot":
        changed = _reduce_few_shot(genome, block_id)
    elif operation == "compress_candidate_strategies":
        changed = _compress_candidate_strategies(genome)
    genome.setdefault("advisor_metadata", {}).setdefault("applied_patch_ids", []).append(patch.get("patch_id"))
    return {"patch_id": patch.get("patch_id"), "operation": operation, "target_block_id": block_id, "target_block_family": family, "changed": changed, "patch_text": text}


def _legacy_overlay(base: str, genome: dict[str, Any]) -> str:
    """Original behaviour: append micro_rules / replacement_text as an overlay.
    Used as a fallback when the base prompt cannot be decomposed into blocks."""
    lines = []
    for block_id, params in (genome.get("block_params") or {}).items():
        rules = params.get("micro_rules") if isinstance(params, dict) else []
        if rules:
            lines.append(f"[GA block {block_id} micro_rules]")
            lines.extend(f"- {rule}" for rule in rules)
        replacement = params.get("replacement_text") if isinstance(params, dict) else ""
        if replacement:
            lines.append(f"[GA block {block_id} replacement_text]")
            lines.append(str(replacement))
    if not lines:
        return base
    return base.rstrip() + "\n\n---\n[GA Prompt Patch Overlay]\n" + "\n".join(lines) + "\n"


def _assemble_prompt_from_genome(system_text: str, genome: dict[str, Any]) -> str | None:
    """Assemble the system prompt from its decomposed blocks so the B/O/V/E axes
    change the emitted text. Returns None when the text is not decomposable
    (caller then falls back to the legacy overlay). Deterministic."""
    blocks = decompose_prompt_to_blocks(system_text)
    if len(blocks) < 2:
        return None
    active = list(genome.get("blocks") or ["01", "02"])
    active_set = set(active)
    block_params = genome.get("block_params") or {}
    few_shot = (genome.get("params") or {}).get("few_shot_count")
    order_index = {bid: i for i, bid in enumerate(active)}

    def order_key(gid: str, blk: dict[str, Any]):
        # active blocks keep the genome's order (O); inactive-but-kept blocks
        # fall to the tail in canonical BLOCK_ORDER.
        primary = order_index.get(gid, len(active) + (BLOCK_ORDER.index(gid) if gid in BLOCK_ORDER else 99))
        return (primary, blk.get("order", 0))

    kept: list[tuple[str, dict[str, Any]]] = []
    examples_kept = False
    for blk in blocks:
        family = str(blk.get("family") or "misc")
        gid = _genome_block_for(family)
        if family in OPTIONAL_FAMILIES and gid in OPTIONAL_BLOCKS and gid not in active_set:
            continue  # B: drop only genuinely-optional families
        if family == "examples":
            examples_kept = True
        kept.append((gid, blk))
    kept.sort(key=lambda item: order_key(item[0], item[1]))

    pieces: list[str] = []
    rules_emitted: set[str] = set()
    for gid, blk in kept:
        params = block_params.get(gid) if isinstance(block_params.get(gid), dict) else {}
        text = str((params or {}).get("replacement_text") or blk.get("text") or "")
        directives = []
        version = str((params or {}).get("version") or "")
        if version and version != DEFAULT_BLOCK_VERSION:  # V axis
            directives.append(f"[GA:{gid}:style={version}]")
        if str(blk.get("family")) == "examples" and few_shot is not None:  # E axis
            directives.append(f"[GA:{gid}:few_shot<={int(few_shot)}]")
        seg = ("\n".join(directives) + "\n" + text) if directives else text
        pieces.append(seg.rstrip("\n"))
        rules = (params or {}).get("micro_rules") or []  # R axis
        if rules and gid not in rules_emitted:
            pieces.append(f"[GA block {gid} micro_rules]\n" + "\n".join(f"- {r}" for r in rules))
            rules_emitted.add(gid)

    overlay: list[str] = []
    if few_shot is not None and not examples_kept:
        overlay.append(f"[GA:few_shot<={int(few_shot)}]")  # keep E effective even with no examples block
    for gid, params in block_params.items():  # rules whose block never rendered
        if gid in rules_emitted or not isinstance(params, dict):
            continue
        for rule in params.get("micro_rules") or []:
            overlay.append(f"[GA block {gid} micro_rules] - {rule}")
        if params.get("replacement_text") and gid not in {g for g, _ in kept}:
            overlay.append(f"[GA block {gid} replacement_text]\n{params['replacement_text']}")

    body = "\n\n".join(p for p in pieces if p.strip())
    if overlay:
        body = body.rstrip() + "\n\n---\n[GA Prompt Patch Overlay]\n" + "\n".join(overlay)
    return body


def rendered_prompt_with_genome(rendered_package: dict[str, Any] | None, genome: dict[str, Any]) -> str:
    pkg = rendered_package or {}
    system_text = str(pkg.get("system_prompt") or "")
    user_text = str(pkg.get("user_prompt") or "")
    base = str(pkg.get("prompt_text") or "")
    source = system_text or base
    assembled = _assemble_prompt_from_genome(source, genome) if source else None
    if assembled is None:
        return _legacy_overlay(base, genome)
    if system_text and user_text:
        return assembled.rstrip() + "\n\n" + user_text + "\n"
    return assembled.rstrip() + "\n"


def apply_prompt_patches(
    *,
    prompt_patches_path: str | Path,
    out_dir: str | Path,
    base_genome_path: str | Path | None = None,
    rendered_package: dict[str, Any] | None = None,
    write_source_file: bool = False,
) -> dict[str, Any]:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    patches_output = read_json(prompt_patches_path)
    genome = load_base_genome(base_genome_path)
    before = copy.deepcopy(genome)
    applications = [apply_patch_to_genome(genome, patch) for patch in patch_list(patches_output)]
    genome["id"] = str(genome.get("id") or "patched_base") + "_patched"
    prompt_preview = rendered_prompt_with_genome(rendered_package, genome)
    visible = [
        item["patch_id"]
        for item in applications
        if item.get("patch_text") and str(item["patch_text"]) in prompt_preview
    ]
    if write_source_file:
        source_dir = root / "generated_blocks"
        source_dir.mkdir(parents=True, exist_ok=True)
        for item in applications:
            if item.get("patch_text"):
                (source_dir / f"block_{item['target_block_id']}_{item['patch_id']}.md").write_text(str(item["patch_text"]) + "\n", encoding="utf-8")
    diff_lines = ["# Prompt Patch Diff", "", "## Applied Patches"]
    for item in applications:
        diff_lines.append(
            f"- `{item.get('patch_id')}` op={item.get('operation')} block={item.get('target_block_id')} changed={item.get('changed')}"
        )
    diff_lines.extend(["", "## Visibility", f"- visible_patch_count: `{len(visible)}`", ""])
    report = {
        "created_at": utc_now(),
        "prompt_patches_path": str(prompt_patches_path),
        "base_genome_path": str(base_genome_path or "fallback"),
        "patched_genome_path": str(root / "patched_genome.json"),
        "accepted_proposal_count": sum(1 for item in applications if item.get("changed")),
        "advisor_child_scheduled_count": 1 if any(item.get("changed") for item in applications) else 0,
        "advisor_backed_diff_count": len(visible),
        "patch_count": len(applications),
        "visible_patch_ids": visible,
        "patch_visibility_ok": len(visible) >= sum(1 for item in applications if item.get("patch_text")),
        "applications": applications,
        "before_blocks": before.get("blocks", []),
        "after_blocks": genome.get("blocks", []),
    }
    write_json(root / "patched_genome.json", genome)
    write_json(root / "patch_application_report.json", report)
    (root / "patch_diff.md").write_text("\n".join(diff_lines) + "\n", encoding="utf-8")
    (root / "patched_prompt_preview.md").write_text(prompt_preview, encoding="utf-8")
    return {"patched_genome": genome, "report": report, "prompt_preview": prompt_preview}


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply prompt_patches.json to a GA-compatible genome without editing prompt files.")
    parser.add_argument("--prompt-patches", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--base-genome", default="")
    parser.add_argument("--write-source-file", action="store_true")
    args = parser.parse_args()
    result = apply_prompt_patches(
        prompt_patches_path=args.prompt_patches,
        out_dir=args.out_dir,
        base_genome_path=args.base_genome or None,
        rendered_package=None,
        write_source_file=args.write_source_file,
    )
    print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
