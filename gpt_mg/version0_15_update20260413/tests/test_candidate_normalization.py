from __future__ import annotations

import json
import sys
from pathlib import Path


VERSION_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = VERSION_ROOT.parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.pipeline_common import load_service_schema, normalize_candidate_json_text


SERVICE_SCHEMA = load_service_schema(SERVER_ROOT / "datasets" / "service_list_ver2.0.1.json")


def _normalize_code(code: str, command_text: str = "") -> str:
    raw = json.dumps({"name": "Candidate", "cron": "", "period": 0, "code": code}, ensure_ascii=False)
    normalized = normalize_candidate_json_text(raw, service_schema=SERVICE_SCHEMA, command_text=command_text)
    return json.loads(normalized)["code"]


def test_function_call_pipe_separator_is_normalized_to_comma() -> None:
    assert (
        _normalize_code('(#RiceCooker).RiceCooker_SetCookingParameters("cooking" | 30)')
        == '(#RiceCooker).ricecooker_setcookingparameters("cooking", 30)'
    )


def test_rice_cooker_minutes_are_normalized_to_seconds_for_cooking_parameters() -> None:
    assert (
        _normalize_code(
            '(#RiceCooker).RiceCooker_SetCookingParameters("cooking" | 30)',
            "Start the rice cooker on cooking mode for 30 minutes.",
        )
        == '(#RiceCooker).ricecooker_setcookingparameters("cooking", 1800)'
    )


def test_minutes_are_not_normalized_for_unrelated_functions() -> None:
    assert (
        _normalize_code(
            "(#Speaker).Speaker_Speak(30)",
            "Tell me the value for 30 minutes.",
        )
        == "(#Speaker).speaker_speak(30)"
    )


def test_value_condition_pipe_like_text_is_not_rewritten() -> None:
    code = (
        "if ((#TemperatureSensor).TemperatureSensor_Temperature >=| 30) {\n"
        '(#Speaker).Speaker_Speak("too hot")\n'
        "}"
    )

    assert _normalize_code(code) == (
        "if ((#TemperatureSensor).temperaturesensor_temperature >=| 30) {\n"
        '(#Speaker).speaker_speak("too hot")\n'
        "}"
    )


def test_quoted_pipe_inside_function_argument_is_preserved() -> None:
    assert (
        _normalize_code('(#ColorControl).ColorControl_SetColor("255|255|0")')
        == '(#ColorControl).colorcontrol_setcolor("255|255|0")'
    )
