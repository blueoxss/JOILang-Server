#!/usr/bin/env python3
"""paper_v1 DET evaluator — 논문 IV-4 식 (3)–(6)의 구현.

의미론적 기준: JOILang-Server ROOT utils/det_evaluator.py(@463f092d)의 8항
구성요소 채점을 그대로 이식(0-1 스케일)한 것으로, v15 strict 프로파일의
재라벨이 **아니다** (strict는 12항·gt_exact override·min(score,0.699) cap을
갖는 별개 평가기이며 무변경 공존). 논문 worked example(외부온도 간결형
e=0.9264397905759162)은 이 모듈로 재현된다.

식 (3): e_i = Σ_k w_k·s_ik,  w0=(0.30,0.15,0.15,0.10,0.10,0.10,0.05,0.05)
식 (4): D_i = 1 iff (치명 오류 없음 ∧ e_i ≥ τ), τ=0.70
치명 오류(hard gate): invalid_json, missing_official_gt, missing_generated_code → e=0.0, D=0

참조 의미론: row에 gt_refs 리스트가 있으면 참조별 채점 후 최댓값(main.tex의
'허용 참조' max), 없으면 단일 gt — 단일 gt에서는 두 정의가 동치(교수님 PDF의
단일 기준 코드 r_i와 정합). JOICommands-280은 단일 gt 열만 갖는다.

가중치는 configs/det_weights/paper_v1.json에서 로드(탐색 전에 정한 설계값,
예비 실험으로 학습한 값 아님, 모든 모델 동일 적용).
"""
from __future__ import annotations

import difflib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

VERSION_DIR = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS_PATH = VERSION_DIR / "configs" / "det_weights" / "paper_v1.json"

# 논문 식(3) w0 — config 부재 시에도 동일값 (설계값 이중 기록)
PAPER_V1_WEIGHTS = {
    "code_sim": 0.30,
    "schedule": 0.15,
    "service_coverage": 0.15,
    "service_precision": 0.10,
    "receiver_coverage": 0.10,
    "numeric_grounding": 0.10,
    "enum_grounding": 0.05,
    "dataflow": 0.05,
}
COMPONENT_KEYS = tuple(PAPER_V1_WEIGHTS)
DEFAULT_THRESHOLD = 0.70
HARD_GATE_REASONS = ("invalid_json", "missing_official_gt", "missing_generated_code")

# ---- ROOT utils/det_evaluator.py에서 이식한 추출·채점 프리미티브 (동작 동일) ----

SERVICE_CALL_RE = re.compile(r"\([^)]*\)\.([A-Za-z_][A-Za-z0-9_]*)")
RECEIVER_RE = re.compile(r"\(([^)]*)\)\.")
NUMERIC_RE = re.compile(r"(?<![A-Za-z_])-?\d+(?:\.\d+)?")
STRING_ARG_RE = re.compile(r"['\"]([^'\"]+)['\"]")


def parse_json_object(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, list):
        if not value:
            raise ValueError(f"{label} is an empty list")
        value = value[0]
    if isinstance(value, dict):
        return value
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is empty")
    parsed = json.loads(text)
    if isinstance(parsed, list):
        if not parsed:
            raise ValueError(f"{label} is an empty JSON list")
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed


def normalize_candidate(candidate: Any) -> dict[str, Any]:
    parsed = parse_json_object(candidate, label="generated candidate")
    return {
        "name": str(parsed.get("name", "")),
        "cron": str(parsed.get("cron", "")),
        "period": parsed.get("period", 0),
        "code": str(parsed.get("code") or parsed.get("script") or ""),
    }


def gt_code(gt_json: dict[str, Any]) -> str:
    return str(gt_json.get("code") or gt_json.get("script") or "")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def similarity(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def extract_services(code: str) -> list[str]:
    return SERVICE_CALL_RE.findall(str(code or ""))


def extract_receivers(code: str) -> list[str]:
    return [normalize_text(item) for item in RECEIVER_RE.findall(str(code or ""))]


def extract_numeric_literals(code: str) -> list[str]:
    return NUMERIC_RE.findall(str(code or ""))


def extract_string_args(code: str) -> list[str]:
    return [normalize_text(item).lower() for item in STRING_ARG_RE.findall(str(code or ""))]


def coverage_score(reference_items: list[str], generated_items: list[str]) -> float:
    if not reference_items:
        return 1.0
    ref_counter = Counter(reference_items)
    gen_counter = Counter(generated_items)
    covered = sum(min(count, gen_counter.get(item, 0)) for item, count in ref_counter.items())
    return covered / sum(ref_counter.values())


def precision_score(reference_items: list[str], generated_items: list[str]) -> float:
    if not generated_items:
        return 1.0 if not reference_items else 0.0
    ref_counter = Counter(reference_items)
    gen_counter = Counter(generated_items)
    matched = sum(min(count, ref_counter.get(item, 0)) for item, count in gen_counter.items())
    return matched / sum(gen_counter.values())


def dataflow_heuristic_score(reference_code: str, generated_code: str) -> float:
    ref_assignments = len(re.findall(r"\b(?:var|let|const)\s+[A-Za-z_][A-Za-z0-9_]*\s*=", reference_code or ""))
    gen_assignments = len(re.findall(r"\b(?:var|let|const)\s+[A-Za-z_][A-Za-z0-9_]*\s*=", generated_code or ""))
    if ref_assignments == 0:
        return 1.0
    if gen_assignments >= ref_assignments:
        return 1.0
    return gen_assignments / ref_assignments


def compare_bool(left: Any, right: Any) -> bool:
    return normalize_text(left) == normalize_text(right)


# ---- 가중치 로딩 ----

def load_det_weights(path: str | Path | None = None) -> tuple[dict[str, float], float, str]:
    """(weights, threshold, profile_name) 로드. 합=1 검증, 미지 키 거부."""
    weights_path = Path(path) if path else DEFAULT_WEIGHTS_PATH
    data = json.loads(weights_path.read_text(encoding="utf-8"))
    weights = {key: float(value) for key, value in dict(data["weights"]).items()}
    unknown = set(weights) - set(COMPONENT_KEYS)
    if unknown:
        raise ValueError(f"unknown DET weight keys {sorted(unknown)}; expected subset of {list(COMPONENT_KEYS)}")
    missing = set(COMPONENT_KEYS) - set(weights)
    if missing:
        raise ValueError(f"missing DET weight keys {sorted(missing)}")
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"DET weights must sum to 1.0 (got {total!r})")
    threshold = float(data.get("threshold", DEFAULT_THRESHOLD))
    return weights, threshold, str(data.get("profile", weights_path.stem))


# ---- 채점 ----

def score_from_components(components: dict[str, float], weights: dict[str, float] | None = None) -> float:
    """성분 벡터 → e_i (식 3). R4 가중치 민감도 재채점의 공용 진입점 (LLM 호출 없음)."""
    w = weights or PAPER_V1_WEIGHTS
    return sum(w[key] * float(components[key]) for key in COMPONENT_KEYS)


def _score_against_reference(gt_json: dict[str, Any], generated_json: dict[str, Any]) -> tuple[dict[str, float], list[str], bool]:
    """단일 참조에 대한 8성분 채점 (ROOT strict_det_evaluate_row와 동작 동일, 0-1)."""
    failure_reasons: list[str] = []
    reference_code = gt_code(gt_json)
    generated_code = str(generated_json.get("code") or "")
    if not reference_code:
        failure_reasons.append("missing_gt_code")
    if not generated_code:
        failure_reasons.append("missing_generated_code")

    cron_match = compare_bool(gt_json.get("cron", ""), generated_json.get("cron", ""))
    period_match = compare_bool(gt_json.get("period", ""), generated_json.get("period", ""))
    if not cron_match:
        failure_reasons.append("cron_mismatch")
    if not period_match:
        failure_reasons.append("period_mismatch")

    code_sim = similarity(reference_code, generated_code) if reference_code and generated_code else 0.0
    code_match = code_sim >= 0.995
    gt_exact = cron_match and period_match and code_match
    if not code_match:
        failure_reasons.append("gt_mismatch")

    ref_service_list = extract_services(reference_code)
    gen_service_list = extract_services(generated_code)
    service_coverage = coverage_score(ref_service_list, gen_service_list)
    service_precision = precision_score(ref_service_list, gen_service_list)
    if ref_service_list and service_coverage < 0.999:
        failure_reasons.append("gt_service_coverage")
    if gen_service_list and service_precision < 0.999:
        failure_reasons.append("unknown_service")

    receiver_coverage = coverage_score(extract_receivers(reference_code), extract_receivers(generated_code))
    if receiver_coverage < 0.999:
        failure_reasons.append("gt_receiver_coverage")

    numeric_grounding = coverage_score(
        extract_numeric_literals(reference_code), extract_numeric_literals(generated_code))
    if numeric_grounding < 0.999:
        failure_reasons.append("numeric_grounding")
    enum_grounding = coverage_score(extract_string_args(reference_code), extract_string_args(generated_code))
    if enum_grounding < 0.999:
        failure_reasons.append("enum_grounding")
    dataflow = dataflow_heuristic_score(reference_code, generated_code)
    if dataflow < 0.999:
        failure_reasons.append("dataflow")

    schedule = 1.0 if cron_match and period_match else (0.5 if cron_match or period_match else 0.0)
    components = {
        "code_sim": code_sim,
        "schedule": schedule,
        "service_coverage": service_coverage,
        "service_precision": service_precision,
        "receiver_coverage": receiver_coverage,
        "numeric_grounding": numeric_grounding,
        "enum_grounding": enum_grounding,
        "dataflow": dataflow,
    }
    return components, failure_reasons, gt_exact


def evaluate_row_paper_v1(
    row: dict[str, Any],
    candidate: Any,
    *,
    weights: dict[str, float] | None = None,
    threshold: float = DEFAULT_THRESHOLD,
    row_no: int | str = "",
) -> dict[str, Any]:
    """행 하나를 paper_v1으로 채점. 반환값은 성분 벡터·메타데이터를 보존(G10)."""
    w = dict(weights or PAPER_V1_WEIGHTS)
    failure_reasons: list[str] = []

    # 참조 수집: gt_refs 리스트 우선, 없으면 단일 gt
    raw_refs = row.get("gt_refs")
    if raw_refs is None:
        raw_refs = [row.get("gt")] if str(row.get("gt") or "").strip() else []
    ref_jsons: list[dict[str, Any]] = []
    for ref in raw_refs:
        try:
            ref_jsons.append(parse_json_object(ref, label="gt reference"))
        except Exception:
            failure_reasons.append("unparseable_reference")
    if not ref_jsons:
        failure_reasons.append("missing_official_gt")

    generated_json: dict[str, Any] = {}
    try:
        generated_json = normalize_candidate(candidate)
    except Exception as exc:
        failure_reasons.append("invalid_json")
        generated_json = {"_error": str(exc), "name": "", "cron": "", "period": "", "code": ""}

    best: dict[str, Any] | None = None
    for ref_index, gt_json in enumerate(ref_jsons):
        components, ref_reasons, gt_exact = _score_against_reference(gt_json, generated_json)
        e = score_from_components(components, w)
        if best is None or e > best["e"]:
            best = {"e": e, "components": components, "reasons": ref_reasons,
                    "gt_exact": gt_exact, "ref_index": ref_index, "gt_json": gt_json}

    if best is None:  # 참조 전무 → hard gate
        best = {"e": 0.0, "components": {key: 0.0 for key in COMPONENT_KEYS},
                "reasons": [], "gt_exact": False, "ref_index": -1, "gt_json": {}}
    failure_reasons.extend(best["reasons"])

    fatal = [reason for reason in HARD_GATE_REASONS if reason in failure_reasons]
    e = 0.0 if fatal else float(best["e"])
    det_pass = (not fatal) and e >= float(threshold)

    unique_reasons: list[str] = []
    for reason in failure_reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)
    return {
        "row_no": row_no,
        "category": row.get("category", ""),
        "det_profile": "paper_v1",
        # e·components는 반올림 없이 원 정밀도 보존 — 반올림하면 det_pass(내부 원값 비교)와
        # 출력값이 임계 경계에서 어긋나고, R4 재가중 재채점에도 오차가 유입된다.
        "e": float(e),
        "det_score": round(100.0 * e, 4),  # 기존 파이프라인(0-100) 호환 표시 필드
        "det_pass": bool(det_pass),
        "gt_exact": bool(best["gt_exact"]),
        "components": {key: float(best["components"][key]) for key in COMPONENT_KEYS},
        "weights": w,
        "threshold": float(threshold),
        "hard_gate": fatal,
        "failure_reasons": unique_reasons,
        "n_refs": len(ref_jsons),
        "selected_ref_index": best["ref_index"],
        "gt_code": gt_code(best["gt_json"]),
        "generated_code": str(generated_json.get("code") or ""),
    }
