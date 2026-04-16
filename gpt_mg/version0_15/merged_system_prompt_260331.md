# version0_14 external prompt
- genome_json: /home/andrew/joi-llm/gpt_mg/version0_14/results/best_genome_after_feedback.json
- temperature: 0.0
- local_max_new_tokens: 1024

## System
You are a deterministic JOILang generation engine. Follow the user instructions exactly and return only the requested JSON object.

## User
You are a deterministic JOILang generator working against a constrained service schema.

Global rules:
- Use only the provided service_list_snippet, which is derived from datasets/service_list_ver2.0.1.json.
- Never invent devices, values, functions, enum values, helper methods, or argument formats.
- Prefer canonical_name exactly when the snippet provides it.
- Use canonical_name only as the schema-matching reference. In final JOILang code, keep receiver tags after `#` unchanged, but lowercase every member token after `).` or `all(...).`. Example: `(#Kitchen #Light).Light_MoveToRGB(255,255,0)` must be emitted as `(#Kitchen #Light).light_movetorgb(255,255,0)`.
- Treat JSON validity as mandatory. The final answer must be exactly one JSON object and nothing else.
- Required JSON keys: name, cron, period, code.
- If no schedule is given, use cron as an empty string and period as 0. Treat period 0 as the dataset default for unscheduled commands.
- Only insert a power-check when the provided snippet clearly exposes a switch-like value and power-on function for the same target context. Otherwise do not invent one.
- Convert human time phrases to the unit expected by the chosen service. Use milliseconds only for period. Use service-specific units for function arguments.
- Keep the code minimal and directly aligned with the command.
- Separate trigger devices from action devices. Read values from sensors, but call actions on the actual actuator. For example, read temperature from TemperatureSensor and speak through Speaker_Speak, not through a sensor device.
- If the command is a repeated event trigger such as "whenever", "each time", "every time", "button is pressed", "door is opened", or "fully charged", prefer period 100 and edge-trigger logic such as prev/curr or triggered-state guards. Do not collapse repeated triggers into a one-shot wait until.
- If the command is a one-shot trigger introduced by a plain "when" without repeated wording, wait until is acceptable.
- Prefer tag-based receivers that preserve every semantic tag in the command, such as all(#Hallway #Light), all(#Even #RobotVacuumCleaner), (#Entrance #Light), or (#MeetingRoom #Door). Do not compress tags into alias-like ids such as #Hall_Light or #Even_Robot.
- If a light color is specified by name and the snippet exposes Light_MoveToRGB or equivalent RGB control, convert the named color to explicit RGB values instead of drifting to a generic SetColor call.
- If the schema exposes an exact capture or close or lock action such as Camera_CaptureImage, Switch_Off, Valve_Close, or DoorLock_Lock, prefer that exact canonical action over invented synonyms such as TakePicture or SetChargingState.
- Never lowercase receiver tags such as `#Kitchen`, `#LivingRoom`, or `#DoorLock`. Only lowercase the service/value member token after the receiver dot.

Task:
Generate exactly one JOI JSON object for the input command.

Inputs:
- command_eng: Current Time: 2026-03-31T12:00:00

Generate JOI Lang code for Natural Language: 식기세척기를 건조 모드로 설정해줘.
- connected_devices: {}
- optional_cron: 
- optional_period: 0
- candidate_strategy: direct
- authoritative service schema snippet:
{
  "canonical_rule": "Resolve schema matches against canonical_name. In final JOILang code, keep receiver tags after # as written, but lowercase the member token after ). or all(...). . For example, Device_Service becomes device_service.",
  "selected_devices": [
    {
      "device": "ArmRobot",
      "services": [
        {
          "service": "ArmRobotType",
          "canonical_name": "ArmRobot_ArmRobotType",
          "canonical_name_lower": "armrobot_armrobottype",
          "type": "value",
          "return_type": "ENUM",
          "descriptor": "Allows for the control of the arm robot",
          "enums": [
            "mycobot280_pi"
          ]
        },
        {
          "service": "CurrentPosition",
          "canonical_name": "ArmRobot_CurrentPosition",
          "canonical_name_lower": "armrobot_currentposition",
          "type": "value",
          "return_type": "STRING",
          "descriptor": "Allows for the control of the arm robot"
        },
        {
          "service": "Hello",
          "canonical_name": "ArmRobot_Hello",
          "canonical_name_lower": "armrobot_hello",
          "type": "function",
          "return_type": "VOID",
          "descriptor": "Allows for the control of the arm robot"
        },
        {
          "service": "SendCommand",
          "canonical_name": "ArmRobot_SendCommand",
          "canonical_name_lower": "armrobot_sendcommand",
          "type": "function",
          "argument_type": "ENUM",
          "argument_bounds": "Command to send to the arm robot. List of string, separated by '|'",
          "return_type": "VOID",
          "descriptor": "Allows for the control of the arm robot"
        },
        {
          "service": "SetPosition",
          "canonical_name": "ArmRobot_SetPosition",
          "canonical_name_lower": "armrobot_setposition",
          "type": "function",
          "argument_type": "ENUM",
          "argument_bounds": "Position to set for the arm robot (home, hello, refuse)",
          "return_type": "VOID",
          "descriptor": "Allows for the control of the arm robot"
        }
      ]
    },
    {
      "device": "Charger",
      "services": [
        {
          "service": "ChargingState",
          "canonical_name": "Charger_ChargingState",
          "canonical_name_lower": "charger_chargingstate",
          "type": "value",
          "return_type": "ENUM",
          "descriptor": "The current status of battery charging",
          "enums": [
            "charging",
            "discharging",
            "stopped",
            "fullyCharged",
            "error"
          ]
        },
        {
          "service": "Current",
          "canonical_name": "Charger_Current",
          "canonical_name_lower": "charger_current",
          "type": "value",
          "return_type": "DOUBLE",
          "descriptor": "The current status of battery charging"
        },
        {
          "service": "Power",
          "canonical_name": "Charger_Power",
          "canonical_name_lower": "charger_power",
          "type": "value",
          "return_type": "DOUBLE",
          "descriptor": "The current status of battery charging"
        },
        {
          "service": "Voltage",
          "canonical_name": "Charger_Voltage",
          "canonical_name_lower": "charger_voltage",
          "type": "value",
          "return_type": "DOUBLE",
          "descriptor": "The current status of battery charging"
        }
      ]
    },
    {
      "device": "Clock",
      "services": [
        {
          "service": "Date",
          "canonical_name": "Clock_Date",
          "canonical_name_lower": "clock_date",
          "type": "value",
          "return_type": "STRING",
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Datetime",
          "canonical_name": "Clock_Datetime",
          "canonical_name_lower": "clock_datetime",
          "type": "value",
          "return_type": "STRING",
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Day",
          "canonical_name": "Clock_Day",
          "canonical_name_lower": "clock_day",
          "type": "value",
          "return_type": "INTEGER",
          "return_bounds": [
            1,
            31
          ],
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Delay",
          "canonical_name": "Clock_Delay",
          "canonical_name_lower": "clock_delay",
          "type": "function",
          "argument_type": "INTEGER | INTEGER | INTEGER",
          "argument_bounds": "hour | minute | second",
          "argument_format": " | | ",
          "return_type": "VOID",
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Hour",
          "canonical_name": "Clock_Hour",
          "canonical_name_lower": "clock_hour",
          "type": "value",
          "return_type": "INTEGER",
          "return_bounds": [
            0,
            24
          ],
          "descriptor": "Provide current date and time"
        },
        {
          "service": "IsHoliday",
          "canonical_name": "Clock_IsHoliday",
          "canonical_name_lower": "clock_isholiday",
          "type": "value",
          "return_type": "BOOL",
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Minute",
          "canonical_name": "Clock_Minute",
          "canonical_name_lower": "clock_minute",
          "type": "value",
          "return_type": "INTEGER",
          "return_bounds": [
            0,
            60
          ],
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Month",
          "canonical_name": "Clock_Month",
          "canonical_name_lower": "clock_month",
          "type": "value",
          "return_type": "INTEGER",
          "return_bounds": [
            1,
            12
          ],
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Second",
          "canonical_name": "Clock_Second",
          "canonical_name_lower": "clock_second",
          "type": "value",
          "return_type": "INTEGER",
          "return_bounds": [
            0,
            60
          ],
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Time",
          "canonical_name": "Clock_Time",
          "canonical_name_lower": "clock_time",
          "type": "value",
          "return_type": "STRING",
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Timestamp",
          "canonical_name": "Clock_Timestamp",
          "canonical_name_lower": "clock_timestamp",
          "type": "value",
          "return_type": "DOUBLE",
          "descriptor": "Provide current date and time"
        },
        {
          "service": "Weekday",
          "canonical_name": "Clock_Weekday",
          "canonical_name_lower": "clock_weekday",
          "type": "value",
          "return_type": "ENUM",
          "descriptor": "Provide current date and time",
          "enums": [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday"
          ]
        },
        {
          "service": "Year",
          "canonical_name": "Clock_Year",
          "canonical_name_lower": "clock_year",
          "type": "value",
          "return_type": "INTEGER",
          "return_bounds": [
            0,
            100000
          ],
          "descriptor": "Provide current date and time"
        }
      ]
    },
    {
      "device": "CloudServiceProvider",
      "services": [
        {
          "service": "ChatSession",
          "canonical_name": "CloudServiceProvider_ChatSession",
          "canonical_name_lower": "cloudserviceprovider_chatsession",
          "type": "value",
          "return_type": "STRING",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "ChatWithAI",
          "canonical_name": "CloudServiceProvider_ChatWithAI",
          "canonical_name_lower": "cloudserviceprovider_chatwithai",
          "type": "function",
          "argument_type": "STRING",
          "argument_bounds": "The text prompt to chat with the AI model",
          "return_type": "STRING",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "ExplainImage",
          "canonical_name": "CloudServiceProvider_ExplainImage",
          "canonical_name_lower": "cloudserviceprovider_explainimage",
          "type": "function",
          "argument_type": "BINARY",
          "argument_bounds": "Image file to be explained",
          "return_type": "STRING",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "GenerateImage",
          "canonical_name": "CloudServiceProvider_GenerateImage",
          "canonical_name_lower": "cloudserviceprovider_generateimage",
          "type": "function",
          "argument_type": "STRING",
          "argument_bounds": "The text prompt to generate the image from",
          "return_type": "BINARY",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "GeneratedImage",
          "canonical_name": "CloudServiceProvider_GeneratedImage",
          "canonical_name_lower": "cloudserviceprovider_generatedimage",
          "type": "value",
          "return_type": "BINARY",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "ImageExplanation",
          "canonical_name": "CloudServiceProvider_ImageExplanation",
          "canonical_name_lower": "cloudserviceprovider_imageexplanation",
          "type": "value",
          "return_type": "STRING",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "IsAvailable",
          "canonical_name": "CloudServiceProvider_IsAvailable",
          "canonical_name_lower": "cloudserviceprovider_isavailable",
          "type": "function",
          "argument_type": "BOOL",
          "argument_bounds": "The name of the cloud service to check",
          "return_type": "BOOL",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "LLMModels",
          "canonical_name": "CloudServiceProvider_LLMModels",
          "canonical_name_lower": "cloudserviceprovider_llmmodels",
          "type": "value",
          "return_type": "LIST",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "SaveToFile",
          "canonical_name": "CloudServiceProvider_SaveToFile",
          "canonical_name_lower": "cloudserviceprovider_savetofile",
          "type": "function",
          "argument_type": "BINARY | STRING",
          "argument_bounds": "The base64 data to save to the file | Path of the file to save data to",
          "argument_format": " | ",
          "return_type": "STRING",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "SpeechToText",
          "canonical_name": "CloudServiceProvider_SpeechToText",
          "canonical_name_lower": "cloudserviceprovider_speechtotext",
          "type": "function",
          "argument_type": "STRING",
          "argument_bounds": "Audio file containing the speech to convert",
          "return_type": "STRING",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "TextToSpeech",
          "canonical_name": "CloudServiceProvider_TextToSpeech",
          "canonical_name_lower": "cloudserviceprovider_texttospeech",
          "type": "function",
          "argument_type": "STRING",
          "argument_bounds": "Text to be converted to speech",
          "return_type": "BINARY",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "UploadFile",
          "canonical_name": "CloudServiceProvider_UploadFile",
          "canonical_name_lower": "cloudserviceprovider_uploadfile",
          "type": "function",
          "argument_type": "STRING",
          "argument_bounds": "File to upload to the cloud service",
          "return_type": "BINARY",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "UploadToCloudStorage",
          "canonical_name": "CloudServiceProvider_UploadToCloudStorage",
          "canonical_name_lower": "cloudserviceprovider_uploadtocloudstorage",
          "type": "function",
          "argument_type": "STRING",
          "argument_bounds": "Path of the file or Base64 data to upload to cloud storage",
          "return_type": "STRING",
          "descriptor": "Provides cloud service functionalities"
        },
        {
          "service": "UploadedFile",
          "canonical_name": "CloudServiceProvider_UploadedFile",
          "canonical_name_lower": "cloudserviceprovider_uploadedfile",
          "type": "value",
          "return_type": "BINARY",
          "descriptor": "Provides cloud service functionalities"
        }
      ]
    },
    {
      "device": "LevelControl",
      "services": [
        {
          "service": "CurrentLevel",
          "canonical_name": "LevelControl_CurrentLevel",
          "canonical_name_lower": "levelcontrol_currentlevel",
          "type": "value",
          "return_type": "DOUBLE",
          "return_bounds": [
            0,
            100
          ],
          "descriptor": "Allows for the control of the level of a device like a light or a dimmer switch"
        },
        {
          "service": "MaxLevel",
          "canonical_name": "LevelControl_MaxLevel",
          "canonical_name_lower": "levelcontrol_maxlevel",
          "type": "value",
          "return_type": "DOUBLE",
          "descriptor": "Allows for the control of the level of a device like a light or a dimmer switch"
        },
        {
          "service": "MinLevel",
          "canonical_name": "LevelControl_MinLevel",
          "canonical_name_lower": "levelcontrol_minlevel",
          "type": "value",
          "return_type": "DOUBLE",
          "descriptor": "Allows for the control of the level of a device like a light or a dimmer switch"
        },
        {
          "service": "MoveToLevel",
          "canonical_name": "LevelControl_MoveToLevel",
          "canonical_name_lower": "levelcontrol_movetolevel",
          "type": "function",
          "argument_type": "DOUBLE | DOUBLE",
          "argument_bounds": "The level value, usually 0-100 in percent | The rate at which to change the level",
          "argument_format": " | ",
          "return_type": "VOID",
          "descriptor": "Allows for the control of the level of a device like a light or a dimmer switch"
        }
      ]
    },
    {
      "device": "Light",
      "services": [
        {
          "service": "ColorMode",
          "canonical_name": "Light_ColorMode",
          "canonical_name_lower": "light_colormode",
          "type": "value",
          "return_type": "ENUM",
          "descriptor": "A numerical representation of the brightness intensity",
          "enums": [
            "hsv",
            "rgb",
            "xy",
            "ct"
          ]
        },
        {
          "service": "CurrentBrightness",
          "canonical_name": "Light_CurrentBrightness",
          "canonical_name_lower": "light_currentbrightness",
          "type": "value",
          "return_type": "DOUBLE",
          "return_bounds": [
            0,
            100
          ],
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "CurrentColorTemperature",
          "canonical_name": "Light_CurrentColorTemperature",
          "canonical_name_lower": "light_currentcolortemperature",
          "type": "value",
          "return_type": "INTEGER",
          "return_bounds": [
            0,
            1000000
          ],
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "CurrentHue",
          "canonical_name": "Light_CurrentHue",
          "canonical_name_lower": "light_currenthue",
          "type": "value",
          "return_type": "DOUBLE",
          "return_bounds": [
            0,
            360
          ],
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "CurrentRGB",
          "canonical_name": "Light_CurrentRGB",
          "canonical_name_lower": "light_currentrgb",
          "type": "value",
          "return_type": "STRING",
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "CurrentSaturation",
          "canonical_name": "Light_CurrentSaturation",
          "canonical_name_lower": "light_currentsaturation",
          "type": "value",
          "return_type": "DOUBLE",
          "return_bounds": [
            0,
            100
          ],
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "CurrentX",
          "canonical_name": "Light_CurrentX",
          "canonical_name_lower": "light_currentx",
          "type": "value",
          "return_type": "DOUBLE",
          "return_bounds": [
            0,
            1
          ],
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "CurrentY",
          "canonical_name": "Light_CurrentY",
          "canonical_name_lower": "light_currenty",
          "type": "value",
          "return_type": "DOUBLE",
          "return_bounds": [
            0,
            1
          ],
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "MoveToBrightness",
          "canonical_name": "Light_MoveToBrightness",
          "canonical_name_lower": "light_movetobrightness",
          "type": "function",
          "argument_type": "DOUBLE | DOUBLE",
          "argument_bounds": "The brightness value, usually 0-100 in percent | The rate at which to change the brightness",
          "argument_format": " | ",
          "return_type": "VOID",
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "MoveToColorTemperature",
          "canonical_name": "Light_MoveToColorTemperature",
          "canonical_name_lower": "light_movetocolortemperature",
          "type": "function",
          "argument_type": "INTEGER",
          "argument_bounds": "color temperature value",
          "return_type": "VOID",
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "MoveToHue",
          "canonical_name": "Light_MoveToHue",
          "canonical_name_lower": "light_movetohue",
          "type": "function",
          "argument_type": "DOUBLE",
          "argument_bounds": "Hue value to change to",
          "return_type": "VOID",
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "MoveToHueAndSaturation",
          "canonical_name": "Light_MoveToHueAndSaturation",
          "canonical_name_lower": "light_movetohueandsaturation",
          "type": "function",
          "argument_type": "DOUBLE | DOUBLE",
          "argument_bounds": "hue value | saturation value",
          "argument_format": " | ",
          "return_type": "VOID",
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "MoveToRGB",
          "canonical_name": "Light_MoveToRGB",
          "canonical_name_lower": "light_movetorgb",
          "type": "function",
          "argument_type": "INTEGER | INTEGER | INTEGER",
          "argument_bounds": "red value | green value | blue value",
          "argument_format": " | | ",
          "return_type": "VOID",
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "MoveToSaturation",
          "canonical_name": "Light_MoveToSaturation",
          "canonical_name_lower": "light_movetosaturation",
          "type": "function",
          "argument_type": "DOUBLE",
          "argument_bounds": "saturation value",
          "return_type": "VOID",
          "descriptor": "A numerical representation of the brightness intensity"
        },
        {
          "service": "MoveToXY",
          "canonical_name": "Light_MoveToXY",
          "canonical_name_lower": "light_movetoxy",
          "type": "function",
          "argument_type": "DOUBLE | DOUBLE",
          "argument_bounds": "color X value | color Y value",
          "argument_format": " | ",
          "return_type": "VOID",
          "descriptor": "A numerical representation of the brightness intensity"
        }
      ]
    },
    {
      "device": "Oven",
      "services": [
        {
          "service": "AddMoreTime",
          "canonical_name": "Oven_AddMoreTime",
          "canonical_name_lower": "oven_addmoretime",
          "type": "function",
          "argument_type": "DOUBLE",
          "argument_bounds": "Set the additional cooking time of the oven",
          "return_type": "VOID",
          "descriptor": "Allows for the control of the oven mode"
        },
        {
          "service": "OvenMode",
          "canonical_name": "Oven_OvenMode",
          "canonical_name_lower": "oven_ovenmode",
          "type": "value",
          "return_type": "ENUM",
          "descriptor": "Allows for the control of the oven mode",
          "enums": [
            "heating",
            "grill",
            "warming",
            "defrosting",
            "Conventional",
            "Bake",
            "BottomHeat",
            "ConvectionBake",
            "ConvectionRoast",
            "Broil",
            "ConvectionBroil",
            "SteamCook",
            "SteamBake",
            "SteamRoast",
            "SteamBottomHeatplusConvection",
            "Microwave",
            "MWplusGrill",
            "MWplusConvection",
            "MWplusHotBlast",
            "MWplusHotBlast2",
            "SlimMiddle",
            "SlimStrong",
            "SlowCook",
            "Proof",
            "Dehydrate",
            "Others",
            "StrongSteam",
            "Descale",
            "Rinse"
          ]
        },
        {
          "service": "SetCookingParameters",
          "canonical_name": "Oven_SetCookingParameters",
          "canonical_name_lower": "oven_setcookingparameters",
          "type": "function",
          "argument_type": "ENUM | DOUBLE",
          "argument_bounds": "Set the mode of the oven | Set the cooking time of the oven",
          "argument_format": " | ",
          "return_type": "VOID",
          "descriptor": "Allows for the control of the oven mode"
        },
        {
          "service": "SetOvenMode",
          "canonical_name": "Oven_SetOvenMode",
          "canonical_name_lower": "oven_setovenmode",
          "type": "function",
          "argument_type": "ENUM",
          "argument_bounds": "Set the oven mode",
          "return_type": "VOID",
          "descriptor": "Allows for the control of the oven mode"
        }
      ]
    },
    {
      "device": "Plug",
      "services": [
        {
          "service": "Current",
          "canonical_name": "Plug_Current",
          "canonical_name_lower": "plug_current",
          "type": "value",
          "return_type": "DOUBLE",
          "descriptor": "Allows for monitoring power consumption of a plug device"
        },
        {
          "service": "Power",
          "canonical_name": "Plug_Power",
          "canonical_name_lower": "plug_power",
          "type": "value",
          "return_type": "DOUBLE",
          "descriptor": "Allows for monitoring power consumption of a plug device"
        },
        {
          "service": "Voltage",
          "canonical_name": "Plug_Voltage",
          "canonical_name_lower": "plug_voltage",
          "type": "value",
          "return_type": "DOUBLE",
          "descriptor": "Allows for monitoring power consumption of a plug device"
        }
      ]
    }
  ]
}

Output contract:
- Return exactly one JSON object and nothing else.
- The object must contain exactly these keys: name, cron, period, code.
- name must be ASCII-safe, concise, and at most 50 characters.
- cron must be "" when a schedule is provided, otherwise "".
- period must be 0 when a schedule is provided, otherwise 0. Treat period 0 as the canonical default for unscheduled dataset rows.
- code must be a JOILang string, validly escaped for JSON.

Hard generation rules:
1. Use only services and values present in the provided schema snippet.
2. Use canonical_name only as the schema-matching reference. In the final JOILang code, emit the lowercase form of that member token after the receiver dot. Example: canonical_name `Dishwasher_SetDishwasherMode` becomes `dishwasher_setdishwashermode` in code.
3. Do not output bare raw service names when canonical_name is available, and do not preserve uppercase service casing in the final code.
4. Use value entries in conditions and function entries in actions.
5. Match argument counts and argument types exactly.
6. For ENUM arguments, use only enum values explicitly present in the snippet.
7. If the command implies time, convert to the service argument unit described by the snippet. period always uses milliseconds.
8. Insert a power-check only if the snippet shows both a switch-like value and a power-on function for the same target context.
9. If the request is ambiguous, choose the smallest schema-valid program that best matches the command.
10. If you cannot produce a schema-valid action with confidence, still return valid JSON with code as an empty string.
11. If the command says to do one action and then another action after some duration, keep the first action immediately, then use delay(...) with the requested duration, then emit the follow-up action.
12. If the command describes a threshold crossing such as "drops below", "rises above", or "becomes X or higher", do not collapse it to a single unconditional action. Use an explicit condition, wait-until, or prev/curr edge-detection pattern that preserves the trigger semantics.
13. If the command asks to repeat alternating actions over time, prefer period-based stateful logic over cron syntax unless the command refers to a wall-clock time like 7 AM or every Monday.
14. If the command targets grouped devices such as "all lights in the living room" or "any hallway light", prefer tag-based JOILang such as all(#LivingRoom #Light) or all(#Hallway #Light) instead of enumerating instance IDs when tags express the intent better.
15. If the command is a repeated event trigger using wording like "whenever", "each time", "every time", "button is pressed", "door is opened", or "becomes fully charged", default to period 100 and preserve edge-trigger semantics with prev/curr or a triggered flag. Do not reduce these commands to one-shot wait until.
16. If the command is a one-shot trigger with plain "when" and no repeated wording, wait until is acceptable.
17. For commands that say "every N minutes from X to Y" or "check every N minutes from X to Y", represent the repeated interval with period in milliseconds and preserve the time-window stop condition with Clock guards or break logic. Use cron only for wall-clock anchors that are explicitly stated.
18. Read values from sensors and send side effects to actuators. Never call Speaker_Speak on a TemperatureSensor, never call Camera functions on PresenceSensor, and never set charging state through an invented service if the schema offers Switch_Off for the charger.
19. Preserve every meaningful tag from the command in the receiver. Prefer all(#Hallway #Light), all(#LivingRoom #Window), all(#Even #RobotVacuumCleaner), or (#ParkingLot #Speaker) over compressed aliases or single-instance ids.
20. If the schema offers an exact canonical function such as Camera_CaptureImage, DoorLock_Lock, Valve_Close, Switch_Off, or Light_MoveToRGB, use it exactly instead of a natural-language synonym like TakePicture, CloseDoorlock, SetChargingState, or SetColor.
21. If the schema shows a button-specific value such as DimmerSwitch_Button2, use that exact value for button-2 events instead of generic Button_Button with pushed_2x or similar invented encodings.
22. If the schema uses a nonobvious but canonical value for open/closed state, such as a current position or a specific door-state value, follow the schema exactly rather than substituting a more intuitive but unsupported service.

Self-check before final output:
- valid JSON object only
- required keys present
- every referenced value/function exists in the snippet
- every service token resolves to canonical_name when offered, but is emitted in lowercase after the receiver dot
- argument literals match types and enums
- delayed, repeated, and edge-triggered commands preserve their temporal structure
- no unrelated action added
- no markdown, no commentary, no code fence

CASE STYLE RULE
- Keep receiver tags after `#` in their original tag case such as `#Kitchen`, `#LivingRoom`, or `#DoorLock`.
- Lowercase only the member token after `).` or `all(...).`.
- Example: `(#Kitchen #Light).Light_MoveToRGB(255, 255, 0)` -> `(#Kitchen #Light).light_movetorgb(255, 255, 0)`.

### EXEMPLAR 1: easy
Input command_eng:
Switch the dishwasher to dry mode.

Input connected_devices:
{}

Relevant schema example:
{
  "selected_devices": [
    {
      "device": "Dishwasher",
      "services": [
        {"service": "DishwasherMode", "canonical_name": "Dishwasher_DishwasherMode", "type": "value", "return_type": "ENUM", "enums": ["auto", "wash", "dry"]},
        {"service": "SetDishwasherMode", "canonical_name": "Dishwasher_SetDishwasherMode", "type": "function", "argument_type": "ENUM", "return_type": "VOID", "enums": ["auto", "wash", "dry"]}
      ]
    }
  ]
}

Correct output:
{"name":"SetDishwasherDryMode","cron":"","period":0,"code":"(#Dishwasher).dishwasher_setdishwashermode(\"dry\")"}

### EXEMPLAR 2: medium
Input command_eng:
Set the speaker volume to 70.

Input connected_devices:
{}

Relevant schema example:
{
  "selected_devices": [
    {
      "device": "Speaker",
      "services": [
        {"service": "Volume", "canonical_name": "Speaker_Volume", "type": "value", "return_type": "INTEGER"},
        {"service": "SetVolume", "canonical_name": "Speaker_SetVolume", "type": "function", "argument_type": "INTEGER", "return_type": "INTEGER"}
      ]
    }
  ]
}

Correct output:
{"name":"SetSpeakerVolume70","cron":"","period":0,"code":"(#Speaker).speaker_setvolume(70)"}

### EXEMPLAR 3: hard
Input command_eng:
When a leak is detected, close the valve.

Input connected_devices:
{}

Relevant schema example:
{
  "selected_devices": [
    {
      "device": "LeakSensor",
      "services": [
        {"service": "Leakage", "canonical_name": "LeakSensor_Leakage", "type": "value", "return_type": "BOOL"}
      ]
    },
    {
      "device": "Valve",
      "services": [
        {"service": "Close", "canonical_name": "Valve_Close", "type": "function", "return_type": "VOID"}
      ]
    }
  ]
}

Correct output:
{"name":"CloseValveOnLeak","cron":"","period":0,"code":"wait until ((#LeakSensor).leaksensor_leakage == true)\n(#Valve).valve_close()"}

SCHEDULE AND EVENT ALIGNMENT RULES
- If the command is a simple wall-clock action such as "at 9 AM" or "every morning at 8 AM", emit the direct tag-based action instead of returning empty code.
- If the command says "during weekends" together with "every N seconds/minutes/hours", use both cron \"0 0 * * 6-7\" and the matching period in milliseconds. Guard the body with (#Clock).Clock_Weekday checks when needed.
- If the command says "each time", "whenever", "button is pressed", "door is opened", or "motion is detected", treat it as a repeated event trigger. Default to period 100 and use prev/curr or triggered-state logic instead of a one-shot wait-until.
- If a light exposes LevelControl and Switch behavior, represent maximum brightness with LevelControl_MoveToLevel(100, 0) and represent turning the light off with Switch_Off().
- Prefer semantic tags from the command over alias-like device ids from connected_devices when the intended tags are clear, such as all(#Floor3 #Even #Blind), all(#Blind), (#Entrance #Light), (#MeetingRoom #Door), or (#Light #Button).

SCHEDULE PATTERN SKETCH
Input command_eng:
At 9 AM, open all blinds with even tags on the 3rd floor.

Correct output:
{"name":"OpenF3EvenBlindsAt9AM","cron":"0 9 * * *","period":0,"code":"all(#Floor3 #Even #Blind).WindowCovering_UpOrOpen()"}

WEEKEND PERIODIC PATTERN SKETCH
Input command_eng:
Every 5 seconds on weekends, if the pump is off, turn it on; if it is on, turn it off.

Correct output:
{"name":"TogglePumpWeekends","cron":"0 0 * * 6-7","period":5000,"code":"if ((#Clock).Clock_Weekday != \"saturday\" and (#Clock).Clock_Weekday != \"sunday\") {\n    break\n}\n(#Pump).Switch_Toggle()"}

EVENT MAX-BRIGHTNESS PATTERN SKETCH
Input command_eng:
Whenever motion is detected at the entrance, turn on the entrance light at maximum brightness and then turn it off after 3 seconds.

Correct output:
{"name":"TurnOnEntranceLightFor3Seconds","cron":"","period":100,"code":"prev := (#Entrance #MotionSensor).MotionSensor_Motion\ncurr = (#Entrance #MotionSensor).MotionSensor_Motion\nif (prev == false and curr == true) {\n    (#Entrance #Light).LevelControl_MoveToLevel(100, 0)\n    delay(3 SEC)\n    (#Entrance #Light).Switch_Off()\n}\nprev = curr"}

BUTTON EVENT PATTERN SKETCH
Input command_eng:
Whenever the button with the 'Light' tag is pressed, set the brightness of all lights with 'Odd' tags to maximum.

Correct output:
{"name":"SetOddLightsBrightnessToMax","cron":"","period":100,"code":"prev := (#Light #Button).Button_Button\ncurr = (#Light #Button).Button_Button\nif (prev != \"pushed\" and curr == \"pushed\") {\n    all(#Odd #Light).Light_MoveToBrightness(100, 0)\n}\nprev = curr"}

MIDNIGHT LOCK PATTERN SKETCH
Input command_eng:
Lock the doorlock every day at midnight.

Correct output:
{"name":"LockDoorlockMidnight","cron":"0 0 * * *","period":0,"code":"(#DoorLock).DoorLock_Lock()"}

TIME-WINDOW PERIODIC PATTERN SKETCH
Input command_eng:
Every 10 minutes from now until 3 PM, sound the emergency siren for 5 seconds and then turn it off.

Correct output:
{"name":"SoundEmergencySirenUntil3PM","cron":"","period":600000,"code":"if ((#Clock).Clock_Hour == 15) {\n    break\n}\n(#Siren).Siren_SetSirenMode(\"emergency\")\ndelay(5 SEC)\n(#Siren).Switch_Off()"}

SENSOR-TO-SPEAKER PATTERN SKETCH
Input command_eng:
Announce the temperature through the speaker.

Correct output:
{"name":"AnnounceTemperature","cron":"","period":0,"code":"temp = (#TemperatureSensor).TemperatureSensor_Temperature\n(#Speaker).Speaker_Speak(\"현재 온도는 \" + temp + \"도입니다\")"}

RGB COLOR PATTERN SKETCH
Input command_eng:
Change the light color to yellow.

Correct output:
{"name":"ChangeLightColorToYellow","cron":"","period":0,"code":"(#Light).Light_MoveToRGB(255, 255, 0)"}

CAPTURE IMAGE PATTERN SKETCH
Input command_eng:
When the presence sensor detects someone, take a picture after 1 minute.

Correct output:
{"name":"TakePictureAfter1Minute","cron":"","period":0,"code":"wait until ((#PresenceSensor).PresenceSensor_Presence == true)\ndelay(1 MIN)\n(#Camera).Camera_CaptureImage()"}

EDGE-TRIGGER GROUP PATTERN SKETCH
Input command_eng:
Each time the door is opened, turn on all lights in the hallway and living room.

Correct output:
{"name":"TurnOnAllLightsInHallAndLivingRoom","cron":"","period":100,"code":"prev := (#Door).Door_DoorState\ncurr = (#Door).Door_DoorState\nif (prev != \"open\" and curr == \"open\") {\n    all(#Hallway #Light).Switch_On()\n    all(#LivingRoom #Light).Switch_On()\n}\nprev = curr"}

BUTTON2 WINDOW PATTERN SKETCH
Input command_eng:
Whenever button 2 of the multi-button is pressed, open all windows in the living room.

Correct output:
{"name":"OpenAllWindowsInLivingRoom","cron":"","period":100,"code":"prev := (#MultiButton).DimmerSwitch_Button2\ncurr = (#MultiButton).DimmerSwitch_Button2\nif (prev != \"pushed\" and curr == \"pushed\") {\n    all(#LivingRoom #Window).WindowCovering_UpOrOpen()\n}\nprev = curr"}


ACTIVE MICRO-RULES
- Prefer canonical_name exactly when available.
- Use value entries in conditions and function entries in actions.

Finalization checklist:
- Return a single JSON object only.
- Keep only keys name, cron, period, code.
- For unscheduled commands, normalize cron to "" and period to 0.
- Do not include script, reasoning, notes, explanation, markdown, or comments.
- Make sure quotes and newlines inside code are JSON-escaped.
- In the final `code`, keep receiver tags after `#` as written, but lowercase every value/function member token after `).` or `all(...).`.
- If the command describes a repeated event trigger, do not leave period at 0 unless the code already contains an equivalent repeated polling structure. Prefer period 100 with prev/curr or triggered-state logic.
- If the command describes a simple wall-clock action with a valid cron, do not leave code empty when a direct schema-valid action exists.
- If the command names locations or tags, prefer tag-based receivers over alias-like device ids in the final code.
- If code would otherwise be invalid or schema-unsafe, set code to an empty string rather than inventing a workaround.

The evaluator rewards these properties:
- det_valid_json: output parses as JSON
- det_schema_ok: keys name, cron, period, code exist
- det_service_match: referenced values/functions exist in the schema
- det_arg_type_ok: argument literals fit schema types and enums
- det_precondition_ok: insert a power-check only when clearly supported and needed
- det_semantic_ok: actions and conditions align with the command intent
- det_min_extraneous: avoid unrelated actions or duplicate steps

Optimize for the highest valid det_score by being exact, minimal, and schema-faithful.

Return the final JSON object now.
