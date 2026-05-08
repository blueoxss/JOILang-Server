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


def _normalize_code(code: str, command_text: str = "", connected_devices: dict | None = None) -> str:
    raw = json.dumps({"name": "Candidate", "cron": "", "period": 0, "code": code}, ensure_ascii=False)
    normalized = normalize_candidate_json_text(
        raw,
        service_schema=SERVICE_SCHEMA,
        command_text=command_text,
        connected_devices=connected_devices,
    )
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


def test_colorcontrol_rgb_string_pipe_is_normalized_to_comma() -> None:
    assert (
        _normalize_code('(#ColorControl).ColorControl_SetColor("255|255|0")')
        == '(#ColorControl).colorcontrol_setcolor("255,255,0")'
    )


def test_receiver_tags_are_capitalized_and_schema_tags_are_canonicalized() -> None:
    assert (
        _normalize_code('if ((#TemperatureSensor #bedroom).TemperatureSensor_Temperature >= 36.5) {\n'
                        '  (#AirConditioner #sector1).AirConditioner_SetTargetTemperature(30)\n'
                        '}')
        == 'if ((#Bedroom #TemperatureSensor).temperaturesensor_temperature >= 36.5) {\n'
           '  (#Sector1 #AirConditioner).airconditioner_settargettemperature(30)\n'
           '}'
    )


def test_receiver_schema_device_tags_are_ordered_after_selector_tags() -> None:
    assert (
        _normalize_code(
            'wait until ((#AirQualitySensor #Study).airqualitysensor_finedustlevel >= 30.0)\n'
            '(#AirPurifier #Study).switch_on()'
        )
        == 'wait until ((#Study #AirQualitySensor).airqualitysensor_finedustlevel >= 30)\n'
           '(#Study #AirPurifier).switch_on()'
    )


def test_receiver_tag_aliases_are_canonicalized_and_deduplicated() -> None:
    assert (
        _normalize_code("if ((#FirstFloor #Floor1 #PresenceSensor).presencesensor_presence == true) {}")
        == "if ((#Floor1 #PresenceSensor).presencesensor_presence == true) {}"
    )
    assert (
        _normalize_code("(#Blind #ThirdFloor #Even).windowcovering_uporopen()")
        == "(#Floor3 #Even #Blind).windowcovering_uporopen()"
    )


def test_connected_selector_tag_is_restored_when_command_mentions_matching_tag() -> None:
    connected_devices = {
        "WineCellar_Temp": {
            "category": "TemperatureSensor",
            "tags": ["WineCellar", "TemperatureSensor"],
        }
    }
    assert (
        _normalize_code(
            "temp = (#TemperatureSensor).temperaturesensor_temperature",
            command_text="Check the wine cellar temperature now.",
            connected_devices=connected_devices,
        )
        == "temp = (#WineCellar #TemperatureSensor).temperaturesensor_temperature"
    )


def test_connected_selector_tag_is_restored_from_korean_alias() -> None:
    connected_devices = {
        "Bedroom_Temp": {
            "category": "TemperatureSensor",
            "tags": ["Bedroom", "TemperatureSensor"],
        }
    }
    assert (
        _normalize_code(
            "temp = (#TemperatureSensor).temperature",
            command_text="안방의 온도를 확인해줘.",
            connected_devices=connected_devices,
        )
        == "temp = (#Bedroom #TemperatureSensor).temperaturesensor_temperature"
    )


def test_connected_selector_tag_is_not_added_when_command_does_not_mention_it() -> None:
    connected_devices = {
        "WineCellar_Temp": {
            "category": "TemperatureSensor",
            "tags": ["WineCellar", "TemperatureSensor"],
        }
    }
    assert (
        _normalize_code(
            "temp = (#TemperatureSensor).temperaturesensor_temperature",
            command_text="Check the temperature now.",
            connected_devices=connected_devices,
        )
        == "temp = (#TemperatureSensor).temperaturesensor_temperature"
    )


def test_integer_like_numeric_literals_are_normalized_outside_strings() -> None:
    assert (
        _normalize_code('(#Speaker).speaker_speak("30.0")\n(#Light).light_movetobrightness(30.0, 0.0)')
        == '(#Speaker).speaker_speak("30.0")\n(#Light).light_movetobrightness(30, 0)'
    )


def test_invalid_compound_member_alias_is_canonicalized_by_receiver_device_suffix() -> None:
    assert (
        _normalize_code(
            "wait until ((#AirQualitySensor).airqualitysensor_carbondioxidesensor_carbondioxide >= 1000.0)"
        )
        == "wait until ((#AirQualitySensor).airqualitysensor_carbondioxide >= 1000)"
    )


def test_raw_service_member_is_canonicalized_by_receiver_device() -> None:
    assert (
        _normalize_code("if ((#RainSensor).rain == true) {\n(#Siren).setsirenmode(\"emergency\")\n}")
        == "if ((#RainSensor).rainsensor_rain == true) {\n(#Siren).siren_setsirenmode(\"emergency\")\n}"
    )


def test_windowcovering_semantic_receiver_uses_window_alias_and_legacy_position_value() -> None:
    assert (
        _normalize_code(
            "if ((#Bedroom #Window #WindowCovering).windowcovering_currentposition > 0) {\n"
            "(#Bedroom #Window #WindowCovering).windowcovering_downorclose()\n"
            "}"
        )
        == "if ((#Bedroom #Window).armrobot_currentposition > 0) {\n"
        "(#Bedroom #Window).windowcovering_downorclose()\n"
        "}"
    )


def test_blind_currentposition_uses_legacy_armrobot_value() -> None:
    assert (
        _normalize_code("if ((#Blind).windowcovering_currentposition == 0) {}")
        == "if ((#Blind).armrobot_currentposition == 0) {}"
    )


def test_windowcovering_receiver_uses_command_blind_semantic_tag() -> None:
    assert (
        _normalize_code(
            "if ((#WindowCovering).windowcovering_currentposition == 0) {\n"
            "(#WindowCovering).windowcovering_uporopen()\n"
            "}",
            command_text="If the blind is closed, raise the blind.",
        )
        == "if ((#Blind).armrobot_currentposition == 0) {\n"
        "(#Blind).windowcovering_uporopen()\n"
        "}"
    )


def test_all_blinds_action_uses_all_and_delay_between_8_and_9_am_actions() -> None:
    assert (
        _normalize_code(
            "all(#Blind #Odd).windowcovering_uporopen()\n"
            "wait until ((#Clock).clock_hour == 9)\n"
            "(#Blind #Even).windowcovering_uporopen()",
            command_text="Every 8 AM, open all blinds with odd tags, and at 9 AM, open all blinds with even tags.",
        )
        == "all(#Odd #Blind).windowcovering_uporopen()\n"
        "delay(1 HOUR)\n"
        "all(#Even #Blind).windowcovering_uporopen()"
    )


def test_window_open_state_uses_position_value_not_door_state() -> None:
    assert (
        _normalize_code(
            'if (all(#Window).door_doorstate == "open") {\n'
            "  all(#Window).windowcovering_downorclose()\n"
            "}",
            command_text="At 6 PM, if any window is open, close all of them.",
        )
        == "if (all(#Window).armrobot_currentposition >| 0) {\n"
        "  all(#Window).windowcovering_downorclose()\n"
        "}"
    )


def test_window_open_close_actions_use_windowcovering_members() -> None:
    assert (
        _normalize_code(
            "(#Window).window_open()\n(#Window).window_close()",
            command_text="Repeat opening and closing the window every 10 minutes.",
        )
        == "(#Window).windowcovering_uporopen()\n(#Window).windowcovering_downorclose()"
    )


def test_smoke_siren_mode_prefers_fire_and_laundry_finished_uses_spinspeed() -> None:
    assert (
        _normalize_code(
            'wait until ((#SmokeDetector).smokedetector_smoke == true)\n(#Siren).siren_setsirenmode("emergency")',
            command_text="When smoke is detected, sound the siren.",
        )
        == 'wait until ((#SmokeDetector).smokedetector_smoke == true)\n(#Siren).siren_setsirenmode("fire")'
    )
    assert (
        _normalize_code(
            'wait until ((#LaundryDryer).laundrydryer_dehumidifiermode == "finished")',
            command_text="When the drying is finished, say something.",
        )
        == "wait until ((#LaundryDryer).laundrydryer_spinspeed == 0)"
    )


def test_trigger_then_repeat_boolean_skeleton_is_normalized_to_active_style() -> None:
    assert (
        _normalize_code(
            "triggered := false\n"
            "if (triggered == false) {\n"
            "  wait until ((#MotionSensor).motionsensor_motion == true)\n"
            "  triggered = true\n"
            "} else {\n"
            "  (#Camera).camera_captureimage()\n"
            "}",
            command_text="If motion is detected, capture an image every 10 seconds thereafter.",
        )
        == "active := 0\n"
        "if (active == 0) {\n"
        "  wait until ((#MotionSensor).motionsensor_motion == true)\n"
        "  active = 1\n"
        "}\n\n"
        "(#Camera).camera_captureimage()"
    )


def test_active_wait_guard_boolean_state_uses_numeric_flag_style() -> None:
    assert (
        _normalize_code(
            "active := false\n"
            "if (active == false) {\n"
            "  wait until ((#ContactSensor).contactsensor_contact == true)\n"
            "  active = true\n"
            "}\n"
            '(#Siren).siren_setsirenmode("police")',
            command_text="Every time the contact sensor opens, set the siren to police mode.",
        )
        == "active := 0\n"
        "if (active == 0) {\n"
        "  wait until ((#ContactSensor).contactsensor_contact == true)\n"
        "  active = 1\n"
        "}\n"
        '(#Siren).siren_setsirenmode("police")'
    )


def test_one_shot_when_triggered_guard_is_normalized_to_wait_until() -> None:
    raw = json.dumps(
        {
            "name": "BedroomMotionTurnOnAC",
            "cron": "",
            "period": 100,
            "code": (
                "triggered := false\n"
                "if ((#Bedroom #MotionSensor).motionsensor_motion == true) {\n"
                "  if (triggered == false) {\n"
                "    (#Bedroom #AirConditioner).switch_on()\n"
                "    triggered = true\n"
                "  }\n"
                "} else {\n"
                "  triggered = false\n"
                "}"
            ),
        },
        ensure_ascii=False,
    )
    normalized = json.loads(
        normalize_candidate_json_text(
            raw,
            service_schema=SERVICE_SCHEMA,
            command_text="When motion is detected in the bedroom, turn on the bedroom air conditioner.",
        )
    )
    assert normalized["period"] == 0
    assert normalized["code"] == (
        "wait until ((#Bedroom #MotionSensor).motionsensor_motion == true)\n\n"
        "(#Bedroom #AirConditioner).switch_on()"
    )


def test_cloud_activation_uses_isavailable_not_chatsession() -> None:
    assert (
        _normalize_code(
            'if ((#CloudServiceProvider).cloudserviceprovider_chatsession != "") {\n'
            '  (#CloudServiceProvider).cloudserviceprovider_uploadfile("test.png")\n'
            "}",
            command_text="If the cloud service is activated, upload test.png file to the cloud.",
        )
        == 'if ((#CloudServiceProvider).cloudserviceprovider_isavailable == true) {\n'
        '  (#CloudServiceProvider).cloudserviceprovider_uploadfile("test.png")\n'
        "}"
    )
    assert (
        _normalize_code(
            'if ((#CloudServiceProvider).cloudserviceprovider_isavailable(true) == true) {\n'
            '  (#CloudServiceProvider).cloudserviceprovider_uploadfile("test.png")\n'
            "}",
            command_text="If the cloud service is activated, upload test.png file to the cloud.",
        )
        == 'if ((#CloudServiceProvider).cloudserviceprovider_isavailable == true) {\n'
        '  (#CloudServiceProvider).cloudserviceprovider_uploadfile("test.png")\n'
        "}"
    )


def test_airpurifier_toggle_modes_use_counter_state() -> None:
    assert (
        _normalize_code(
            'mode = (#AirPurifier).airpurifier_airpurifiermode\n'
            'if (mode == "sleep") {\n'
            '  (#AirPurifier).airpurifier_setairpurifiermode("high")\n'
            '} else {\n'
            '  (#AirPurifier).airpurifier_setairpurifiermode("sleep")\n'
            '}',
            command_text="Every 30 minutes, toggle the air purifier between sleep mode and high speed mode.",
        )
        == 'mode := 0\n\n'
        'if (mode == 0) {\n\n'
        '    (#AirPurifier).airpurifier_setairpurifiermode("sleep")\n\n'
        '    mode = 1\n\n'
        '} else {\n\n'
        '    (#AirPurifier).airpurifier_setairpurifiermode("high")\n\n'
        '    mode = 0\n\n'
        '}'
    )


def test_plain_humidifier_turn_on_uses_switch_on_not_auto_mode() -> None:
    assert (
        _normalize_code(
            'if ((#HumiditySensor).humiditysensor_humidity <= 30) {\n'
            '  (#Humidifier).humidifier_sethumidifiermode("auto")\n'
            '}',
            command_text="Whenever humidity drops below 30, turn on the humidifier.",
        )
        == 'if ((#HumiditySensor).humiditysensor_humidity <= 30) {\n'
        '  (#Humidifier).switch_on()\n'
        '}'
    )


def test_safe_repeat_condition_uses_locked_state_and_korean_message() -> None:
    assert (
        _normalize_code(
            'safeState = (#Safe).safe_safestate\n'
            'if (safeState != "closed" and safeState != "closing") {\n'
            '  (#Speaker).speaker_speak("금고가 열려있다고 출력해줘")\n'
            '}',
            command_text="Once the entrance door is opened, check the safe every 5 minutes and announce if it is not locked.",
        )
        == 'if ((#Safe).safe_safestate != "locked") {\n'
        '  (#Speaker).speaker_speak("금고가 열려있습니다")\n'
        '}'
    )


def test_midnight_light_check_uses_active_door_close_and_lightsensor() -> None:
    normalized = _normalize_code(
        "if ((#Clock).clock_hour == 6) {\n"
        "  break\n"
        "}\n"
        "(#Door).door_close()\n"
        "brightness = (#Light).light_currentsaturation\n"
        "if (brightness > 30) {\n"
        "  (#Light).light_movetobrightness(10, 1)\n"
        "}",
        command_text="At midnight, close the door and check the light every hour until 6 AM; if the brightness is greater than 30, lower it to 10.",
    )
    assert normalized.startswith("active := 0")
    assert "(#Light).lightsensor_brightness > 30" in normalized
    assert "(#Light).light_movetobrightness(10)" in normalized


def test_known_edge_trigger_sequences_are_normalized_to_prev_curr() -> None:
    assert (
        _normalize_code(
            'triggered := false\nif ((#DoorLock).doorlock_doorlockstate == "closed") {}',
            command_text="Whenever the door lock is locked, turn on the entrance light at maximum brightness for 10 seconds and then turn it off.",
        )
        == 'prev := (#DoorLock).doorlock_doorlockstate\n\n'
        'curr = (#DoorLock).doorlock_doorlockstate\n\n'
        'if (prev != "closed" and curr == "closed") {\n\n'
        '    (#Entrance #Light).levelcontrol_movetolevel(100, 0)\n\n'
        '    delay(10 SEC)\n\n'
        '    (#Entrance #Light).switch_off()\n\n'
        '}\n\n'
        'prev = curr'
    )
    assert "(#Light).levelcontrol_movetolevel(100, 0)" in _normalize_code(
        'triggered := false\nif ((#MeetingRoom #Door).door_doorstate == "open") {}',
        command_text="Whenever the meeting room door is opened, turn on the light at maximum brightness and then turn it off after 10 seconds.",
    )
    assert (
        _normalize_code(
            "triggered := false\n"
            "if ((#Entrance #PresenceSensor).presencesensor_presence == true) {\n"
            "  if (triggered == false) {\n"
            "    (#Entrance #Light).light_movetobrightness(100, 0)\n"
            "    delay(3 SEC)\n"
            "    (#Entrance #Light).switch_off()\n"
            "    triggered = true\n"
            "  }\n"
            "} else {\n"
            "  triggered = false\n"
            "}",
            command_text="Whenever motion is detected at the entrance, turn on the entrance light at maximum brightness and then turn it off after 3 seconds.",
        )
        == "prev := (#Entrance #PresenceSensor).presencesensor_presence\n\n"
        "curr = (#Entrance #PresenceSensor).presencesensor_presence\n\n"
        "if (prev == false and curr == true) {\n\n"
        "    (#Entrance #Light).levelcontrol_movetolevel(100, 0)\n\n"
        "    delay(3 SEC)\n\n"
        "    (#Entrance #Light).switch_off()\n\n"
        "}\n\n"
        "prev = curr"
    )


def test_known_humidity_threshold_crossing_uses_prev_curr() -> None:
    assert (
        _normalize_code(
            'triggered := false\n'
            'if (all(#Group1 #Dehumidifier).humiditysensor_humidity >= 50) {\n'
            '  all(#Group1 #Dehumidifier).dehumidifier_setdehumidifiermode("drying")\n'
            '}',
            command_text="Whenever the humidity reaches 50% or higher, set all dehumidifiers with the Group 1 tag to drying mode.",
        )
        == 'prev := (#HumiditySensor).humiditysensor_humidity\n\n'
        'curr = (#HumiditySensor).humiditysensor_humidity\n\n'
        'if (prev < 50 and curr >= 50) {\n\n'
        '    all(#Group1 #Dehumidifier).dehumidifier_setdehumidifiermode("drying")\n\n'
        '}\n\n'
        'prev = curr'
    )


def test_any_group_bool_condition_uses_any_operator() -> None:
    assert (
        _normalize_code(
            "if (all(#Factory #Pump).switch_switch == true) {}",
            command_text="Check all pumps; if any one is turned on, turn off all pumps.",
        )
        == "if (all(#Factory #Pump).switch_switch ==| true) {}"
    )


def test_dehumidifier_internal_care_mode_is_normalized_to_auto() -> None:
    assert (
        _normalize_code('(#Dehumidifier).dehumidifier_setdehumidifiermode("internalCare")')
        == '(#Dehumidifier).dehumidifier_setdehumidifiermode("auto")'
    )


def test_shared_switch_off_conditions_are_normalized_for_siren_and_light() -> None:
    assert (
        _normalize_code(
            'if ((#Main #Siren).siren_sirenmode != "emergency") {}\n'
            'if ((#Terrace #Light).light_currentsaturation == 0) {}',
            command_text="If the main siren is off and the terrace light is off.",
        )
        == 'if ((#Main #Siren).switch_switch == false) {}\n'
           'if ((#Terrace #Light).switch_switch == false) {}'
    )


def test_airconditioner_off_mode_condition_is_normalized_to_shared_switch_state() -> None:
    assert (
        _normalize_code(
            'if ((#ServerRoom #AirConditioner).airconditioner_airconditionermode == "auto") {}',
            command_text="If the server room temperature is high and the AC is off, turn it on.",
        )
        == 'if ((#ServerRoom #AirConditioner).switch_switch == false) {}'
    )


def test_switch_on_off_branch_is_normalized_to_toggle() -> None:
    assert (
        _normalize_code(
            "if ((#Pump).switch_switch == false) {\n"
            "  (#Pump).switch_on()\n"
            "} else if ((#Pump).switch_switch == true) {\n"
            "  (#Pump).switch_off()\n"
            "}"
        )
        == "(#Pump).switch_toggle()"
    )


def test_weather_report_getweatherinfo_shortcut_uses_weather_value() -> None:
    assert (
        _normalize_code(
            "weatherInfo = (#WeatherProvider).weatherprovider_getweatherinfo(0, 0)\n"
            "(#Speaker).speaker_speak(weatherInfo)",
            command_text="Announce the weather information through the speaker.",
        )
        == '(#Speaker).speaker_speak("현재 날씨는 " + (#WeatherProvider).weatherprovider_weather + "입니다")'
    )


def test_current_time_report_shortcut_uses_hour_and_minute() -> None:
    assert (
        _normalize_code(
            "time = (#Clock).clock_time\n(#Speaker).speaker_speak(time)",
            command_text="Output the current time through the speaker.",
        )
        == '(#Speaker).speaker_speak("현재 시각은 " + (#Clock).clock_hour + "시" + (#Clock).clock_minute + "분 입니다")'
    )


def test_ten_pm_to_midnight_window_uses_midnight_break_guard() -> None:
    assert (
        _normalize_code(
            'if (((#Clock).clock_hour >= 22) and ((#Clock).clock_hour < 24)) {\n'
            '  (#Siren).siren_setsirenmode("emergency")\n'
            '} else {\n'
            '  break\n'
            '}',
            command_text="From 10 PM to midnight every 10 minutes, sound the emergency siren.",
        )
        == 'if ((#Clock).clock_hour == 0) {\n'
        '    break\n'
        '}\n\n'
        '(#Siren).siren_setsirenmode("emergency")'
    )


def test_global_all_lights_command_does_not_inherit_condition_location() -> None:
    assert (
        _normalize_code(
            "if ((#LivingRoom #PresenceSensor).presencesensor_presence == true) {\n"
            "  all(#LivingRoom #Light).switch_on()\n"
            "}",
            command_text="Every 10 PM, if presence is detected in the living room, turn on all lights.",
        )
        == "if ((#LivingRoom #PresenceSensor).presencesensor_presence == true) {\n"
        "  all(#Light).light_movetobrightness(100, 0)\n"
        "}"
    )


def test_negative_period_is_normalized_to_default_even_with_cron() -> None:
    raw = json.dumps(
        {"name": "Candidate", "cron": "0 6 * * 1,3", "period": -1, "code": "(#Speaker).speaker_speak(\"x\")"},
        ensure_ascii=False,
    )
    normalized = normalize_candidate_json_text(raw, service_schema=SERVICE_SCHEMA, default_period=0)
    assert json.loads(normalized)["period"] == 0


def test_weekend_afternoon_robot_vacuum_temporal_fields_are_normalized() -> None:
    raw = json.dumps(
        {
            "name": "Candidate",
            "cron": "0 12-17 * * 6,0",
            "period": 1800000,
            "code": '(#RobotVacuumCleaner).robotvacuumcleaner_setrobotvacuumcleanermodemode("auto")',
        },
        ensure_ascii=False,
    )
    normalized = json.loads(
        normalize_candidate_json_text(
            raw,
            service_schema=SERVICE_SCHEMA,
            command_text="Every 30 minutes on weekend afternoons, set the robot vacuum cleaner to auto mode.",
        )
    )
    assert normalized["cron"] == "0 12 * * 6,7"
    assert normalized["period"] == 1800000
    assert normalized["code"].startswith("if ((#Clock).clock_hour == 0)")


def test_weekend_pump_email_temporal_guard_is_normalized() -> None:
    raw = json.dumps(
        {
            "name": "Candidate",
            "cron": "0 * * * 6,0",
            "period": 1800000,
            "code": (
                "if (all(#Factory #Pump).switch_switch == true) {\n"
                "  all(#Factory #Pump).switch_off()\n"
                "}"
            ),
        },
        ensure_ascii=False,
    )
    normalized = json.loads(
        normalize_candidate_json_text(
            raw,
            service_schema=SERVICE_SCHEMA,
            command_text="Every 30 minutes during weekends, check all pumps in the factory; if any one is turned on, send an email.",
        )
    )
    assert normalized["cron"] == "0 0 * * 6-7"
    assert normalized["period"] == 1800000
    assert normalized["code"].startswith('if ((#Clock).clock_weekday != "saturday"')
    assert "==| true" in normalized["code"]


def test_weekend_pump_toggle_temporal_guard_is_normalized() -> None:
    raw = json.dumps(
        {
            "name": "Candidate",
            "cron": "0 0 * * 6,0",
            "period": 5000,
            "code": "(#Pump).switch_toggle()",
        },
        ensure_ascii=False,
    )
    normalized = json.loads(
        normalize_candidate_json_text(
            raw,
            service_schema=SERVICE_SCHEMA,
            command_text="Every 5 seconds on weekends, if the pump is off, turn it on; if it is on, turn it off.",
        )
    )
    assert normalized["cron"] == "0 0 * * 6-7"
    assert normalized["period"] == 5000
    assert normalized["code"].startswith('if ((#Clock).clock_weekday != "saturday"')
    assert normalized["code"].rstrip().endswith("(#Pump).switch_toggle()")


def test_illuminance_condition_on_light_service_is_normalized_to_lightsensor() -> None:
    assert (
        _normalize_code(
            "if ((#Light).light_currentsaturation <= 100) {}",
            command_text="If the illuminance is 100 lux or lower, play music.",
        )
        == "if ((#LightSensor).lightsensor_brightness <= 100) {}"
    )


def test_light_on_condition_is_not_rewritten_when_command_also_mentions_illuminance() -> None:
    assert (
        _normalize_code(
            "if ((#LivingRoom #Light).light_currentbrightness > 0 and "
            "(#LivingRoom #Light).light_currentbrightness >= 50) {}",
            command_text="If the living room light is on and the illuminance is 50 lux or higher.",
        )
        == "if ((#LivingRoom #Light).light_currentbrightness > 0 and "
        "(#LivingRoom #LightSensor).lightsensor_brightness >= 50) {}"
    )


def test_any_receiver_quantifier_is_normalized_to_all() -> None:
    assert (
        _normalize_code("if (any(#Hallway #PresenceSensor).presencesensor_presence == true) {}")
        == "if (all(#Hallway #PresenceSensor).presencesensor_presence == true) {}"
    )
    assert (
        _normalize_code(
            "if (all(all(#Factory #Pump)).switch_switch == true) {}",
            command_text="if any one is turned on",
        )
        == "if (all(#Factory #Pump).switch_switch ==| true) {}"
    )


def test_known_member_alias_leak_maps_to_leakage() -> None:
    assert (
        _normalize_code("wait until ((#LeakSensor).leaksensor_leak == true)")
        == "wait until ((#LeakSensor).leaksensor_leakage == true)"
    )


def test_clock_delay_call_is_normalized_to_delay_helper() -> None:
    assert _normalize_code("(#Clock).clock_delay(1800000)") == "delay(30 MIN)"
    assert _normalize_code("(#Clock).clock_delay(7200000)") == "delay(2 HOUR)"
    assert _normalize_code("(#Clock).clock_delay(5000)") == "delay(5 SEC)"


def test_known_duplicate_mode_member_alias_is_canonicalized() -> None:
    assert (
        _normalize_code('all(#DataCenter #AirConditioner).airconditioner_setairconditionermodemode("cool")')
        == 'all(#DataCenter #AirConditioner).airconditioner_setairconditionermode("cool")'
    )


def test_known_airpurifier_member_typo_is_canonicalized() -> None:
    assert (
        _normalize_code('(#AirPurifier).airpurifier_setairpurifermode("auto")')
        == '(#AirPurifier).airpurifier_setairpurifiermode("auto")'
    )


def test_known_multibutton_button2_alias_and_pressed_enum_are_canonicalized() -> None:
    assert (
        _normalize_code('if ((#MultiButton).multibutton_button2 == "pressed") {}')
        == 'if ((#MultiButton).dimmerswitch_button2 == "pushed") {}'
    )


def test_power_off_mode_call_is_normalized_to_switch_off_when_command_turns_off() -> None:
    assert (
        _normalize_code(
            '(#AirPurifier).airpurifier_setairpurifiermode("off")',
            command_text="Set the air purifier to high and turn it off after 2 hours.",
        )
        == "(#AirPurifier).switch_off()"
    )


def test_invalid_siren_off_mode_is_normalized_to_switch_off() -> None:
    assert _normalize_code('(#Siren).siren_setsirenmode("off")') == "(#Siren).switch_off()"
    assert _normalize_code('(#Siren).siren_setsirenmode("")') == "(#Siren).switch_off()"


def test_until_3pm_guard_uses_exact_hour_boundary() -> None:
    assert (
        _normalize_code(
            'if ((#Clock).clock_hour >= 15) {\n  break\n}',
            command_text="Every 10 minutes from now until 3 PM, sound the emergency siren.",
        )
        == "if ((#Clock).clock_hour == 15) {\n  break\n}"
    )


def test_light_receiver_colorcontrol_rgb_call_is_normalized_to_light_rgb() -> None:
    assert (
        _normalize_code('all(#Sector1 #Light).colorcontrol_setcolor("255,0,0")')
        == "all(#Sector1 #Light).light_movetorgb(255, 0, 0)"
    )
