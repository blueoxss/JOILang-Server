#!/usr/bin/env python3
"""IV-4 DET 민감도 표 — 고정 출력 재채점 (LLM 호출·모델 로딩 없음).

입력: 데이터셋 CSV, 입력 manifest(모델×방법별 저장 출력 jsonl), 조건 설정(configs/det_sensitivity_table.json).
평가기: 저장소 루트 utils/det_evaluator.py 의 8항 구성 함수(file-path import, 패키지 부작용 없음).
출력(--out): input_provenance.json, evaluation_contract.md, sensitivity_conditions.json, components.jsonl,
             rescored_rows.csv, det_sensitivity_by_model.csv, det_sensitivity_by_category.csv,
             det_sensitivity_summary.csv, pass_flip_analysis.csv, checks.json, manifest.json

    python scripts/rescore_det_sensitivity_table.py \
        --inputs configs/det_sensitivity_inputs_20260827_reproduction.json \
        --config configs/det_sensitivity_table.json --dataset datasets/JOICommands-280.csv \
        --out results/det_sensitivity_table/<run_id>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
EVALUATOR_PATH = REPO_ROOT / "utils" / "det_evaluator.py"
HARD_GATES = ("invalid_json", "missing_official_gt", "missing_generated_code")


def load_evaluator(path: Path = EVALUATOR_PATH):
    spec = importlib.util.spec_from_file_location("root_det_evaluator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_row_uid(category: str, command_eng: str, gt: str) -> str:
    payload = json.dumps([category, command_eng, gt], ensure_ascii=False, separators=(",", ":"))
    return sha256_bytes(payload.encode("utf-8"))[:24]


def legacy_row_uid(category: str, command: str, reference: str) -> str:
    """재현 실행 기록이 쓴 식별자: SHA256(category || 공백정규화 명령 || 공백정규화 참조)[:24]."""
    norm_cmd = " ".join(str(command).split())
    norm_ref = " ".join(str(reference).split())
    return sha256_bytes(f"{category}||{norm_cmd}||{norm_ref}".encode("utf-8"))[:24]


# ---------------------------------------------------------------- 파서 (원본 ga_multimodel_sweep.parse_candidate 그대로)
def _extract_first_json_block(text: str) -> str:
    if not isinstance(text, str):
        return ""
    s = text.strip()
    if s.startswith("```json"):
        s = s[len("```json"):].strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    elif s.startswith("```"):
        s = s[3:].strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    start = s.find("{")
    if start == -1:
        return s
    depth = 0; in_str = False; esc = False
    for i in range(start, len(s)):
        c = s[i]
        if esc:
            esc = False; continue
        if c == "\\":
            esc = True; continue
        if c == '"':
            in_str = not in_str; continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start:i + 1].strip()
    return s[start:].strip()


def parse_candidate(text: str) -> dict[str, Any]:
    block = _extract_first_json_block(text)
    if not block:
        return {}
    try:
        obj = json.loads(block, strict=False)
    except json.JSONDecodeError:
        return {}
    if isinstance(obj, list):
        obj = obj[0] if obj else {}
    if not isinstance(obj, dict):
        return {}
    if "code" not in obj and "script" in obj:
        obj["code"] = obj.pop("script")
    if isinstance(obj.get("period"), str):
        try:
            obj["period"] = int(obj["period"].strip())
        except (TypeError, ValueError):
            pass
    return obj


# ---------------------------------------------------------------- 8항 성분 (utils/det_evaluator.py 의 계산식 그대로)
def compute_components(ev, gt_json: dict[str, Any], generated_json: dict[str, Any]) -> tuple[list[float], list[str]]:
    reasons: list[str] = []
    reference_code = ev.gt_code(gt_json)
    generated_code = str(generated_json.get("code") or "")
    if not reference_code:
        reasons.append("missing_gt_code")
    if not generated_code:
        reasons.append("missing_generated_code")
    cron_match = ev.compare_bool(gt_json.get("cron", ""), generated_json.get("cron", ""))
    period_match = ev.compare_bool(gt_json.get("period", ""), generated_json.get("period", ""))
    code_sim = ev.similarity(reference_code, generated_code) if reference_code and generated_code else 0.0
    ref_services = ev.extract_services(reference_code)
    gen_services = ev.extract_services(generated_code)
    components = [
        code_sim,
        1.0 if cron_match and period_match else (0.5 if cron_match or period_match else 0.0),
        ev.coverage_score(ref_services, gen_services),
        ev.precision_score(ref_services, gen_services),
        ev.coverage_score(ev.extract_receivers(reference_code), ev.extract_receivers(generated_code)),
        ev.coverage_score(ev.extract_numeric_literals(reference_code), ev.extract_numeric_literals(generated_code)),
        ev.coverage_score(ev.extract_string_args(reference_code), ev.extract_string_args(generated_code)),
        ev.dataflow_heuristic_score(reference_code, generated_code),
    ]
    return components, reasons


def score_record(ev, gt_text: str, output_text: str) -> dict[str, Any]:
    """저장 출력 하나의 파싱 상태, v, 8항 성분. 파싱 실패면 성분은 모두 0, v=0."""
    gt_json = ev.parse_json_object(gt_text, label="gt")
    candidate = parse_candidate(output_text)
    if not candidate:
        return {"parse_ok": False, "v": 0, "components": [0.0] * 8, "reasons": ["invalid_json"],
                "candidate": None}
    generated_json = ev.normalize_candidate(candidate)
    components, reasons = compute_components(ev, gt_json, generated_json)
    v = 0 if any(r in reasons for r in HARD_GATES) else 1
    return {"parse_ok": True, "v": v, "components": components, "reasons": reasons, "candidate": generated_json}


def weighted(components: list[float], weights: list[float]) -> float:
    return sum(w * s for w, s in zip(weights, components))


def validate_weights(profiles: dict[str, list[float]]) -> None:
    for name, w in profiles.items():
        if len(w) != 8 or any((not isinstance(x, (int, float))) or x != x or x < 0 or x == float("inf") for x in w):
            raise ValueError(f"weight profile {name} must be 8 finite non-negative numbers")
        if abs(sum(w) - 1.0) > 1e-9:
            raise ValueError(f"weight profile {name} sums to {sum(w)!r}, not 1")


# ---------------------------------------------------------------- 메인
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--config", default=str(REPO_ROOT / "configs/det_sensitivity_table.json"))
    ap.add_argument("--dataset", default=str(REPO_ROOT / "datasets/JOICommands-280.csv"))
    ap.add_argument("--evaluator", default=str(EVALUATOR_PATH))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    inputs = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
    validate_weights(config["weight_profiles"])
    ev = load_evaluator(Path(args.evaluator))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)

    with Path(args.dataset).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 280:
        raise SystemExit(f"dataset rows {len(rows)} != 280")
    by_legacy: dict[str, tuple[int, dict[str, str]]] = {}
    by_canonical: dict[str, tuple[int, dict[str, str]]] = {}
    for row_no, row in enumerate(rows, start=1):
        by_legacy[legacy_row_uid(row["category"], row["command_eng"], row["gt"])] = (row_no, row)
        by_canonical[canonical_row_uid(row["category"], row["command_eng"], row["gt"])] = (row_no, row)
    if len(by_legacy) != 280 or len(by_canonical) != 280:
        raise SystemExit("row uid collision in dataset")

    conditions = config["conditions"]
    comp_keys = config["component_keys"]
    checks: dict[str, Any] = {"sets": {}, "stored_component_mismatches": 0, "stored_e_mismatch_rows": 0,
                              "parse_failures": 0, "monotonicity_ok": True, "sdet_inequality_ok": True}
    components_records: list[dict[str, Any]] = []
    rescored: list[dict[str, Any]] = []
    set_meta: list[dict[str, Any]] = []

    for spec in inputs["sets"]:
        records = [json.loads(l) for l in Path(spec["records"]).read_text(encoding="utf-8").splitlines() if l.strip()]
        records = [r for r in records if r["model"] == spec["model"] and r["method"] == spec["method"]]
        uids = [r["row_uid"] for r in records]
        if len(uids) != 280 or len(set(uids)) != 280 or any(u not in by_legacy for u in uids):
            raise SystemExit(f"{spec['model']}/{spec['method']}: 280 complete rows required (got {len(uids)}, unique {len(set(uids))})")
        n_err = sum(1 for r in records if r.get("status") != "ok" or r.get("generation_error"))
        base_w = config["weight_profiles"]["base"]
        stored_mismatch = e_mismatch = parse_fail = 0
        for rec in records:
            row_no, row = by_legacy[rec["row_uid"]]
            scored = score_record(ev, row["gt"], rec["output_text"])
            if not scored["parse_ok"]:
                parse_fail += 1
            stored = rec.get("components") or {}
            stored_vec = [stored.get(k) for k in ("code_sim", "schedule", "service_coverage", "service_precision",
                                                   "receiver_coverage", "numeric_grounding", "enum_grounding", "dataflow")]
            if scored["parse_ok"] and any(s is None or abs(float(s) - c) > 1e-9 for s, c in zip(stored_vec, scored["components"])):
                stored_mismatch += 1
            e_base = weighted(scored["components"], base_w) if scored["parse_ok"] else 0.0
            if abs(float(rec.get("e", 0.0)) - e_base) > 1e-9:
                e_mismatch += 1
            canonical = canonical_row_uid(row["category"], row["command_eng"], row["gt"])
            components_records.append({
                "row_uid": canonical, "legacy_row_uid": rec["row_uid"], "row_no": row_no,
                "category": row["category"], "index": row["index"], "model": spec["model"], "method": spec["method"],
                "role": spec["role"], "run_id": spec["run_id"], "repeat_id": rec.get("repeat_id", 0), "seed": rec.get("seed", 0),
                "prompt_sha256": rec.get("prompt_sha256", ""), "genome_id": rec.get("genome_id", ""), "genome_hash": rec.get("genome_hash", ""),
                "reference_sha256": sha256_bytes(row["gt"].encode("utf-8")),
                "output_sha256": sha256_bytes(str(rec["output_text"]).encode("utf-8")),
                "generation_status": rec.get("status", ""), "generation_error": rec.get("generation_error", ""),
                "parse_ok": scored["parse_ok"], "v": scored["v"], "reasons": scored["reasons"],
                "candidate": scored["candidate"],
                "components": dict(zip(comp_keys, scored["components"])),
                "stored_components_match": (not scored["parse_ok"]) or all(
                    s is not None and abs(float(s) - c) <= 1e-9 for s, c in zip(stored_vec, scored["components"])),
                "stored_e": rec.get("e"), "recomputed_e_base": e_base,
            })
            e_by_cond = {}
            for cond in conditions:
                w = config["weight_profiles"][cond["weights"]]
                e_c = weighted(scored["components"], w) if scored["parse_ok"] else 0.0
                e_by_cond[cond["id"]] = e_c
                rescored.append({"condition_id": cond["id"], "row_uid": canonical, "row_no": row_no, "category": row["category"],
                                 "model": spec["model"], "method": spec["method"], "role": spec["role"],
                                 "v": scored["v"], "e": e_c, "tau": cond["tau"], "D": int(scored["v"] == 1 and e_c >= cond["tau"])})
        checks["sets"][f"{spec['model']}/{spec['method']}"] = {
            "rows": len(records), "generation_errors_recorded": n_err, "parse_failures": parse_fail,
            "stored_component_mismatches": stored_mismatch, "stored_e_mismatch_rows": e_mismatch,
            "records_sha256": sha256_file(spec["records"])}
        checks["stored_component_mismatches"] += stored_mismatch
        checks["stored_e_mismatch_rows"] += e_mismatch
        checks["parse_failures"] += parse_fail
        set_meta.append({k: spec[k] for k in spec if k != "records"} | {"records_path": spec["records"], "records_sha256": sha256_file(spec["records"])})

    # ---- 집계
    by_model_rows: list[dict[str, Any]] = []
    by_cat_rows: list[dict[str, Any]] = []
    flips: list[dict[str, Any]] = []
    pass_sets: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    e_sum: dict[tuple[str, str, str], float] = defaultdict(float)
    cat_pass: dict[tuple[str, str, str, str], int] = Counter()
    cat_n: dict[tuple[str, str, str], int] = Counter()
    for r in rescored:
        key = (r["condition_id"], r["model"], r["method"])
        if r["D"]:
            pass_sets[key].add(r["row_uid"])
        e_sum[key] += r["e"]
        cat_n[(r["model"], r["method"], r["category"])] += 1 if r["condition_id"] == "base_t090" else 0
        if r["D"]:
            cat_pass[(r["condition_id"], r["model"], r["method"], r["category"])] += 1
    roles = {(s["model"], s["method"]): s["role"] for s in inputs["sets"]}
    for cond in conditions:
        for (model, method), role in roles.items():
            key = (cond["id"], model, method)
            passed = len(pass_sets[key])
            base_key = ("base_t090", model, method)
            gained = len(pass_sets[key] - pass_sets[base_key]); lost = len(pass_sets[base_key] - pass_sets[key])
            by_model_rows.append({"condition_id": cond["id"], "model": model, "method": method, "role": role,
                                  "passed": passed, "denominator": 280, "detpass_pct": 100.0 * passed / 280,
                                  "sdet": e_sum[key] / 280, "runs": 1})
            flips.append({"condition_id": cond["id"], "model": model, "method": method, "role": role,
                          "fail_to_pass_vs_base": gained, "pass_to_fail_vs_base": lost, "net": passed - len(pass_sets[base_key])})
            for cat in sorted({r["category"] for r in rows}, key=int):
                n = cat_n[(model, method, cat)]
                by_cat_rows.append({"condition_id": cond["id"], "model": model, "method": method, "role": role, "category": cat,
                                    "passed": cat_pass[(cond["id"], model, method, cat)], "denominator": n,
                                    "detpass_pct": 100.0 * cat_pass[(cond["id"], model, method, cat)] / n if n else ""})
            sdet = e_sum[key] / 280
            if sdet + 1e-12 < cond["tau"] * passed / 280:
                checks["sdet_inequality_ok"] = False
    # 단조성: Pass(.95) ⊆ Pass(.90) ⊆ Pass(.85)
    for (model, method) in roles:
        p85, p90, p95 = (pass_sets[(c, model, method)] for c in ("base_t085", "base_t090", "base_t095"))
        if not (p95 <= p90 <= p85):
            checks["monotonicity_ok"] = False

    # ---- 대상 모델 평균 (논문 표: paper_dt / paper_gps 역할만; 3모델 미완이면 N/A)
    models = sorted({s["model"] for s in inputs["sets"]})
    summary_rows: list[dict[str, Any]] = []
    for cond in conditions:
        row: dict[str, Any] = {"condition_id": cond["id"], "row_label": cond["row_label"], "group": cond["group"],
                               "tau": cond["tau"], "weights": cond["weights"]}
        for method, role_name in (("dt", "paper_dt"), ("gps", "paper_gps")):
            vals = [r["detpass_pct"] for r in by_model_rows if r["condition_id"] == cond["id"] and r["method"] == method and r["role"] == role_name]
            counts = [r["passed"] for r in by_model_rows if r["condition_id"] == cond["id"] and r["method"] == method and r["role"] == role_name]
            complete = len(vals) == len(models) == 3
            row[f"{method}_models_available"] = len(vals)
            row[f"{method}_avg_pct"] = sum(vals) / 3 if complete else ""
            row[f"{method}_passed_total"] = sum(counts) if complete else ""
            row[f"{method}_status"] = "computed" if complete else f"N/A (paper-table outputs for {len(vals)}/3 models)"
        if row["dt_avg_pct"] != "" and row["gps_avg_pct"] != "":
            row["diff_pp"] = row["gps_avg_pct"] - row["dt_avg_pct"]
        else:
            row["diff_pp"] = ""
        # 진단: 교차 적용 GPS 포함 평균(별도 분석)
        diag = [r["detpass_pct"] for r in by_model_rows if r["condition_id"] == cond["id"] and r["method"] == "gps"]
        row["diagnostic_gps_avg_pct_incl_cross_applied"] = sum(diag) / len(diag) if len(diag) == 3 else ""
        row["diagnostic_diff_pp_incl_cross_applied"] = (row["diagnostic_gps_avg_pct_incl_cross_applied"] - row["dt_avg_pct"]
                                                        if row["dt_avg_pct"] != "" and row["diagnostic_gps_avg_pct_incl_cross_applied"] != "" else "")
        summary_rows.append(row)

    # ---- 저장
    def write_csv(path: Path, rows_: list[dict[str, Any]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows_[0].keys())); w.writeheader(); w.writerows(rows_)

    with (out / "components.jsonl").open("w", encoding="utf-8") as f:
        for rec in components_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    base_pass = {(r["row_uid"], r["model"], r["method"]): r["D"] for r in rescored if r["condition_id"] == "base_t090"}
    for r in rescored:
        b = base_pass[(r["row_uid"], r["model"], r["method"])]
        r["flip_vs_base"] = "none" if b == r["D"] else ("fail_to_pass" if r["D"] else "pass_to_fail")
    write_csv(out / "rescored_rows.csv", rescored)
    write_csv(out / "det_sensitivity_by_model.csv", by_model_rows)
    write_csv(out / "det_sensitivity_by_category.csv", by_cat_rows)
    write_csv(out / "det_sensitivity_summary.csv", summary_rows)
    write_csv(out / "pass_flip_analysis.csv", flips)
    (out / "sensitivity_conditions.json").write_text(json.dumps(config, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1), encoding="utf-8")

    git = lambda *a: subprocess.run(["git", "-C", str(REPO_ROOT), *a], capture_output=True, text=True).stdout.strip()
    provenance = {
        "inputs_manifest": args.inputs, "inputs_manifest_sha256": sha256_file(args.inputs),
        "dataset": args.dataset, "dataset_sha256": sha256_file(args.dataset), "dataset_rows": 280,
        "evaluator": str(Path(args.evaluator)), "evaluator_sha256": sha256_file(args.evaluator),
        "config": args.config, "config_sha256": sha256_file(args.config),
        "candidate_parser": inputs.get("candidate_parser", ""), "generation": inputs.get("generation", {}),
        "sets": set_meta, "missing_for_paper_table": inputs.get("missing_for_paper_table", []),
        "row_uid_rule": config["row_uid"], "legacy_row_uid_rule": "SHA256(category||norm command||norm gt)[:24] (재현 실행 기록의 키)",
    }
    (out / "input_provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=1), encoding="utf-8")
    manifest = {
        "started": started, "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "git_head": git("rev-parse", "HEAD"), "git_branch": git("branch", "--show-current"),
        "git_dirty": bool(git("status", "--short")),
        "python": sys.version.split()[0], "platform": platform.platform(),
        "command": " ".join(sys.argv), "records_per_condition": len(rescored) // len(conditions),
        "aggregation": config["rules"], "llm_calls": 0,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "evaluation_contract.md").write_text(EVALUATION_CONTRACT, encoding="utf-8")
    print(json.dumps({"out": str(out), "checks": {k: v for k, v in checks.items() if k != "sets"},
                      "summary": [{k: r[k] for k in ("condition_id", "dt_avg_pct", "gps_avg_pct", "diff_pp", "gps_status")} for r in summary_rows]},
                     ensure_ascii=False, indent=1))
    return 0


EVALUATION_CONTRACT = """# 재채점 평가 계약 (8항 DET)

- 구현: 저장소 루트 `utils/det_evaluator.py` 의 구성 함수(similarity, extract_services, extract_receivers,
  extract_numeric_literals, extract_string_args, coverage_score, precision_score, dataflow_heuristic_score,
  compare_bool, normalize_candidate, parse_json_object). 점수 계산식은 `strict_det_evaluate_row` 와 같다.
- s1: `difflib.SequenceMatcher(None, u_r, u_y).ratio()` (기본 설정, autojunk 기본값, 인자 순서 기준→생성).
  원문 코드 중 하나라도 빈 문자열이면 0. 두 원문이 비어 있지 않고 공백 제거 후 모두 비면 ratio()=1.
- s2: cron, period 각각 `str(value or "")` 에서 공백 제거 후 일치 여부의 평균(None·""·0 → ""). 생성 JSON 의 period
  기본값은 0(원본 normalize_candidate), cron 기본값 "".
- S: `\\([^)]*\\)\\.([A-Za-z_][A-Za-z0-9_]*)` 의 member 목록. T: `\\(([^)]*)\\)\\.` 괄호 내부 공백 제거 목록.
  N: `(?<![A-Za-z_])-?\\d+(?:\\.\\d+)?` 문자열 그대로(23 ≠ 23.0). L: `['"]([^'"]+)['"]` 내부 공백 제거·소문자.
- c(A,B)=Σmin/|A| (A 비면 1), p(A,B)=Σmin/|B| (B 비면: A 비면 1, 아니면 0). 중복 출현 반영(Counter).
- s8: `\\b(?:var|let|const)\\s+[A-Za-z_][A-Za-z0-9_]*\\s*=` 선언 수; 기준 0 → 1, 아니면 min(1, 생성/기준).
- 파싱: 저장 출력에서 첫 JSON 객체 추출 + json.loads(strict=False) (원본 파이프라인 parse_candidate). 실패 시 e=0, v=0.
  파싱 성공 후 code 가 비면 v=0, 나머지 비교값은 유지.
- e = Σ w_k s_k 를 반올림 없이 계산, D = 1[v=1 ∧ e ≥ τ] (epsilon 없음).
- Python: 이 실행의 manifest.json 참조. 가중치 재정규화 없음.
"""

if __name__ == "__main__":
    raise SystemExit(main())
