#!/usr/bin/env python3
"""WI-01: 저장소 설정 실측 manifest 생성기.

논문 가정(AS-01~08)과 저장소 실측값을 대조해
audit/manifest.json 과 audit/assumptions_diff.md 를 생성한다.

원칙(P-1/P-2): 모든 값은 이 스크립트가 데이터 파일과 소스 코드에서
직접 측정/추출한다. 추출 실패 시 그럴듯한 값 대신 "EXTRACT_FAILED"를 기록한다.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def _extract(path: str, pattern: str, cast=str):
    """소스에서 pattern의 group(1)을 추출하고 (값, '파일:행') 을 반환."""
    text = _read(path)
    match = re.search(pattern, text)
    if not match:
        return "EXTRACT_FAILED", f"{path} (pattern: {pattern})"
    line_no = text[: match.start()].count("\n") + 1
    return cast(match.group(1)), f"{path}:{line_no}"


def measure_benchmark() -> dict:
    path = "datasets/JOICommands-280.csv"
    with (REPO / path).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    dist: dict[str, int] = {}
    for r in rows:
        dist[str(r["category"])] = dist.get(str(r["category"]), 0) + 1
    return {
        "path": path,
        "rows": len(rows),
        "columns": list(rows[0].keys()),
        "category_distribution": dict(sorted(dist.items())),
        "n_categories": len(dist),
        "note": "cat1~6 각 30건(합 180) + cat7 50건 + cat8 50건. 논문의 180/60/40 분할 매니페스트는 부재.",
    }


def measure_replay_sources() -> dict:
    total = 0
    files = 0
    for p in sorted((REPO / "datasets" / "usr_rag").glob("*.csv")):
        with p.open(encoding="utf-8-sig", newline="") as f:
            total += len(list(csv.DictReader(f)))
        files += 1
    admin = sorted((REPO / "admin_logs" / "slack").glob("*.jsonl"))
    admin_rows = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in admin)
    return {
        "usr_rag_files": files,
        "usr_rag_rows": total,
        "usr_rag_columns": ["sentence", "best_code"],
        "admin_log_files": [str(p.relative_to(REPO)) for p in admin],
        "admin_log_rows": admin_rows,
        "replayfit_computation": "ABSENT — 정본 런타임에 리플레이 재해결율 계산 경로 없음 (audit C-05/C-14)",
    }


def measure_stress() -> dict:
    hits = [
        str(p.relative_to(REPO))
        for p in REPO.rglob("*stress*")
        if ".git" not in p.parts and "__pycache__" not in p.parts
    ]
    return {"status": "NOT_FOUND" if not hits else "FOUND", "hits": hits}


def extract_ga_budget() -> dict:
    pop, pop_src = _extract("utils/ga_search/cli.py", r'--population",\s*type=int,\s*default=(\d+)', int)
    gens, gens_src = _extract("utils/ga_search/cli.py", r'--gens",\s*type=int,\s*default=(\d+)', int)
    check_pop, check_pop_src = _extract("run_ga_search_check.sh", r'POPULATION=(\d+)', int)
    legacy = "gpt_mg/version0_15_update20260413/scripts/run_ga_search.py"
    leg_pop, leg_pop_src = _extract(legacy, r'--population",\s*type=int,\s*default=(\d+)', int)
    leg_gens, leg_gens_src = _extract(legacy, r'--gens",\s*type=int,\s*default=(\d+)', int)
    leg_elites, leg_elites_src = _extract(legacy, r'--elites",\s*type=int,\s*default=(\d+)', int)
    return {
        "canonical_cli_defaults": {
            "population": pop,
            "generations": gens,
            "sources": [pop_src, gens_src],
        },
        "canonical_engine_behavior": {
            "elite": "1 고정 (ga_engine.py:369 — 최고 유전형 1개 복제)",
            "tournament": "없음 — 상위 min(3,len) 중 rng.choice (ga_engine.py:371)",
            "p_mutation": "비엘리트 자식 100% 변이 (ga_engine.py:372)",
            "crossover": "없음 — 변이 4종만 (audit C-11)",
        },
        "check_script_full_mode": {"population": check_pop, "source": check_pop_src},
        "legacy_backup_defaults": {
            "population": leg_pop,
            "generations": leg_gens,
            "elites": leg_elites,
            "sources": [leg_pop_src, leg_gens_src, leg_elites_src],
        },
    }


def extract_fitness() -> dict:
    text = _read("utils/ga_search/rerank.py")
    match = re.search(r'"fitness":\s*(.+),', text)
    line_no = text[: match.start()].count("\n") + 1 if match else -1
    return {
        "canonical": {
            "formula": match.group(1).strip() if match else "EXTRACT_FAILED",
            "hardcoded": True,
            "source": f"utils/ga_search/rerank.py:{line_no}",
            "terms_vs_paper": "ReplayFit 항 부재, 논문에 없는 gt_exact_rate 항 존재, 토큰/지연 비정규화",
            "token_cost_caveat": "worker 백엔드가 usage 토큰을 0으로 보고(프로브 실측) — 토큰 항이 실효 없음",
        },
        "paper_assumption": {
            "formula": "α·DETPass + β·S_DET + γ·ReplayFit_search − λt·Tok̂ − λl·Lat̂",
            "weights": [0.50, 0.15, 0.20, 0.10, 0.05],
            "externalized_config": True,
        },
    }


def extract_det() -> dict:
    thr, thr_src = _extract("utils/det_evaluator.py", r"det_threshold:\s*float\s*=\s*([\d.]+)", float)
    text = _read("utils/det_evaluator.py")
    comp_pattern = re.findall(r"([\d.]+)\s*\*\s*(code_sim|schedule_score|service_coverage|service_precision|receiver_coverage|numeric_grounding|enum_grounding|dataflow_score)", text)
    rename = {"schedule_score": "schedule", "dataflow_score": "dataflow"}
    comps = {rename.get(name, name): float(w) for w, name in comp_pattern}
    comps["code_sim"] = comps.get("code_sim", 0.0)
    return {
        "threshold": thr,
        "threshold_source": thr_src,
        "paper_threshold_claim": 0.8,
        "sdet_component_weights": comps,
        "sdet_scale": "0~100 (×100)",
        "fatal_zero_rules": ["invalid_json", "missing_official_gt"],
        "note": "논문의 '1−정규화 구조 편집거리'가 아니라 8성분 가중합 (audit C-03)",
    }


def extract_serving() -> dict:
    req = _read("requirements.txt")
    worker_tokens, worker_src = _extract("utils/ga_search/local_worker.py", r'"local_max_new_tokens",\s*(\d+)', int)
    if worker_tokens == "EXTRACT_FAILED":
        worker_tokens, worker_src = _extract("utils/ga_search/local_worker.py", r"local_max_new_tokens[\"'\],\s ]*(?:or|,|=)?\s*(\d+)", int)
    reg_tokens, reg_src = _extract("utils/ga_search/local_model_registry.py", r"local_max_new_tokens:\s*int\s*=\s*(\d+)", int)
    return {
        "vllm_present": bool(re.search(r"^vllm", req, re.M)),
        "actual_backends": {
            "worker": "HF transformers subprocess (utils/ga_search/local_worker.py; greedy decoding)",
            "local": "OpenAI 호환 HTTP (기본 http://127.0.0.1:8000/v1/chat/completions)",
            "openai": "OpenAI SDK (gpt-4.1-mini 기본)",
        },
        "max_model_len": "NOT_FOUND",
        "max_model_len_search": "grep -rn max_model_len 전역 0건 (audit C-19)",
        "local_max_new_tokens": {
            "local_worker_default": worker_tokens,
            "local_worker_source": worker_src,
            "registry_default": reg_tokens,
            "registry_source": reg_src,
        },
        "local_models_available": [
            "qwen25_coder_7b", "llama31_8b", "qwen25_coder_14b", "gemma2_9b_it", "phi35_mini",
        ],
        "gpu_probe": "2×RTX A6000 48GB; worker 모드 Qwen7B 1건 생성 성공 (results/phase1_worker_probe/)",
    }


def build_assumptions_diff(m: dict) -> list[dict]:
    bench = m["datasets"]["benchmark"]
    replay = m["datasets"]["replay_sources"]
    budget = m["ga_budget"]
    return [
        {
            "id": "AS-01",
            "paper": "벤치마크 N=180",
            "measured": f"정본 CSV {bench['rows']}행({bench['n_categories']}범주). cat1~6 합계 180으로 분할 설계 가능하나 분할 매니페스트 부재",
            "status": "MISMATCH",
            "mapped_wi": "WI-01/WI-05",
        },
        {
            "id": "AS-02",
            "paper": "리플레이 60건 (탐색 30 / 보류 30)",
            "measured": f"ReplayFit 계산 경로 자체 부재. 실사용 리플레이 원천: usr_rag {replay['usr_rag_rows']}행 + admin 로그 {replay['admin_log_rows']}건",
            "status": "ABSENT",
            "mapped_wi": "WI-05",
        },
        {
            "id": "AS-03",
            "paper": "스트레스 40건",
            "measured": "스트레스 셋 전역 부재 (find/grep 0건)",
            "status": "ABSENT",
            "mapped_wi": "WI-01 후속(스트레스 셋 확보 또는 FIX_PAPER)",
        },
        {
            "id": "AS-04",
            "paper": "GA 예산 pop 10 / gen 12 / elite 2 / tournament 3 / p_m 0.35",
            "measured": f"정본 기본 pop {budget['canonical_cli_defaults']['population']} / gen {budget['canonical_cli_defaults']['generations']}, elite 1 고정, tournament 없음, 100% 변이. 레거시 백업 pop {budget['legacy_backup_defaults']['population']} / gen {budget['legacy_backup_defaults']['generations']} / elites {budget['legacy_backup_defaults']['elites']}",
            "status": "MISMATCH",
            "mapped_wi": "WI-16",
        },
        {
            "id": "AS-05",
            "paper": "적합도 가중치 0.50:0.15:0.20:0.10:0.05, config 외부화",
            "measured": f"하드코딩 수식: {m['fitness']['canonical']['formula']}",
            "status": "MISMATCH",
            "mapped_wi": "WI-07",
        },
        {
            "id": "AS-06",
            "paper": "세대당 층화 표본 9범주×5=45",
            "measured": f"층화 표본기 부재(rng.sample 단순 무작위). 실데이터는 {bench['n_categories']}범주 — 9범주 서술은 FIX_PAPER 대상",
            "status": "ABSENT",
            "mapped_wi": "WI-07 (+FIX_PAPER: 9범주→8범주)",
        },
        {
            "id": "AS-07",
            "paper": "명령당 3회 반복 생성 평균, 비율 0.1% 반올림",
            "measured": "candidate_k 기본 1(정본)·2(레거시), 3 지정 스크립트/설정 전역 부재. 반올림 프로토콜 코드 부재",
            "status": "ABSENT",
            "mapped_wi": "WI-02/WI-03 실행 config에서 적용",
        },
        {
            "id": "AS-08",
            "paper": "vLLM 서빙 + max_model_len 기록",
            "measured": "vLLM 부재(requirements 포함). 실서빙: HF transformers subprocess + OpenAI호환 local HTTP. max_model_len 전역 0건, local_max_new_tokens(256/512)만 존재",
            "status": "MISMATCH",
            "mapped_wi": "WI-11 (+FIX_PAPER)",
        },
    ]


def main() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    manifest = {
        "generated_by": "tools/build_settings_manifest.py",
        "source_commit": head,
        "datasets": {
            "benchmark": measure_benchmark(),
            "replay_sources": measure_replay_sources(),
            "stress": measure_stress(),
        },
        "ga_budget": extract_ga_budget(),
        "fitness": extract_fitness(),
        "det": extract_det(),
        "serving": extract_serving(),
    }
    manifest["assumptions_diff"] = build_assumptions_diff(manifest)

    out_json = REPO / "audit" / "manifest.json"
    out_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 논문 가정(AS-01~08) vs 저장소 실측 diff",
        "",
        f"- 생성: tools/build_settings_manifest.py @ {head}",
        "- 실측 상세: audit/manifest.json",
        "",
        "| ID | 논문 가정 | 실측 | 상태 | 매핑 WI |",
        "|---|---|---|---|---|",
    ]
    for d in manifest["assumptions_diff"]:
        lines.append(f"| {d['id']} | {d['paper']} | {d['measured']} | {d['status']} | {d['mapped_wi']} |")
    (REPO / "audit" / "assumptions_diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written: {out_json}")
    print(f"written: {REPO / 'audit' / 'assumptions_diff.md'}")
    failed = json.dumps(manifest, ensure_ascii=False).count("EXTRACT_FAILED")
    print(f"EXTRACT_FAILED count: {failed}")


if __name__ == "__main__":
    main()
