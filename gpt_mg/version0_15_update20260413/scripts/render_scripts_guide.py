#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _code_block(code: str, language: str = "bash") -> str:
    return (
        f"<div class='code-block'>"
        f"<div class='code-label'>{_escape(language)}</div>"
        f"<pre><code>{_escape(code.strip())}</code></pre>"
        f"</div>"
    )


def _badge(text: str, kind: str = "neutral") -> str:
    return f"<span class='badge badge-{_escape(kind)}'>{_escape(text)}</span>"


def _card(title: str, body: str, *, kind: str = "neutral") -> str:
    return (
        f"<article class='card card-{_escape(kind)}'>"
        f"<h3>{_escape(title)}</h3>"
        f"<div class='card-body'>{body}</div>"
        f"</article>"
    )


def _list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head_html = "".join(f"<th>{_escape(header)}</th>" for header in headers)
    row_html = []
    for row in rows:
        row_html.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    return (
        "<div class='table-wrap'>"
        "<table>"
        f"<thead><tr>{head_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table>"
        "</div>"
    )


def _section(section_id: str, title: str, subtitle: str, body: str) -> str:
    return (
        f"<section id='{_escape(section_id)}' class='section'>"
        f"<div class='section-head'>"
        f"<p class='eyebrow'>{_escape(section_id.upper())}</p>"
        f"<h2>{_escape(title)}</h2>"
        f"<p class='section-subtitle'>{_escape(subtitle)}</p>"
        f"</div>"
        f"{body}"
        "</section>"
    )


def _script_link(filename: str) -> str:
    return f"<a href='{_escape(filename)}'>{_escape(filename)}</a>"


def _render_html() -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    quick_cards = "".join(
        [
            _card(
                "가장 먼저 실행할 파일",
                "<p><strong>run_benchmark.py</strong> 하나만 기억하면 됩니다.</p>"
                "<p>single-model이면 row report가 자동으로 붙고, 필요한 비교와 audit도 옵션으로 이어집니다.</p>",
                kind="primary",
            ),
            _card(
                "실험 비교",
                "<p><strong>--compare-to</strong>를 주면 baseline vs retrieval 같은 A/B 비교를 자동으로 수행합니다.</p>"
                "<p>별도 실행은 <code>compare_benchmarks.py</code>입니다.</p>",
                kind="accent",
            ),
            _card(
                "DET 읽는 기준",
                "<p>역사 비교와 GA는 <strong>legacy</strong>, 실제 품질 판정과 리포트는 <strong>strict</strong>가 권장됩니다.</p>",
                kind="warn",
            ),
            _card(
                "가장 흔한 오해",
                "<p><code>failure_reasons</code>는 런타임 크래시 로그가 아니라 <strong>왜 감점됐는지</strong>를 설명하는 태그입니다.</p>",
                kind="danger",
            ),
        ]
    )

    start_here = _section(
        "start-here",
        "처음 시작할 때 보는 순서",
        "복잡한 스크립트들을 한 번에 외우기보다, 가장 짧은 의사결정 경로만 먼저 잡는 것이 좋습니다.",
        "".join(
            [
                "<div class='grid grid-2'>",
                _card(
                    "1. 환경 준비",
                    _code_block(
                        """
cd /home/mgjeong/Desktop/llm/JOILang-Server

export JOI_V15_WORKER_PYTHON=/home/mgjeong/miniconda3/envs/l/bin/python
export JOI_V15_LOCAL_DEVICE=cuda:0
                        """,
                        "bash",
                    ),
                    kind="neutral",
                ),
                _card(
                    "2. 모델 준비 상태 확인",
                    _code_block(
                        """
python gpt_mg/version0_15_update20260413/scripts/run_benchmark.py \
  --suite paper_local5 \
  --preflight-only \
  --print-worker-info
                        """,
                        "bash",
                    ),
                    kind="neutral",
                ),
                _card(
                    "3. 가장 기본적인 smoke test",
                    _code_block(
                        """
python gpt_mg/version0_15_update20260413/scripts/run_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --det-profile strict \
  --print-mode summary \
  --strict-availability
                        """,
                        "bash",
                    ),
                    kind="primary",
                ),
                _card(
                    "4. 자주 쓰는 후처리 옵션",
                    _list(
                        [
                            "<code>--analyze-det</code>: legacy vs strict DET audit",
                            "<code>--compare-to /abs/path</code>: 이전 실험과 자동 비교",
                            "<code>--export-row-report</code>: multi-model run에서도 row report 생성",
                            "<code>--export-paper-artifacts</code>: figure / table export",
                        ]
                    ),
                    kind="accent",
                ),
                "</div>",
            ]
        ),
    )

    script_rows = [
        [
            _script_link("run_benchmark.py"),
            _badge("권장", "primary"),
            "메인 benchmark 실행기. 실험 진입점으로 가장 먼저 기억할 파일.",
        ],
        [
            _script_link("compare_benchmarks.py"),
            _badge("직접 실행", "accent"),
            "baseline vs retrieval 등 두 결과 디렉터리 비교.",
        ],
        [
            _script_link("export_row_report.py"),
            _badge("직접 실행", "accent"),
            "GT JOICode vs Generated JOICode를 좌우 배치한 HTML/PDF 리포트 생성.",
        ],
        [
            _script_link("audit_det.py"),
            _badge("직접 실행", "warn"),
            "legacy vs strict DET 차이 분석 및 과대평가 탐지.",
        ],
        [
            _script_link("export_paper_figures.py"),
            _badge("직접 실행", "neutral"),
            "scatter / bar / category figure export.",
        ],
        [
            _script_link("prepare_local_models.py"),
            _badge("준비", "neutral"),
            "local model cache, readiness, preflight 준비.",
        ],
        [
            _script_link("inspect_service_context.py"),
            _badge("디버깅", "neutral"),
            "schema fallback vs retrieval fallback prompt 길이/구성 확인.",
        ],
        [
            _script_link("run_generate.py"),
            _badge("내부용", "danger"),
            "candidate generation 저수준 실행기. 보통은 직접 치지 않음.",
        ],
        [
            _script_link("run_rerank.py"),
            _badge("내부용", "danger"),
            "DET rerank / repair 저수준 실행기.",
        ],
        [
            _script_link("run_ga_search.py"),
            _badge("실험", "neutral"),
            "GA prompt search.",
        ],
        [
            _script_link("run_category_sweep.py"),
            _badge("실험", "neutral"),
            "category sweep.",
        ],
        [
            _script_link("run_admin_feedback_update.py"),
            _badge("실험", "neutral"),
            "admin feedback update pipeline.",
        ],
    ]

    script_map = _section(
        "script-map",
        "스크립트 지도",
        "이 폴더 안 파일이 많아 보여도, 실제로는 상위 진입점 몇 개와 내부용 스크립트로 나뉩니다.",
        _table(["파일", "분류", "언제 쓰는가"], script_rows)
        + "<div class='callout callout-primary'><strong>실무 권장:</strong> 일반 사용자는 "
        "<code>run_generate.py</code>, <code>run_rerank.py</code>를 직접 치기보다 "
        "<code>run_benchmark.py</code>로 먼저 시작하는 편이 안전합니다.</div>",
    )

    workflows = _section(
        "workflows",
        "가장 자주 쓰는 실행 시나리오",
        "복사해서 바로 쓸 수 있는 대표 패턴을 시나리오별로 정리했습니다.",
        "".join(
            [
                "<div class='workflow-band'>",
                _card(
                    "단일 모델 + 자동 row report",
                    _code_block(
                        """
python gpt_mg/version0_15_update20260413/scripts/run_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --det-profile strict \
  --print-mode summary \
  --strict-availability
                        """,
                        "bash",
                    )
                    + "<p>single-model run이면 기본적으로 row report HTML/PDF가 자동 생성됩니다.</p>",
                    kind="primary",
                ),
                _card(
                    "단일 모델 + DET audit",
                    _code_block(
                        """
python gpt_mg/version0_15_update20260413/scripts/run_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --det-profile strict \
  --analyze-det \
  --print-mode summary \
  --strict-availability
                        """,
                        "bash",
                    ),
                    kind="warn",
                ),
                _card(
                    "기존 run과 자동 비교",
                    _code_block(
                        """
python gpt_mg/version0_15_update20260413/scripts/run_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --row-no 1 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --enable-retrieval-premapping \
  --retrieval-topk 10 \
  --retrieval-device cpu \
  --compare-to /abs/path/to/older/results_dir \
  --print-mode summary \
  --strict-availability
                        """,
                        "bash",
                    ),
                    kind="accent",
                ),
                _card(
                    "multi-model run + 특정 모델 row report",
                    _code_block(
                        """
python gpt_mg/version0_15_update20260413/scripts/run_benchmark.py \
  --suite paper_local5 \
  --model-key qwen25_coder_7b \
  --model-key qwen25_coder_14b \
  --category 1 \
  --category 2 \
  --limit-per-category 10 \
  --candidate-k 1 \
  --repair-attempts 0 \
  --export-row-report \
  --row-report-model-key qwen25_coder_14b \
  --print-mode summary \
  --strict-availability
                        """,
                        "bash",
                    ),
                    kind="neutral",
                ),
                "</div>",
            ]
        ),
    )

    results_artifacts = _section(
        "results",
        "benchmark가 끝나면 어떤 결과가 생기나",
        "실험 결과는 보통 results/model_suite_<timestamp>/ 아래에 쌓입니다. 무엇을 먼저 봐야 하는지도 같이 표시했습니다.",
        "<div class='grid grid-3'>"
        + _card(
            "핵심 CSV",
            _list(
                [
                    "<code>suite_summary.csv</code>: 모델 단위 요약",
                    "<code>row_comparison.csv</code>: row 단위 상세 결과",
                    "<code>failure_reason_summary.csv</code>: failure reason 집계",
                    "<code>category_summary.csv</code>: category 단위 요약",
                ]
            ),
            kind="primary",
        )
        + _card(
            "자동 후처리 산출물",
            _list(
                [
                    "<code>side_by_side_report_&lt;model_key&gt;/report.html</code>",
                    "<code>side_by_side_report_&lt;model_key&gt;/report.pdf</code>",
                    "<code>det_audit/analysis_summary.json</code>",
                    "<code>context_compare_.../context_comparison_summary.json</code>",
                ]
            ),
            kind="accent",
        )
        + _card(
            "논문용 산출물",
            _list(
                [
                    "<code>main_model_comparison.csv</code>",
                    "<code>tradeoff_summary.csv</code>",
                    "<code>paper_metrics_summary.json</code>",
                    "<code>paper_figures/...</code>",
                ]
            ),
            kind="warn",
        )
        + "</div>",
    )

    det_profile_table = _table(
        ["프로파일", "장점", "약점", "권장 용도"],
        [
            [
                "<strong>legacy</strong>",
                "기존 실험과 호환, 빠르고 비교적 관대함",
                "값 흐름, receiver coverage, numeric/enum grounding을 후하게 줄 수 있음",
                "historical comparison, GA search",
            ],
            [
                "<strong>strict</strong>",
                "GT service coverage, receiver coverage, dataflow, numeric/enum grounding을 엄격히 반영",
                "service equivalence가 없는 케이스는 다소 보수적으로 볼 수 있음",
                "최종 품질 검증, 리포트, 논문용 해석",
            ],
        ],
    )

    det_metric_cards = "".join(
        [
            _card("det_score", "<p>최종 DET 점수. 0~100.</p>", kind="primary"),
            _card("det_gt_exact", "<p>GT와 exact match 여부.</p>", kind="neutral"),
            _card("det_gt_similarity", "<p>GT와의 전체 유사도. exact가 아니어도 구조가 비슷하면 일부 점수를 받습니다.</p>", kind="neutral"),
            _card("det_service_match", "<p>생성 코드의 서비스가 schema에 얼마나 잘 resolve되는지.</p>", kind="neutral"),
            _card("det_arg_type_ok", "<p>각 서비스의 인자 타입과 개수가 schema expectation과 얼마나 맞는지.</p>", kind="neutral"),
            _card("det_precondition_ok", "<p>전제조건이나 guard가 필요한 경우 그것이 반영됐는지.</p>", kind="neutral"),
            _card("det_semantic_ok", "<p>명령 의미와 action 방향이 얼마나 맞는지.</p>", kind="neutral"),
            _card("det_min_extraneous", "<p>명령에 없는 불필요한 action이 섞였는지.</p>", kind="neutral"),
            _card("det_gt_service_coverage", "<p>GT에 필요한 서비스를 생성 코드가 모두 포함했는지.</p>", kind="warn"),
            _card("det_gt_receiver_coverage", "<p>GT의 receiver scope와 instance coverage를 얼마나 잘 덮었는지.</p>", kind="warn"),
            _card("det_dataflow_score", "<p>sensor/value를 읽은 뒤 실제 downstream 함수에 전달했는지.</p>", kind="warn"),
            _card("det_numeric_grounding", "<p>시간, 채널, 온도 같은 숫자 정보가 정확히 반영됐는지.</p>", kind="warn"),
            _card("det_enum_grounding", "<p>enum 값(dry, emergency 등)이 정확한지.</p>", kind="warn"),
        ]
    )

    det_section = _section(
        "det",
        "DET를 어떻게 읽어야 하나",
        "DET는 단순 exact match가 아니라, service 해석·의미 정렬·GT coverage·값 흐름을 여러 축으로 합산한 점수입니다.",
        det_profile_table
        + "<div class='callout callout-warn'><strong>권장 해석:</strong> "
        "historical/GA 비교는 <code>legacy</code>, 실제 품질 리포트와 acceptance는 <code>strict</code>를 우선으로 보세요.</div>"
        + "<div class='grid grid-3 metrics-grid'>"
        + det_metric_cards
        + "</div>",
    )

    failure_rows = [
        ["<strong>invalid_json</strong>", "출력이 JSON으로 파싱되지 않음", "자유 텍스트, braces mismatch, explanation 혼입", "맨 앞단 실패. 나머지 지표보다 먼저 해결"],
        ["<strong>schema_missing_keys</strong>", "JSON은 맞지만 name / cron / period / code 중 필수 키 누락", "code 없이 script만 반환", "출력 스키마 프롬프트 확인"],
        ["<strong>no_parseable_member_access</strong>", "code는 있지만 (#Device).Service(...) 형식으로 parse 불가", "JOILang 대신 의사코드 반환", "코드 포맷을 먼저 고정"],
        ["<strong>unknown_service:&lt;member&gt;</strong>", "schema에서 매핑 불가한 service/member", "invented helper, 심한 오타, 잘못된 camel/snake case", "schema grounding 강화"],
        ["<strong>service_match</strong>", "전체 호출 중 일부가 schema에 정확히 resolve되지 않음", "맞는 서비스와 틀린 서비스 혼재", "unknown service와 함께 자주 나타남"],
        ["<strong>arg_type</strong>", "서비스는 맞지만 인자 타입/개수/순서 불일치", "숫자 대신 string, enum 대신 자유 텍스트", "numeric/enum grounding과 같이 해석"],
        ["<strong>precondition</strong>", "필요한 전제조건/guard가 부족", "power/switch guard 없이 바로 action", "명령 의도보다 실행 안전성 문제"],
        ["<strong>semantic</strong>", "명령 의미와 action 방향이 약하게 맞음", "increase/decrease, lock/unlock 반대", "service 이름은 맞아도 의미가 어긋날 수 있음"],
        ["<strong>extraneous</strong>", "명령에 없는 불필요한 action 추가", "speaker가 필요 없는데 speaker까지 사용", "과생성 신호"],
        ["<strong>gt_mismatch</strong>", "GT와 exact match는 아님", "매우 넓은 요약 태그", "이것만 보면 부족. 아래 coverage 항목을 같이 봐야 함"],
        ["<strong>gt_service_coverage</strong>", "GT에 필요한 서비스 일부 누락", "HumiditySensor + Speaker 중 Speaker 누락", "가장 자주 중요한 감점 사유 중 하나"],
        ["<strong>gt_receiver_coverage</strong>", "GT의 receiver scope 일부 누락", "Front/Back 둘 다 필요한데 하나만 처리", "all(...) 계열 명령에서 중요"],
        ["<strong>dataflow</strong>", "읽은 값이 실제 sink로 전달되지 않음", "sensor value를 읽기만 하고 speak/set에 안 씀", "strict에서 핵심"],
        ["<strong>numeric_grounding</strong>", "숫자/단위 정보가 정확하지 않음", "30분을 1800초 대신 ms 표현 또는 잘못된 수치", "strict에서 강하게 감점"],
        ["<strong>enum_grounding</strong>", "enum 값이 틀림", "dry 대신 warm", "strict에서 강하게 감점"],
    ]

    failure_section = _section(
        "failure-reasons",
        "failure_reasons 상세 해설",
        "failure_reasons는 런타임 크래시 로그가 아니라, 왜 감점됐는지를 설명하는 진단 태그입니다.",
        _table(["failure_reason", "무슨 뜻인가", "대표 원인", "읽는 팁"], failure_rows)
        + "<div class='callout callout-danger'><strong>가장 흔한 오해:</strong> "
        "<code>gt_mismatch</code> 하나만 보고 판단하면 원인을 놓치기 쉽습니다. "
        "<code>gt_service_coverage</code>, <code>gt_receiver_coverage</code>, <code>dataflow</code>, "
        "<code>numeric_grounding</code>, <code>enum_grounding</code>을 같이 봐야 합니다.</div>",
    )

    case_studies = _section(
        "cases",
        "실제 DET 해석 예시",
        "legacy가 후하게 준 케이스와 strict가 더 정확하게 본 케이스를 같이 보면, 어떤 failure를 어떻게 읽어야 하는지 훨씬 빠르게 익힐 수 있습니다.",
        _table(
            ["케이스", "legacy", "strict", "주요 failure", "해석"],
            [
                [
                    "row 10 humidity - sensor_only",
                    "87.7078",
                    "67.5942",
                    "<code>dataflow</code>, <code>gt_mismatch</code>, <code>gt_receiver_coverage</code>, <code>gt_service_coverage</code>",
                    "센서값은 읽었지만 실제로 speaker까지 전달하지 못한 코드. legacy는 후했고 strict는 데이터 흐름이 끊긴 점을 잡았습니다.",
                ],
                [
                    "row 10 humidity - malformed_chain",
                    "96.1031",
                    "69.9",
                    "<code>dataflow</code>, <code>gt_mismatch</code>",
                    "겉보기에는 비슷하지만 source value가 sink에 제대로 연결되지 않은 케이스입니다.",
                ],
                [
                    "row 3 rice cooker - wrong_unit_ms_expr",
                    "93.9479",
                    "69.9",
                    "<code>arg_type</code>, <code>gt_mismatch</code>, <code>numeric_grounding</code>",
                    "시간/단위가 미묘하게 틀린 코드는 strict에서 강하게 내려갑니다.",
                ],
                [
                    "row 37 door lock - explicit_two",
                    "92.3641",
                    "97.0607",
                    "<code>gt_mismatch</code>",
                    "GT의 all(...)을 Front/Back 두 줄로 명시적으로 푼 케이스. strict는 receiver coverage가 충분해서 더 높게 볼 수 있습니다.",
                ],
                [
                    "row 37 door lock - only_back",
                    "96.7727",
                    "69.9",
                    "<code>gt_mismatch</code>, <code>gt_receiver_coverage</code>",
                    "그룹 receiver 중 일부만 처리했는데 legacy가 너무 높게 준 대표 사례입니다.",
                ],
            ],
        )
        + "<div class='callout callout-neutral'><strong>남아 있는 한계:</strong> "
        "<code>MoveToRGB</code> vs <code>SetColor</code>처럼 service equivalence map이 필요한 케이스는 strict가 다소 보수적으로 볼 수 있습니다.</div>",
    )

    playbook = _section(
        "playbook",
        "문제 분석 순서",
        "row report와 CSV를 볼 때 어디서부터 읽으면 빠른지, 실무 기준 디버깅 순서를 정리했습니다.",
        "<div class='grid grid-2'>"
        + _card(
            "row report 먼저 볼 때",
            _list(
                [
                    "<code>DET</code>와 <code>failure_reasons</code>를 먼저 확인",
                    "<code>gt_service_coverage</code>, <code>gt_receiver_coverage</code>, <code>dataflow</code>를 바로 같이 보기",
                    "GT vs Generated JOICode를 좌우 배치로 비교",
                    "필요하면 <code>prompt_tokens</code>, <code>llm_latency_sec</code>, <code>peak_vram_gb</code>까지 확인",
                ]
            ),
            kind="primary",
        )
        + _card(
            "CSV / audit으로 깊게 볼 때",
            _list(
                [
                    "<code>failure_reason_summary.csv</code>에서 모델별 failure distribution 확인",
                    "<code>row_comparison.csv</code>에서 낮은 DET row 필터링",
                    "<code>audit_det.py</code>로 legacy vs strict 차이 확인",
                    "<code>compare_benchmarks.py</code>로 baseline vs retrieval 변화 확인",
                ]
            ),
            kind="accent",
        )
        + "</div>"
        + "<div class='callout callout-primary'><strong>실무 팁:</strong> "
        "<code>legacy high && strict low</code>인 row는 evaluator가 후하게 준 의심 케이스라서 우선순위 높게 보는 것이 좋습니다.</div>",
    )

    naming = _section(
        "naming",
        "짧은 이름 vs 기존 긴 이름",
        "새 짧은 이름이 권장 entrypoint이고, 기존 긴 이름은 호환용으로 유지됩니다.",
        _table(
            ["기존 이름", "권장 이름", "설명"],
            [
                ["<code>run_model_suite_benchmark.py</code>", "<code>run_benchmark.py</code>", "메인 benchmark 실행기"],
                ["<code>compare_service_context_results.py</code>", "<code>compare_benchmarks.py</code>", "두 결과 디렉터리 비교"],
                ["<code>export_joi_code_side_by_side_report.py</code>", "<code>export_row_report.py</code>", "GT vs Generated HTML/PDF row report"],
                ["<code>analyze_det_profiles.py</code>", "<code>audit_det.py</code>", "DET profile audit"],
            ],
        ),
    )

    toc_items = [
        ("start-here", "처음 시작"),
        ("script-map", "스크립트 지도"),
        ("workflows", "실행 시나리오"),
        ("results", "결과 구조"),
        ("det", "DET 설명"),
        ("failure-reasons", "failure_reasons"),
        ("cases", "실제 사례"),
        ("playbook", "디버깅 순서"),
        ("naming", "이름 매핑"),
    ]
    toc_html = "".join(
        f"<a href='#{_escape(anchor)}'>{_escape(label)}</a>" for anchor, label in toc_items
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>version0_15 Scripts Guide</title>
  <style>
    :root {{
      --bg: #f5f1e8;
      --paper: #fffdf8;
      --ink: #1c1a18;
      --muted: #615b53;
      --line: #ddd2c2;
      --primary: #7d4f2c;
      --accent: #145f6a;
      --warn: #8a5b0f;
      --danger: #8f2d2d;
      --primary-soft: #f2e2d1;
      --accent-soft: #dceff2;
      --warn-soft: #f6e7c3;
      --danger-soft: #f3d8d8;
      --neutral-soft: #efe7db;
      --shadow: 0 20px 50px rgba(28, 26, 24, 0.08);
      --radius: 18px;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(125, 79, 44, 0.10), transparent 28%),
        radial-gradient(circle at top right, rgba(20, 95, 106, 0.10), transparent 26%),
        linear-gradient(180deg, #f6f1e7 0%, #f4efe7 48%, #f6f2ec 100%);
      color: var(--ink);
      font: 16px/1.65 "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code, pre {{
      font-family: "JetBrains Mono", "SFMono-Regular", Menlo, Consolas, monospace;
    }}
    .page {{
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
      gap: 28px;
      max-width: 1560px;
      margin: 0 auto;
      padding: 28px 28px 56px;
    }}
    .sidebar {{
      position: sticky;
      top: 22px;
      align-self: start;
      background: rgba(255, 253, 248, 0.86);
      backdrop-filter: blur(14px);
      border: 1px solid rgba(221, 210, 194, 0.9);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 24px;
    }}
    .sidebar h1 {{
      margin: 0;
      font-size: 1.65rem;
      line-height: 1.15;
      letter-spacing: -0.02em;
    }}
    .sidebar .subtitle {{
      margin: 12px 0 16px;
      color: var(--muted);
      font-size: 0.96rem;
    }}
    .sidebar .meta {{
      color: var(--muted);
      font-size: 0.86rem;
      margin-bottom: 18px;
    }}
    .sidebar nav {{
      display: grid;
      gap: 8px;
      margin: 18px 0 0;
    }}
    .sidebar nav a {{
      padding: 10px 12px;
      border-radius: 12px;
      background: #fff8ef;
      border: 1px solid var(--line);
      color: var(--ink);
      font-weight: 600;
    }}
    .sidebar nav a:hover {{
      background: #fff4e4;
      text-decoration: none;
    }}
    .sidebar .legend {{
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px dashed var(--line);
    }}
    .sidebar .legend p {{
      margin: 0 0 10px;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .main {{
      min-width: 0;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(125, 79, 44, 0.12), rgba(20, 95, 106, 0.10));
      border: 1px solid rgba(221, 210, 194, 0.95);
      border-radius: 28px;
      box-shadow: var(--shadow);
      padding: 34px 34px 28px;
      margin-bottom: 28px;
      overflow: hidden;
      position: relative;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -80px -80px auto;
      width: 240px;
      height: 240px;
      background: radial-gradient(circle, rgba(125, 79, 44, 0.15), transparent 68%);
      pointer-events: none;
    }}
    .eyebrow {{
      margin: 0 0 8px;
      color: var(--primary);
      text-transform: uppercase;
      font-size: 0.78rem;
      font-weight: 800;
      letter-spacing: 0.11em;
    }}
    .hero h2 {{
      margin: 0 0 10px;
      font-size: 2.6rem;
      line-height: 1.08;
      letter-spacing: -0.03em;
    }}
    .hero p {{
      margin: 0;
      max-width: 72ch;
      color: #3a342f;
      font-size: 1.02rem;
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
      margin-top: 24px;
    }}
    .section {{
      margin: 28px 0 34px;
      background: rgba(255, 253, 248, 0.9);
      border: 1px solid rgba(221, 210, 194, 0.95);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 28px 28px 24px;
    }}
    .section-head {{
      margin-bottom: 18px;
    }}
    .section-head h2 {{
      margin: 0;
      font-size: 1.9rem;
      line-height: 1.15;
      letter-spacing: -0.02em;
    }}
    .section-subtitle {{
      margin: 10px 0 0;
      color: var(--muted);
      max-width: 78ch;
    }}
    .grid {{
      display: grid;
      gap: 18px;
    }}
    .grid-2 {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .grid-3 {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .workflow-band {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .card {{
      border-radius: var(--radius);
      padding: 18px 18px 16px;
      border: 1px solid var(--line);
      background: var(--paper);
      min-width: 0;
    }}
    .card h3 {{
      margin: 0 0 10px;
      font-size: 1.12rem;
      line-height: 1.25;
    }}
    .card p {{
      margin: 0 0 10px;
    }}
    .card ul {{
      margin: 0;
      padding-left: 20px;
    }}
    .card-primary {{ background: linear-gradient(180deg, #fffaf3, var(--primary-soft)); }}
    .card-accent {{ background: linear-gradient(180deg, #fafdfe, var(--accent-soft)); }}
    .card-warn {{ background: linear-gradient(180deg, #fffdf6, var(--warn-soft)); }}
    .card-danger {{ background: linear-gradient(180deg, #fffafb, var(--danger-soft)); }}
    .badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 0.28rem 0.66rem;
      font-size: 0.8rem;
      font-weight: 700;
      border: 1px solid transparent;
      white-space: nowrap;
    }}
    .badge-primary {{ background: var(--primary-soft); color: var(--primary); border-color: rgba(125,79,44,0.18); }}
    .badge-accent {{ background: var(--accent-soft); color: var(--accent); border-color: rgba(20,95,106,0.16); }}
    .badge-warn {{ background: var(--warn-soft); color: var(--warn); border-color: rgba(138,91,15,0.16); }}
    .badge-danger {{ background: var(--danger-soft); color: var(--danger); border-color: rgba(143,45,45,0.16); }}
    .badge-neutral {{ background: var(--neutral-soft); color: #5c534a; border-color: rgba(92,83,74,0.12); }}
    .callout {{
      margin-top: 18px;
      padding: 15px 17px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: #fff9f1;
    }}
    .callout-primary {{ background: var(--primary-soft); }}
    .callout-warn {{ background: var(--warn-soft); }}
    .callout-danger {{ background: var(--danger-soft); }}
    .callout-neutral {{ background: var(--neutral-soft); }}
    .code-block {{
      border: 1px solid rgba(23, 21, 19, 0.08);
      border-radius: 16px;
      overflow: hidden;
      background: #161512;
      color: #f7efe5;
      margin-top: 10px;
    }}
    .code-label {{
      background: rgba(255,255,255,0.08);
      color: #dbcdb8;
      font-size: 0.78rem;
      font-weight: 700;
      padding: 8px 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    pre {{
      margin: 0;
      overflow: auto;
      padding: 16px 18px 18px;
      line-height: 1.55;
      font-size: 0.88rem;
    }}
    .table-wrap {{
      overflow: auto;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: var(--paper);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 780px;
    }}
    th, td {{
      padding: 13px 14px;
      text-align: left;
      vertical-align: top;
      border-bottom: 1px solid rgba(221, 210, 194, 0.85);
    }}
    th {{
      background: #f8f1e5;
      font-size: 0.86rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #5e5449;
    }}
    tbody tr:nth-child(even) {{
      background: rgba(248, 241, 229, 0.38);
    }}
    .metrics-grid {{
      margin-top: 18px;
    }}
    .footer {{
      margin-top: 28px;
      color: var(--muted);
      font-size: 0.88rem;
      text-align: right;
    }}
    @media (max-width: 1220px) {{
      .page {{
        grid-template-columns: 1fr;
      }}
      .sidebar {{
        position: static;
      }}
    }}
    @media (max-width: 920px) {{
      .hero-grid,
      .grid-3,
      .workflow-band,
      .grid-2 {{
        grid-template-columns: 1fr;
      }}
      .hero h2 {{
        font-size: 2rem;
      }}
      .section {{
        padding: 22px 18px 18px;
      }}
      .page {{
        padding: 16px;
      }}
    }}
    @media print {{
      body {{
        background: white;
      }}
      .page {{
        display: block;
        max-width: none;
        padding: 0;
      }}
      .sidebar {{
        position: static;
        box-shadow: none;
        margin-bottom: 18px;
      }}
      .section,
      .hero,
      .card {{
        box-shadow: none;
      }}
      .section,
      .card,
      .code-block,
      .table-wrap {{
        break-inside: avoid;
      }}
      a {{
        color: inherit;
        text-decoration: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <aside class="sidebar">
      <p class="eyebrow">Scripts Guide</p>
      <h1>version0_15<br/>Scripts README</h1>
      <p class="subtitle">실험 진입점, 자동 후처리, DET 점수 체계, failure reason 해석을 한 번에 보는 시각 가이드</p>
      <p class="meta">Generated at {generated_at}</p>
      <nav>{toc_html}</nav>
      <div class="legend">
        <p><strong>가장 먼저 기억할 것</strong></p>
        <p><code>run_benchmark.py</code> 하나면 benchmark 흐름은 거의 시작할 수 있습니다.</p>
      </div>
    </aside>
    <main class="main">
      <section class="hero">
        <p class="eyebrow">Quick Orientation</p>
        <h2>복잡한 스크립트를<br/>실행 순서 기준으로 다시 정리한 문서</h2>
        <p>
          이 문서는 <code>version0_15_update20260413/scripts/</code> 안의 스크립트들을
          “무엇을 먼저 실행해야 하는지”, “무슨 결과가 자동으로 생기는지”, “DET와 failure reasons를 어떻게 읽어야 하는지”
          기준으로 다시 구조화한 가이드입니다.
        </p>
        <div class="hero-grid">{quick_cards}</div>
      </section>
      {start_here}
      {script_map}
      {workflows}
      {results_artifacts}
      {det_section}
      {failure_section}
      {case_studies}
      {playbook}
      {naming}
      <div class="footer">
        Visual companion for <a href="README.md">README.md</a> · source folder: {ROOT}
      </div>
    </main>
  </div>
</body>
</html>
"""


def _chrome_path(user_value: str) -> str:
    if user_value:
        return user_value
    for candidate in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return ""


def _render_pdf(html_path: Path, pdf_path: Path, chrome_path: str) -> dict[str, str | bool]:
    chrome = _chrome_path(chrome_path)
    if not chrome:
        return {"ok": False, "reason": "chrome_not_found", "pdf_path": str(pdf_path)}
    command = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--allow-file-access-from-files",
        f"--print-to-pdf={pdf_path}",
        str(html_path),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        return {"ok": False, "reason": f"chrome_exec_failed:{exc}", "pdf_path": str(pdf_path)}
    if completed.returncode != 0:
        return {
            "ok": False,
            "reason": f"chrome_returncode_nonzero:{completed.returncode}",
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "pdf_path": str(pdf_path),
        }
    return {"ok": True, "pdf_path": str(pdf_path), "chrome_path": chrome}


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a visual HTML/PDF guide for scripts/README.md")
    parser.add_argument("--output-html", default=str(ROOT / "README.html"))
    parser.add_argument("--output-pdf", default=str(ROOT / "README.pdf"))
    parser.add_argument("--skip-pdf", action="store_true")
    parser.add_argument("--chrome-path", default="")
    parser.add_argument("--print-json", action="store_true")
    args = parser.parse_args()

    html_path = Path(args.output_html).resolve()
    pdf_path = Path(args.output_pdf).resolve()
    html_path.write_text(_render_html(), encoding="utf-8")

    result = {
        "html": str(html_path),
        "pdf": None,
    }
    if not args.skip_pdf:
        result["pdf"] = _render_pdf(html_path, pdf_path, args.chrome_path)
    if args.print_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"HTML: {html_path}")
        if result["pdf"]:
            print(f"PDF: {result['pdf']}")


if __name__ == "__main__":
    main()
