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


def test_light_move_to_rgb_matches_color_control_set_color_with_same_rgb() -> None:
    result = _evaluate(
        "(#Light).light_movetorgb(255, 255, 0)",
        '(#ColorControl).colorcontrol_setcolor("255,255,0")',
    )

    _assert_det_equivalent(result)


def test_light_move_to_rgb_does_not_match_color_control_with_wrong_rgb() -> None:
    result = _evaluate(
        "(#Light).light_movetorgb(255, 255, 0)",
        '(#ColorControl).colorcontrol_setcolor("255,0,0")',
    )

    _assert_not_det_equivalent(result)
    assert result["det_score"] < 70.0


def test_light_move_to_rgb_does_not_match_color_control_with_legacy_pipe_rgb() -> None:
    result = _evaluate(
        "(#Light).light_movetorgb(255, 255, 0)",
        '(#ColorControl).colorcontrol_setcolor("255|255|0")',
    )

    _assert_not_det_equivalent(result)
    assert result["det_score"] < 70.0


def test_conditional_colorcontrol_setcolor_matches_light_movetorgb_with_same_trigger() -> None:
    result = _evaluate(
        'wait until (all(#Hallway #PresenceSensor).presencesensor_presence ==| true)\n'
        'all(#Hallway #Light).colorcontrol_setcolor("128,0,128")',
        "triggered := false\n"
        "if (all(#Hallway #PresenceSensor).presencesensor_presence == true) {\n"
        "  if (triggered == false) {\n"
        "    triggered = true\n"
        "    all(#Hallway #Light).light_movetorgb(128, 0, 128)\n"
        "  }\n"
        "} else {\n"
        "  triggered = false\n"
        "}",
    )

    _assert_det_equivalent(result)


def test_conditional_colorcontrol_setcolor_requires_same_rgb() -> None:
    result = _evaluate(
        'wait until (all(#Hallway #PresenceSensor).presencesensor_presence ==| true)\n'
        'all(#Hallway #Light).colorcontrol_setcolor("128,0,128")',
        "if (all(#Hallway #PresenceSensor).presencesensor_presence == true) {\n"
        "  all(#Hallway #Light).light_movetorgb(255, 0, 0)\n"
        "}",
    )

    _assert_not_det_equivalent(result)


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


def test_air_quality_sensor_dust_levels_are_equivalent_for_speaker_reports() -> None:
    result = _evaluate(
        "dust = (#AirQualitySensor).airqualitysensor_dustlevel\n"
        '(#Speaker).speaker_speak("미세먼지 농도는 " + dust + "입니다")',
        "fineDust = (#AirQualitySensor).airqualitysensor_finedustlevel\n"
        "(#Speaker).speaker_speak(fineDust)",
    )

    _assert_det_equivalent(result)


def test_air_quality_sensor_very_fine_dust_is_in_same_report_family() -> None:
    result = _evaluate(
        "dust = (#AirQualitySensor).airqualitysensor_dustlevel",
        "veryFineDust = (#AirQualitySensor).airqualitysensor_veryfinedustlevel",
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


def test_air_quality_sensor_dust_equivalence_does_not_allow_temperature() -> None:
    result = _evaluate(
        "dust = (#AirQualitySensor).airqualitysensor_dustlevel",
        "temp = (#AirQualitySensor).airqualitysensor_temperature",
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


def test_det_receiver_coverage_ignores_non_schema_location_tags() -> None:
    result = _evaluate(
        "if ((#Bedroom #TemperatureSensor).temperaturesensor_temperature >= 36.5) {\n"
        "  (#Bedroom #AirConditioner).airconditioner_settargettemperature(30)\n"
        "}",
        "if ((#TemperatureSensor #bedroom).temperaturesensor_temperature >= 36.5) {\n"
        "  (#AirConditioner).airconditioner_settargettemperature(30)\n"
        "}",
    )

    assert result["det_gt_service_coverage"] == 1.0
    assert result["det_gt_receiver_coverage"] == 1.0
    assert "gt_receiver_coverage" not in result["failure_reasons"]


def test_dataflow_accepts_sensor_assignment_variable_used_in_condition() -> None:
    result = _evaluate(
        "original_temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "delay(10 MIN)\n"
        "temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "if (temp >= original_temp + 1 or temp <= original_temp - 1) {\n"
        '  (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")\n'
        "}",
        "originalTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "delay(10 MIN)\n"
        "newTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "if ((newTemp >= originalTemp + 1) or (newTemp <= originalTemp - 1)) {\n"
        '  (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")\n'
        "}",
    )

    _assert_det_equivalent(result)


def test_snapshot_delta_report_accepts_diff_variable_algebra() -> None:
    result = _evaluate(
        "original_temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "delay(10 MIN)\n"
        "temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "if (temp >= original_temp + 1 or temp <= original_temp - 1) {\n"
        '  (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")\n'
        "}",
        "originalTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "delay(10 MIN)\n"
        "newTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "diff = newTemp - originalTemp\n"
        "if (diff >= 1 or diff <= -1) {\n"
        '  (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")\n'
        "}",
    )

    _assert_det_equivalent(result)


def test_snapshot_delta_report_requires_same_threshold() -> None:
    result = _evaluate(
        "original_temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "delay(10 MIN)\n"
        "temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "if (temp >= original_temp + 1 or temp <= original_temp - 1) {\n"
        '  (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")\n'
        "}",
        "originalTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "delay(10 MIN)\n"
        "newTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "diff = newTemp - originalTemp\n"
        "if (diff >= 2 or diff <= -2) {\n"
        '  (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")\n'
        "}",
    )

    _assert_not_det_equivalent(result)


def test_dataflow_accepts_sensor_assignment_variable_used_in_condition_without_exact_algebra() -> None:
    result = _evaluate(
        "original_temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "delay(10 MIN)\n"
        "temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "if (temp >= original_temp + 1 or temp <= original_temp - 1) {\n"
        '  (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")\n'
        "}",
        "originalTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "delay(10 MIN)\n"
        "newTemp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature\n"
        "if ((newTemp >= originalTemp + 1) or (newTemp <= originalTemp - 1)) {\n"
        '  (#Speaker).speaker_speak("와인셀러의 온도가 급변했습니다")\n'
        "}",
    )

    assert result["det_dataflow_score"] == 1.0
    assert "dataflow" not in result["failure_reasons"]
    assert result["det_score"] >= 70.0


def test_numeric_grounding_treats_integer_and_dot_zero_as_same_value() -> None:
    result = evaluate_candidate(
        "When the brightness falls below 100 lux, turn on the light.",
        {
            "name": "Candidate",
            "cron": "",
            "period": 0,
            "code": "wait until ((#LightSensor).lightsensor_brightness < 100.0)\n(#Light).switch_on()",
        },
        SERVICE_SCHEMA,
        ground_truth={
            "name": "GroundTruth",
            "cron": "",
            "period": 0,
            "code": "wait until ((#LightSensor).lightsensor_brightness < 100)\n(#Light).switch_on()",
        },
        profile="strict",
    )

    assert result["det_numeric_grounding"] == 1.0
    assert "numeric_grounding" not in result["failure_reasons"]
