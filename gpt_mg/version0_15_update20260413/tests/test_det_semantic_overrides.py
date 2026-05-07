from __future__ import annotations

import sys
from pathlib import Path


VERSION_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = VERSION_ROOT.parents[1]
if str(VERSION_ROOT) not in sys.path:
    sys.path.insert(0, str(VERSION_ROOT))

from utils.det_evaluator import evaluate_candidate


SERVICE_SCHEMA = str(SERVER_ROOT / "datasets" / "service_list_ver2.0.1.json")


def _evaluate(gt_code: str, pred_code: str) -> dict:
    return evaluate_candidate(
        "DET semantic override focused test",
        {
            "name": "Candidate",
            "cron": "",
            "period": 0,
            "code": pred_code,
        },
        SERVICE_SCHEMA,
        ground_truth={
            "name": "GroundTruth",
            "cron": "",
            "period": 0,
            "code": gt_code,
        },
        profile="strict",
    )


def _assert_det_equivalent(result: dict) -> None:
    assert result["det_gt_exact"] is True
    assert result["det_score"] == 100.0
    assert result["det_gt_service_coverage"] == 1.0
    assert result["det_gt_receiver_coverage"] == 1.0
    assert result["failure_reasons"] == []


def _assert_not_det_equivalent(result: dict) -> None:
    assert result["det_gt_exact"] is False
    assert "gt_mismatch" in result["failure_reasons"]


def test_light_hue_saturation_compound_matches_known_split_calls() -> None:
    result = _evaluate(
        "(#Light).light_movetohueandsaturation(200, 50)",
        "(#Light).light_movetohue(200)\n(#Light).light_movetosaturation(50)",
    )

    _assert_det_equivalent(result)


def test_light_hue_saturation_split_requires_both_calls() -> None:
    result = _evaluate(
        "(#Light).light_movetohueandsaturation(200, 50)",
        "(#Light).light_movetohue(200)",
    )

    _assert_not_det_equivalent(result)
    assert result["det_score"] < 70.0


def test_light_hue_saturation_split_requires_matching_arguments() -> None:
    result = _evaluate(
        "(#Light).light_movetohueandsaturation(200, 50)",
        "(#Light).light_movetohue(123)\n(#Light).light_movetosaturation(50)",
    )

    _assert_not_det_equivalent(result)
    assert result["det_score"] < 70.0


def test_speaker_report_ignores_gt_literal_wrapper_around_same_source() -> None:
    result = _evaluate(
        'dust = (#WeatherProvider).weatherprovider_pm10weather\n'
        '(#Speaker).speaker_speak("외부 미세먼지 농도는 " + dust + "입니다")',
        "x = (#WeatherProvider).weatherprovider_pm10weather\n"
        "(#Speaker).speaker_speak(x)",
    )

    _assert_det_equivalent(result)


def test_speaker_report_ignores_pred_literal_wrapper_around_same_source() -> None:
    result = _evaluate(
        "dust = (#WeatherProvider).weatherprovider_pm10weather\n"
        "(#Speaker).speaker_speak(dust)",
        "x = (#WeatherProvider).weatherprovider_pm10weather\n"
        '(#Speaker).speaker_speak("오늘의 농도는 " + x)',
    )

    _assert_det_equivalent(result)


def test_speaker_report_allows_explicit_pm10_pm25_output_family() -> None:
    result = _evaluate(
        'dust = (#WeatherProvider).weatherprovider_pm10weather\n'
        '(#Speaker).speaker_speak("외부 미세먼지 농도는 " + dust + "입니다")',
        "pm25 = (#WeatherProvider).weatherprovider_pm25weather\n"
        "(#Speaker).speaker_speak(pm25)",
    )

    _assert_det_equivalent(result)


def test_air_quality_pm10_pm25_value_reads_are_equivalent() -> None:
    result = _evaluate(
        "dust = (#WeatherProvider).weatherprovider_pm10weather",
        "pm25 = (#WeatherProvider).weatherprovider_pm25weather",
    )

    _assert_det_equivalent(result)


def test_wrapper_tolerance_does_not_apply_to_non_speaker_report_sink() -> None:
    result = _evaluate(
        'dust = (#WeatherProvider).weatherprovider_pm10weather\n'
        '(#Light).light_movetohue("외부 미세먼지 농도는 " + dust)',
        "x = (#WeatherProvider).weatherprovider_pm10weather\n"
        "(#Light).light_movetohue(x)",
    )

    _assert_not_det_equivalent(result)


def test_air_quality_value_read_equivalence_does_not_allow_unrelated_weather_source() -> None:
    result = _evaluate(
        "dust = (#WeatherProvider).weatherprovider_pm10weather",
        "temp = (#WeatherProvider).weatherprovider_temperatureweather",
    )

    _assert_not_det_equivalent(result)


def test_speaker_report_does_not_allow_unrelated_weather_source_family() -> None:
    result = _evaluate(
        "dust = (#WeatherProvider).weatherprovider_pm10weather\n"
        "(#Speaker).speaker_speak(dust)",
        "temp = (#WeatherProvider).weatherprovider_temperatureweather\n"
        "(#Speaker).speaker_speak(temp)",
    )

    _assert_not_det_equivalent(result)
    assert result["det_score"] < 70.0
