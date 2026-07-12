"""WI-17 회귀 테스트 — 다중 행 실생성의 첫 행 명령 재사용 결함.

실측 근거: results/search_signal/20260712T180451Z (8개 상이한 명령 → 전부 동일 출력,
row 28/263 프롬프트 로그의 messages 완전 동일). package_for_row 가 행별 user 명령을
주입해야 하며, 생성 루프가 이를 사용해야 한다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from utils.ga_search.candidate_generation import generate_candidates_for_rows, package_for_row  # noqa: E402


def _rendered():
    return {
        "model_id": "test",
        "render_mode": "test",
        "prompt_text": "SYSTEM PROMPT",
        "system_prompt": "SYSTEM PROMPT",
        "user_prompt": "first command",
        "messages": [
            {"role": "system", "content": "SYSTEM PROMPT"},
            {"role": "user", "content": "first command"},
        ],
    }


def test_package_for_row_swaps_last_user_message():
    row = {"command_eng": "Turn off the fan.", "gt": "{}"}
    package = package_for_row(_rendered(), row)
    users = [m["content"] for m in package["messages"] if m["role"] == "user"]
    assert users == ["Turn off the fan."]
    assert package["user_prompt"] == "Turn off the fan."
    # 원본 불변
    assert _rendered()["messages"][1]["content"] == "first command"


def test_package_for_row_appends_when_no_user_message():
    rendered = _rendered()
    rendered["messages"] = [{"role": "system", "content": "SYS"}]
    rendered["user_prompt"] = ""
    package = package_for_row(rendered, {"command_kor": "선풍기 꺼줘", "gt": "{}"})
    assert package["messages"][-1] == {"role": "user", "content": "선풍기 꺼줘"}


def test_generation_prompt_logs_differ_per_row(tmp_path):
    rows = [
        (1, {"command_eng": "Turn on the light.", "category": "1", "gt": json.dumps({"name": "a", "cron": "", "period": -1, "code": "x"})}),
        (2, {"command_eng": "Lower the speaker volume.", "category": "2", "gt": json.dumps({"name": "b", "cron": "", "period": -1, "code": "y"})}),
    ]
    generate_candidates_for_rows(
        rows=rows,
        rendered_package=_rendered(),
        out_dir=tmp_path,
        llm_mode="mock",
        candidate_k=1,
        generation=0,
        genome_id="t",
    )
    log1 = json.loads((tmp_path / "prompts" / "row_1_cand_0_gen_000.json").read_text(encoding="utf-8"))
    log2 = json.loads((tmp_path / "prompts" / "row_2_cand_0_gen_000.json").read_text(encoding="utf-8"))
    user1 = [m["content"] for m in log1["messages"] if m["role"] == "user"]
    user2 = [m["content"] for m in log2["messages"] if m["role"] == "user"]
    assert user1 == ["Turn on the light."]
    assert user2 == ["Lower the speaker volume."]
    assert log1["messages"] != log2["messages"], "행별 메시지가 동일하면 첫 행 명령 재사용 결함 재발"
