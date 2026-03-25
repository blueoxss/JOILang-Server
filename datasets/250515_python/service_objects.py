from aenum import auto as aauto
from dataclasses import dataclass, field
import textwrap
import sys
from typing import List, Dict, Any, Tuple, Union

from .enum import MXIntEnum, MXStrEnum
from .SkillObjects import (
    Skill,
    SkillValue,
    SkillFunction,
    SkillFunctionArgument,
    MXClassproperty,
    MXValueType,
    MXType,
)

INFINITY = sys.maxsize


@dataclass
class airConditionerMode(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the air conditioner.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • auto - auto
                • cool - cool
                • heat - heat'''
            )

        class airConditionerModeEnum(MXStrEnum):
            auto = aauto()
            cool = aauto()
            heat = aauto()

    class Values:
        @dataclass
        class airConditionerMode(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current mode of the air conditioner'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=airConditionerMode.Enums.airConditionerModeEnum)

        @dataclass
        class targetTemperature(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current temperature status of the air conditioner'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[-470, 10000])

        class supportedAcModes(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Supported states for this air conditioner to be in: "str|..."'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.LIST, format=List[airConditionerMode.Enums.airConditionerModeEnum])

    class Functions:
        @dataclass
        class setAirConditionerMode(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the air conditioner mode'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class mode(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the air conditioner mode'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=airConditionerMode.Enums.airConditionerModeEnum)

        @dataclass
        class setTemperature(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the air conditioner temperature'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class temperature(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the air conditioner temperature'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-460, 10000])


@dataclass
class airPurifierFanMode(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Maintains and sets the state of an air purifier\'s fan'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • auto - The fan is on auto
                • sleep - The fan is in sleep mode to reduce noise
                • low - The fan is on low
                • medium - The fan is on medium
                • high - The fan is on high
                • quiet - The fan is on quiet mode to reduce noise
                • windFree - The fan is on wind free mode to reduce the feeling of cold air
                • off - The fan is off'''
            )

        class airPurifierFanModeEnum(MXStrEnum):
            auto = aauto()
            sleep = aauto()
            low = aauto()
            medium = aauto()
            high = aauto()
            quiet = aauto()
            windFree = aauto()
            off = aauto()

    class Values:
        @dataclass
        class airPurifierFanMode(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current mode of the air purifier fan, an enum of auto, low, medium, high, sleep, quiet or windFree'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=airPurifierFanMode.Enums.airPurifierFanModeEnum)

        class supportedAirPurifierFanModes(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Supported states for this air purifier fan to be in: "str|..."'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.LIST, format=List[airPurifierFanMode.Enums.airPurifierFanModeEnum])

    class Functions:
        @dataclass
        class setAirPurifierFanMode(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the air purifier fan\'s mode'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class mode(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the air purifier fan\'s mode'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=airPurifierFanMode.Enums.airPurifierFanModeEnum)


@dataclass
class audioRecord(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Record audio'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • idle - The audio recorder is idle
                • recording - The audio recorder is recording'''
            )

        class recordStatusEnum(MXStrEnum):
            idle = aauto()
            recording = aauto()

    class Values:
        @dataclass
        class recordStatus(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current status of the audio recorder'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=audioRecord.Enums.recordStatusEnum)

    class Functions:
        @dataclass
        class record(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Record audio'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class file(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The file to record to'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class duration(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The duration to record for'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])


@dataclass
class battery(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Defines that the device has a battery'

    class Values:
        @dataclass
        class battery(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'An indication of the status of the battery'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 100])


@dataclass
class button(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'A device with one or more buttons'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • pushed - The value if the button is pushed
                • held - The value if the button is held
                • double - The value if the button is pushed twice
                • pushed_2x - The value if the button is pushed twice
                • pushed_3x - The value if the button is pushed three times
                • pushed_4x - The value if the button is pushed four times
                • pushed_5x - The value if the button is pushed five times
                • pushed_6x - The value if the button is pushed six times
                • down - The value if the button is clicked down
                • down_2x - The value if the button is clicked down twice
                • down_3x - The value if the button is clicked down three times
                • down_4x - The value if the button is clicked down four times
                • down_5x - The value if the button is clicked down five times
                • down_6x - The value if the button is clicked down six times
                • down_hold - The value if the button is clicked down and held
                • up - The value if the button is clicked up
                • up_2x - The value if the button is clicked up twice
                • up_3x - The value if the button is clicked up three times
                • up_4x - The value if the button is clicked up four times
                • up_5x - The value if the button is clicked up five times
                • up_6x - The value if the button is clicked up six times
                • up_hold - The value if the button is clicked up and held
                • swipe_up - The value if the button is swiped up from botton to top
                • swipe_down - The value if the button is swiped down from top to bottom
                • swipe_left - The value if the button is swiped from right to left
                • swipe_right - The value if the button is swiped from left to right'''
            )

        class buttonEnum(MXStrEnum):
            pushed = aauto()
            held = aauto()
            double = aauto()
            pushed_2x = aauto()
            pushed_3x = aauto()
            pushed_4x = aauto()
            pushed_5x = aauto()
            pushed_6x = aauto()
            down = aauto()
            down_2x = aauto()
            down_3x = aauto()
            down_4x = aauto()
            down_5x = aauto()
            down_6x = aauto()
            down_hold = aauto()
            up = aauto()
            up_2x = aauto()
            up_3x = aauto()
            up_4x = aauto()
            up_5x = aauto()
            up_6x = aauto()
            up_hold = aauto()
            swipe_up = aauto()
            swipe_down = aauto()
            swipe_left = aauto()
            swipe_right = aauto()

    class Values:
        @dataclass
        class button(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The state of the buttons'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=button.Enums.buttonEnum)

        @dataclass
        class numberOfButtons(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The number of buttons on the device'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, bound=[0, INFINITY])

        @dataclass
        class supportedButtonValues(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'List of valid button attribute values: "str|..."'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.LIST, format=List[button.Enums.buttonEnum])


@dataclass
class buttonx4(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'A device with four buttons'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • pushed - The value if the button is pushed
                • held - The value if the button is held
                • double - The value if the button is pushed twice
                • pushed_2x - The value if the button is pushed twice
                • pushed_3x - The value if the button is pushed three times
                • pushed_4x - The value if the button is pushed four times
                • pushed_5x - The value if the button is pushed five times
                • pushed_6x - The value if the button is pushed six times
                • down - The value if the button is clicked down
                • down_2x - The value if the button is clicked down twice
                • down_3x - The value if the button is clicked down three times
                • down_4x - The value if the button is clicked down four times
                • down_5x - The value if the button is clicked down five times
                • down_6x - The value if the button is clicked down six times
                • down_hold - The value if the button is clicked down and held
                • up - The value if the button is clicked up
                • up_2x - The value if the button is clicked up twice
                • up_3x - The value if the button is clicked up three times
                • up_4x - The value if the button is clicked up four times
                • up_5x - The value if the button is clicked up five times
                • up_6x - The value if the button is clicked up six times
                • up_hold - The value if the button is clicked up and held
                • swipe_up - The value if the button is swiped up from botton to top
                • swipe_down - The value if the button is swiped down from top to bottom
                • swipe_left - The value if the button is swiped from right to left
                • swipe_right - The value if the button is swiped from left to right'''
            )

        class buttonEnum(MXStrEnum):
            pushed = aauto()
            held = aauto()
            double = aauto()
            pushed_2x = aauto()
            pushed_3x = aauto()
            pushed_4x = aauto()
            pushed_5x = aauto()
            pushed_6x = aauto()
            down = aauto()
            down_2x = aauto()
            down_3x = aauto()
            down_4x = aauto()
            down_5x = aauto()
            down_6x = aauto()
            down_hold = aauto()
            up = aauto()
            up_2x = aauto()
            up_3x = aauto()
            up_4x = aauto()
            up_5x = aauto()
            up_6x = aauto()
            up_hold = aauto()
            swipe_up = aauto()
            swipe_down = aauto()
            swipe_left = aauto()
            swipe_right = aauto()

    class Values:
        @dataclass
        class button1(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The state of the button1'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=button.Enums.buttonEnum)

        @dataclass
        class button2(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The state of the button2'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=button.Enums.buttonEnum)

        @dataclass
        class button3(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The state of the button3'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=button.Enums.buttonEnum)

        @dataclass
        class button4(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The state of the button4'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=button.Enums.buttonEnum)

        @dataclass
        class numberOfButtons(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The number of buttons on the device'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, bound=[0, INFINITY])

        @dataclass
        class supportedButtonValues(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'List of valid button attribute values: "str|..."'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.LIST, format=List[button.Enums.buttonEnum])


@dataclass
class carbonDioxideMeasurement(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Measure carbon dioxide levels'

    class Values:
        @dataclass
        class carbonDioxide(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The level of carbon dioxide detected'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, [0, 1000000])


@dataclass
class chargingState(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'The current status of battery charging'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • charging - charging
                • discharging - discharging
                • stopped - stopped
                • fullyCharged - fully charged
                • error - error'''
            )

        class chargingStateEnum(MXStrEnum):
            charging = aauto()
            discharging = aauto()
            stopped = aauto()
            fullyCharged = aauto()
            error = aauto()

    class Values:
        @dataclass
        class chargingState(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current charging state of the device'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=chargingState.Enums.chargingStateEnum)

        @dataclass
        class supportedChargingStates(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The list of charging states that the device supports. Optional, defaults to all states if not set.: "str|..."'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.LIST, format=List[chargingState.Enums.chargingStateEnum])


@dataclass
class clock(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Provide current date and time'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • monday
                • tuesday
                • wednesday
                • thursday
                • friday
                • saturday
                • sunday'''
            )

        class weekdayEnum(MXStrEnum):
            monday = aauto()
            tuesday = aauto()
            wednesday = aauto()
            thursday = aauto()
            friday = aauto()
            saturday = aauto()
            sunday = aauto()

    class Values:
        @dataclass
        class year(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current year'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 100000])

        @dataclass
        class month(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current month'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [1, 12])

        @dataclass
        class day(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current day'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [1, 31])

        @dataclass
        class weekday(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current weekday'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=clock.Enums.weekdayEnum)

        @dataclass
        class hour(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current hour'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 24])

        @dataclass
        class minute(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current minute'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 60])

        @dataclass
        class second(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current second'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 60])

        @dataclass
        class timestamp(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current timestamp (return current unix time - unit: seconds with floating point)'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class datetime(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current date and time as double number - format: YYYYMMddhhmm'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class date(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current date as double number - format: YYYYMMdd'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class time(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current time as double number - format: hhmm'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class isHoliday(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'today is holiday or not'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.BOOL)

    class Functions:
        @dataclass
        class delay(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'delay for a given amount of time'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class hour(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'hour'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, bound=[0, INFINITY])

                @dataclass
                class minute(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'minute'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, bound=[0, INFINITY])

                @dataclass
                class second(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'second'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, bound=[0, INFINITY])


@dataclass
class contactSensor(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows reading the value of a contact sensor device'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • closed - The value if closed
                • open - The value if open'''
            )

        class contactEnum(MXStrEnum):
            open = aauto()
            closed = aauto()

    class Values:
        @dataclass
        class contact(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current state of the contact sensor'

            @MXClassproperty
            def value_type(cls) -> MXType:
                return MXValueType(MXType.ENUM, format=contactSensor.Enums.contactEnum)


@dataclass
class colorControl(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for control of a color changing device by setting its hue, saturation, and color values'

    class Values:
        @dataclass
        class color(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return '``{"hue":"0-100 (percent)", "saturation":"0-100 (percent)"}``'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.STRING)

        @dataclass
        class hue(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return '``0-100`` (percent)'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, [0, 100])

        @dataclass
        class saturation(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return '``0-100`` (percent)'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, [0, 100])

    class Functions:
        @dataclass
        class setColor(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Sets the color based on the values passed in with the given map'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class color(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The color map supports the following key/value pairs:"RED|GREEN|BLUE", example:"255|255|255"'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DICT)

        @dataclass
        class setHue(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the hue value of the color'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class hue(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'A number in the range ``0-100`` representing the hue as a value of percent'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, [0, 100])

        @dataclass
        class setSaturation(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the saturation value of the color'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class saturation(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'A number in the range ``0-100`` representing the saturation as a value of percent'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, [0, 100])


@dataclass
class refresh(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allow the execution of the refresh command for devices that support it'

    class Functions:
        @dataclass
        class refresh(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Send the refresh command to the device - Return refresh success'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.BOOL


@dataclass
class currentMeasurement(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Get the value of electrical current measured from a device.'

    class Values:
        @dataclass
        class current(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A number representing the current measured.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])


@dataclass
class dehumidifierMode(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the dehumidifier mode.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • cooling
                • delayWash
                • drying
                • finished
                • refreshing
                • weightSensing
                • wrinklePrevent
                • dehumidifying
                • AIDrying
                • sanitizing
                • internalCare
                • freezeProtection
                • continuousDehumidifying
                • thawingFrozenInside'''
            )

        class dehumidifierModeEnum(MXStrEnum):
            cooling = aauto()
            delayWash = aauto()
            drying = aauto()
            finished = aauto()
            refreshing = aauto()
            weightSensing = aauto()
            wrinklePrevent = aauto()
            dehumidifying = aauto()
            AIDrying = aauto()
            sanitizing = aauto()
            internalCare = aauto()
            freezeProtection = aauto()
            continuousDehumidifying = aauto()
            thawingFrozenInside = aauto()

    class Values:
        @dataclass
        class dehumidifierMode(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current mode of the dehumidifier'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=dehumidifierMode.Enums.dehumidifierModeEnum)

    class Functions:
        @dataclass
        class setDehumidifierMode(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the dehumidifier mode'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class mode(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the dehumidifier mode'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=dehumidifierMode.Enums.dehumidifierModeEnum)


@dataclass
class dishwasherMode(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the dishwasher mode.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • eco - The dishwasher is in "eco" mode
                • intense - The dishwasher is in "intense" mode
                • auto - The dishwasher is in "auto" mode
                • quick - The dishwasher is in "quick" mode
                • rinse - The dishwasher is in "rinse" mode
                • dry - The dishwasher is in "dry" mode'''
            )

        class dishwasherModeEnum(MXStrEnum):
            eco = aauto()
            intense = aauto()
            auto = aauto()
            quick = aauto()
            rinse = aauto()
            dry = aauto()

    class Values:
        @dataclass
        class dishwasherMode(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current mode of the dishwasher'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=dishwasherMode.Enums.dishwasherModeEnum)

    class Functions:
        @dataclass
        class setDishwasherMode(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the dishwasher mode'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class mode(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the dishwasher mode to "eco", "intense", "auto", "quick", "rinse", or "dry" mode'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=dishwasherMode.Enums.dishwasherModeEnum)


@dataclass
class doorControl(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allow for the control of a door'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • closed - The door is closed
                • closing - The door is closing
                • open - The door is open
                • opening - The door is opening
                • unknown - The current state of the door is unknown'''
            )

        class doorEnum(MXStrEnum):
            closed = aauto()
            closing = aauto()
            open = aauto()
            opening = aauto()
            unknown = aauto()

    class Values:
        @dataclass
        class door(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current state of the door'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=doorControl.Enums.doorEnum)

    class Functions:
        @dataclass
        class open(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Open the door'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class close(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Close the door'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class dustSensor(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Gets the reading of the dust sensor.'

    class Values:
        @dataclass
        class dustLevel(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current dust level -- also refered to as PM10, measured in micrograms per cubic meter'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, INFINITY])

        @dataclass
        class fineDustLevel(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current level of fine dust -- also refered to as PM2.5, measured in micrograms per cubic meter'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, INFINITY])

        @dataclass
        class veryFineDustLevel(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current level of fine dust -- also refered to as PM1.0, measured in micrograms per cubic meter'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, INFINITY])


@dataclass
class fanControl(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the fan.'

    class Values:
        @dataclass
        class fanSpeed(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current fan speed represented as a integer value. - unit: RPM'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, INFINITY])

        @dataclass
        class percent(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current fan speed represented as a percent value.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 100])

    class Functions:
        @dataclass
        class setFanSpeed(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the fan speed'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class speed(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the fan to this speed'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, [0, INFINITY])

        @dataclass
        class setPercent(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the fan speed percent.'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class percent(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The percent value to set the fan speed to.'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, [0, 100])


@dataclass
class feederOperatingState(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of a feeder device.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • idle - idle
                • feeding - feeding
                • error - error'''
            )

        class feederOperatingStateEnum(MXStrEnum):
            idle = aauto()
            feeding = aauto()
            error = aauto()

    class Values:
        @dataclass
        class feederOperatingState(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current state of the feeder.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=feederOperatingState.Enums.feederOperatingStateEnum)

    class Functions:
        @dataclass
        class startFeeding(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Begin the feeding process.'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class irrigatorOperatingState(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of a irrigator device.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • idle - idle
                • watering - watering
                • error - error'''
            )

        class irrigatorOperatingStateEnum(MXStrEnum):
            idle = aauto()
            watering = aauto()
            error = aauto()

    class Values:
        @dataclass
        class irrigatorOperatingState(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current state of the irrigator.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=irrigatorOperatingState.Enums.irrigatorOperatingStateEnum)

    class Functions:
        @dataclass
        class startWatering(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Begin the watering process.'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class feederPortion(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the portion control of a feeder device.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • grams
                • pounds
                • ounces
                • servings'''
            )

        class unitEnum(MXStrEnum):
            grams = aauto()
            pounds = aauto()
            ounces = aauto()
            servings = aauto()

    class Values:
        @dataclass
        class feedPortion(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A number that represents the portion (in grams, pounds, ounces, or servings) that will dispense.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, [0, 2000])

    class Functions:
        @dataclass
        class setFeedPortion(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the portion (in grams, pounds, ounces, or servings) that the feeder will dispense.'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class portion(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The portion (in grams, pounds, ounces, or servings) to dispense.'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, [0, 2000])

                @dataclass
                class unit(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return ''

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=feederPortion.Enums.unitEnum)


@dataclass
class irrigatorPortion(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the portion control of a irrigator device.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • liters
                • milliliters
                • gallons
                • ounces
                '''
            )

        class unitEnum(MXStrEnum):
            liters = aauto()
            milliliters = aauto()
            gallons = aauto()
            ounces = aauto()

    class Values:
        @dataclass
        class waterPortion(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A number that represents the portion (in liters, milliliters, gallons, or ounces) that will dispense.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

    class Functions:
        @dataclass
        class setWaterPortion(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the portion (in liters, milliliters, gallons, or ounces) that the irrigator will dispense.'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class portion(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The portion (in grams, pounds, ounces, or servings) to dispense.'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, [0, 2000])

                @dataclass
                class unit(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return ''

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=irrigatorPortion.Enums.unitEnum)


@dataclass
class switch(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of a switch device'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • on - The value of the ``switch`` attribute if the switch is on
                • off - The value of the ``switch`` attribute if the switch is off'''
            )

        class switchEnum(MXStrEnum):
            on = aauto()
            off = aauto()

    class Values:
        @dataclass
        class switch(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A string representation of whether the switch is on or off'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=switch.Enums.switchEnum)

    class Functions:
        @dataclass
        class on(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Turn a switch on'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class off(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Turn a switch off'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class toggle(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Toggle a switch'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class switchLevel(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the level of a device like a light or a dimmer switch.'

    class Values:
        @dataclass
        class level(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A number that represents the current level, usually ``0-100`` in percent'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 100])

        @dataclass
        class levelRange(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Constraints on the level value:"min|max",example:"30|60"'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DICT)

    class Functions:
        @dataclass
        class setLevel(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the level to the given value. If the device supports being turned on and off then it will be turned on if ``level`` is greater than 0 and turned off if ``level`` is equal to 0.'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class level(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The level value, usually ``0-100`` in percent'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, [-0, 100])

                @dataclass
                class rate(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The rate at which to change the level'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, [-0, 100])

        @dataclass
        class alert(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Alert with dimming'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class lightLevel(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'A numerical representation of the brightness intensity'

    class Values:
        @dataclass
        class light(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'brightness intensity (Unit: lux)'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, [0, INFINITY])


@dataclass
class manager(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allow Manager Thing\'s features'

    class Functions:
        @dataclass
        class discover(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Discover local devices - Return device list with json format'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.STRING

        @dataclass
        class add_thing(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Add staff thing - Return error string'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.STRING

            class Arguments:

                @dataclass
                class parameter(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Staff thing\'s parameter'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class client_id(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Requester\'s client id'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class name(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Staff thing\'s name'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

        @dataclass
        class delete_thing(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Delete staff thing - Return error string'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.STRING

            class Arguments:

                @dataclass
                class name(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Staff thing\'s name'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class client_id(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Requester\'s client id'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)


@dataclass
class motionSensor(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return textwrap.dedent(
            '''\
                • active - The value when motion is detected
                • inactive - The value when no motion is detected'''
        )

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent('''  ''')

        class motionEnum(MXStrEnum):
            active = aauto()
            inactive = aauto()

    class Values:
        @dataclass
        class motion(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current state of the motion sensor'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=motionSensor.Enums.motionEnum)


@dataclass
class temperatureMeasurement(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Get the temperature from a Device that reports current temperature'

    class Values:
        @dataclass
        class temperature(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A number that usually represents the current temperature'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, [-460, 10000])

        @dataclass
        class temperatureRange(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Constraints on the temperature value:"min|max", example:"-20|50"'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DICT)


@dataclass
class testSkill(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'testSkill'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent('''testSkill Enums''')

        class testSkillEnum(MXStrEnum):
            enum1 = aauto()
            enum2 = aauto()
            enum3 = aauto()

    class Values:
        @dataclass
        class testSkillValue(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'testSkillValue'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.STRING)

    class Functions:
        @dataclass
        class testSkillFunction(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'testSkillFunction'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.STRING

            class Arguments:
                @dataclass
                class testArgument(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'testArgument'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)


@dataclass
class tvChannel(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the TV channel.'

    class Values:
        @dataclass
        class tvChannel(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current status of the TV channel'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, INFINITY])

        @dataclass
        class tvChannelName(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current status of the TV channel name'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.STRING)

    class Functions:
        @dataclass
        class channelUp(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Move the TV channel up'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class channelDown(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Move the TV channel down'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class setTvChannel(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the TV channel'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class tvChannel(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return ''

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, bound=[0, INFINITY])

        @dataclass
        class setTvChannelName(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the TV channel Name'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class tvChannelName(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return ''

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)


@dataclass
class voltageMeasurement(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Get the value of voltage measured from devices that support it'

    class Values:
        @dataclass
        class voltage(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A number representing the current voltage measured'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])


@dataclass
class gasMeter(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Read the gas consumption of an energy metering device'

    class Values:
        @dataclass
        class gasMeter(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'the gas energy reported by the metering device. unit: kWh'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class gasMeterCalorific(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'a measure of the available heat energy, used as part of the calculation to convert gas volume to gas energy. - unit: kcal'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class gasMeterTime(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The cumulative gas use time reported by the metering device. - unit: seconds'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class gasMeterVolume(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'the cumulative gas volume reported by the metering device. - unit: cubic meters'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])


@dataclass
class soilHumidityMeasurement(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allow reading the soil humidity from devices that support it'

    class Values:
        @dataclass
        class soilHumidity(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A numerical representation of the soil humidity measurement taken by the device'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[-10000, 100000])


@dataclass
class camera(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of a camera device'

    class Values:
        @dataclass
        class image(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The latest image captured by the camera'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.BINARY)

        @dataclass
        class video(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The latest video captured by the camera'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.BINARY)

    class Functions:
        @dataclass
        class take(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Take a picture with the camera - Return the image as binary data'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.BINARY

        @dataclass
        class takeTimelapse(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Take a picture with the camera - Return the video as binary data'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.BINARY

            class Arguments:

                @dataclass
                class duration(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The duration of the timelapse in seconds'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, [0, INFINITY])

                @dataclass
                class speed(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The speed of the timelapse'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, [0, INFINITY])


@dataclass
class tvocMeasurement(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Measure total volatile organic compound levels'

    class Values:
        @dataclass
        class tvocLevel(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The level of total volatile organic compounds detected'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, [0, 1000000])


@dataclass
class valve(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of a valve device'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • closed - The value of the ``valve`` attribute if the valve is closed
                • open - The value of the ``valve`` attribute if the valve is open'''
            )

        class valveEnum(MXStrEnum):
            open = aauto()
            closed = aauto()

    class Values:
        @dataclass
        class valve(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A string representation of whether the valve is open or closed'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=valve.Enums.valveEnum)

    class Functions:
        @dataclass
        class open(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Open the valve'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class close(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Close the valve'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class pump(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of a pump device'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • closed - The value of the ``pump`` attribute if the pump is closed
                • open - The value of the ``pump`` attribute if the pump is open'''
            )

        class pumpEnum(MXStrEnum):
            open = aauto()
            closed = aauto()

    class Values:
        @dataclass
        class pump(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A string representation of whether the pump is open or closed'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=pump.Enums.pumpEnum)

    class Functions:
        @dataclass
        class open(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Open the pump'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class close(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Close the pump'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class audioMute(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of audio mute.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • muted - The audio is in "muted" state
                • unmuted - The audio is in "unmuted" state'''
            )

        class muteEnum(MXStrEnum):
            muted = aauto()
            unmuted = aauto()

    class Values:
        @dataclass
        class muteStatus(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current status of the audio mute'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=audioMute.Enums.muteEnum)

    class Functions:
        @dataclass
        class mute(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the audio to mute state'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class unmute(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the audio to unmute state'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class setMute(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the state of the audio mute'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class state(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the audio mute state to "muted" or "unmuted"'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=audioMute.Enums.muteEnum)


@dataclass
class mediaPlayback(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the media playback.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • paused - Media playback is in a "paused" state
                • playing - Media playback is in a "playing" state
                • stopped - Media playback is in a "stopped" state
                • fast forwarding - Media playback is in a "fast forwarding" state
                • rewinding - Media playback is in a "rewinding" state
                • buffering - Media playback is in a "buffering" state'''
            )

        class mediaPlaybackEnum(MXStrEnum):
            paused = aauto()
            playing = aauto()
            stopped = aauto()
            fast = aauto()
            rewinding = aauto()
            buffering = aauto()

    class Values:
        @dataclass
        class playbackStatus(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Status of the media playback'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=mediaPlayback.Enums.mediaPlaybackEnum)

        @dataclass
        class supportedPlaybackCommands(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Media playback commands which are supported: "str|..."'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.LIST, format=List[mediaPlayback.Enums.mediaPlaybackEnum])

    class Functions:

        @dataclass
        class play(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Play the media playback'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class source(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The source of the media playback'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

        @dataclass
        class stop(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Stop the media playback'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class pause(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Pause the media playback'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class fastForward(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Fast forward the media playback'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class rewind(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Rewind the media playback'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class setPlaybackStatus(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the playback status'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class status(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the playback status to "paused", "playing", "stopped", "fast forwarding" or "rewinding" state.'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=mediaPlayback.Enums.mediaPlaybackEnum)

        @dataclass
        class speak(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'TTS feature'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class text(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The text to be spoken'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)


@dataclass
class refrigeration(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the refrigeration.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • on - The value of the ``defrost``, ``rapidCooling``, ``rapidFreezing`` attribute if the defrost, rapidCooling, rapidFreezing is on
                • off - The value of the ``defrost``, ``rapidCooling``, ``rapidFreezing`` attribute if the defrost, rapidCooling, rapidFreezing is off'''
            )

        class defrostEnum(MXStrEnum):
            on = aauto()
            off = aauto()

        class rapidCoolingEnum(MXStrEnum):
            on = aauto()
            off = aauto()

        class rapidFreezingEnum(MXStrEnum):
            on = aauto()
            off = aauto()

    class Values:
        @dataclass
        class defrost(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Status of the defrost'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=refrigeration.Enums.defrostEnum)

        @dataclass
        class rapidCooling(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Status of the rapid cooling'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=refrigeration.Enums.rapidCoolingEnum)

        @dataclass
        class rapidFreezing(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Status of the rapid freezing'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=refrigeration.Enums.rapidFreezingEnum)

    class Functions:
        @dataclass
        class setDefrost(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Sets the defrost on or off'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class defrost(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The on or off value for the defrost'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=refrigeration.Enums.defrostEnum)

        @dataclass
        class setRapidCooling(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Sets the rapid cooling on or off'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class rapidCooling(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The on or off value for the rapid cooling'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=refrigeration.Enums.rapidCoolingEnum)

        @dataclass
        class setRapidFreezing(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Sets the rapid freezing on or off'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class rapidFreezing(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The on or off value for the rapid freezing'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=refrigeration.Enums.rapidFreezingEnum)


@dataclass
class audioVolume(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of audio volume.'

    class Values:
        @dataclass
        class volume(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current volume setting of the audio'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 100])

    class Functions:
        @dataclass
        class setVolume(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the audio volume level'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class volume(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'A value to which the audio volume level should be set'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, [0, 100])

        @dataclass
        class volumeUp(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Turn the audio volume up'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class volumeDown(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Turn the audio volume down'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class windowShadeLevel(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the level of a window shade.'

    class Values:
        @dataclass
        class shadeLevel(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A number that represents the current level as a function of being open, ``0-100`` in percent; 0 representing completely closed, and 100 representing completely open.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 100])

    class Functions:
        @dataclass
        class setShadeLevel(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the shade level to the given value.'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class shadeLevel(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The level to which the shade should be set, ``0-100`` in percent; 0 representing completely closed, and 100 representing completely open.'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, [0, 100])


@dataclass
class curtainLevel(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the level of a curtain.'

    class Values:
        @dataclass
        class curtainLevel(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A number that represents the current level as a function of being open, ``0-100`` in percent; 0 representing completely closed, and 100 representing completely open.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 100])

    class Functions:
        @dataclass
        class setCurtainLevel(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the curtain level to the given value.'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class curtainLevel(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The level to which the curtain should be set, ``0-100`` in percent; 0 representing completely closed, and 100 representing completely open.'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, [0, 100])


@dataclass
class blindLevel(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the level of a blind.'

    class Values:
        @dataclass
        class blindLevel(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A number that represents the current level as a function of being open, ``0-100`` in percent; 0 representing completely closed, and 100 representing completely open.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.INTEGER, [0, 100])

    class Functions:
        @dataclass
        class setBlindLevel(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the blind level to the given value.'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class blindLevel(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The level to which the blind should be set, ``0-100`` in percent; 0 representing completely closed, and 100 representing completely open.'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.INTEGER, [0, 100])


@dataclass
class windowShade(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the window shade.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • closed - closed
                • closing - closing…
                • open - open
                • opening - opening…
                • partially open - partially open
                • paused -
                • unknown - unknown'''
            )

        class windowShadeEnum(MXStrEnum):
            closed = aauto()
            closing = aauto()
            open = aauto()
            opening = aauto()
            partially = aauto()
            paused = aauto()
            unknown = aauto()

    class Values:
        @dataclass
        class windowShade(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A string representation of whether the window shade is open or closed'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=windowShade.Enums.windowShadeEnum)

        @dataclass
        class supportedWindowShadeCommands(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Window shade commands supported by this instance of Window Shade: "str|..."'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.LIST, format=List[windowShade.Enums.windowShadeEnum])

    class Functions:
        @dataclass
        class open(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Open the window shade'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class close(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Close the window shade'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class pause(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Pause opening or closing the window shade'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class curtain(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the curtain.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • closed - closed
                • closing - closing…
                • open - open
                • opening - opening…
                • partially open - partially open
                • paused -
                • unknown - unknown'''
            )

        class curtainEnum(MXStrEnum):
            closed = aauto()
            closing = aauto()
            open = aauto()
            opening = aauto()
            partially = aauto()
            paused = aauto()
            unknown = aauto()

    class Values:
        @dataclass
        class curtain(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A string representation of whether the curtain is open or closed'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=curtain.Enums.curtainEnum)

        @dataclass
        class supportedCurtainCommands(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Curtain commands supported by this instance of Curtain: "str|..."'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.LIST, format=List[curtain.Enums.curtainEnum])

    class Functions:
        @dataclass
        class open(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Open the curtain'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class close(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Close the curtain'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class pause(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Pause opening or closing the curtain'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class blind(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the blind.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • closed - closed
                • closing - closing…
                • open - open
                • opening - opening…
                • partially open - partially open
                • paused -
                • unknown - unknown'''
            )

        class blindEnum(MXStrEnum):
            closed = aauto()
            closing = aauto()
            open = aauto()
            opening = aauto()
            partially = aauto()
            paused = aauto()
            unknown = aauto()

    class Values:
        @dataclass
        class blind(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A string representation of whether the blind is open or closed'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=blind.Enums.blindEnum)

    class Functions:
        @dataclass
        class open(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Open the blind'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class close(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Close the blind'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class pause(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Pause opening or closing the blind'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class robotCleanerCleaningMode(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the robot cleaner cleaning mode.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • auto - The robot cleaner cleaning mode is in "auto" mode
                • part - The robot cleaner cleaning mode is in "part" mode
                • repeat - The robot cleaner cleaning mode is in "repeat" mode
                • manual - The robot cleaner cleaning mode is in "manual" mode
                • stop - The robot cleaner cleaning mode is in "stop" mode
                • map - The robot cleaner cleaning mode is in "map" mode'''
            )

        class robotCleanerCleaningModeEnum(MXStrEnum):
            auto = aauto()
            part = aauto()
            repeat = aauto()
            manual = aauto()
            stop = aauto()
            map = aauto()

    class Values:
        @dataclass
        class robotCleanerCleaningMode(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current status of the robot cleaner cleaning mode'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=robotCleanerCleaningMode.Enums.robotCleanerCleaningModeEnum)

    class Functions:
        @dataclass
        class setRobotCleanerCleaningMode(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the robot cleaner cleaning mode'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class mode(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the robot cleaner cleaning mode, to "auto", "part", "repeat", "manual" or "stop" modes'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=robotCleanerCleaningMode.Enums.robotCleanerCleaningModeEnum)


@dataclass
class powerMeter(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for reading the power consumption from devices that report it'

    class Values:
        @dataclass
        class power(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return (
                    'A number representing the current power consumption. Check the device documentation for how this value is reported - unit: Watts'
                )

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class powerConsumption(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'energy and power consumption during specific time period:"unit|Wh", example:"kWh|30"'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DICT)


@dataclass
class presenceSensor(Skill):c

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'The ability to see the current status of a presence sensor device'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • present - The device is present
                • not present - left'''
            )

        class presenceEnum(MXStrEnum):
            present = aauto()
            not_present = aauto()

    class Values:
        @dataclass
        class presence(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current state of the presence sensor'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=presenceSensor.Enums.presenceEnum)


@dataclass
class soundSensor(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'A Device that senses sound'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • detected - Sound is detected
                • not detected - no sound'''
            )

        class soundEnum(MXStrEnum):
            detected = aauto()
            not_detected = aauto()

    class Values:
        @dataclass
        class sound(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Whether or not sound was detected by the Device'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=soundSensor.Enums.soundEnum)


@dataclass
class leakSensor(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'A Device that senses water leakage'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • detected - water leak is detected
                • not detected - no leak'''
            )

        class presenceEnum(MXStrEnum):
            detected = aauto()
            not_detected = aauto()

    class Values:
        @dataclass
        class leakage(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Whether or not water leakage was detected by the Device'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=leakSensor.Enums.presenceEnum)


@dataclass
class atmosphericPressureSensor(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Measure the atmospheric pressure'

    class Values:
        @dataclass
        class pressure(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Gets the value of the atmospheric pressure level.'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, 2000])


@dataclass
class soundPressureLevel(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Gets the value of the sound pressure level.'

    class Values:
        @dataclass
        class soundPressureLevel(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Level of the sound pressure'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, [0, 194])


@dataclass
class smokeDetector(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'A device that detects the presence or absence of smoke.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                    • clear - No smoke detected
                    • detected - Smoke detected
                    • tested - Smoke detector test button was activated'''
            )

        class smokeEnum(MXStrEnum):
            clear = aauto()
            detected = aauto()
            tested = aauto()

    class Values:
        @dataclass
        class smoke(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The state of the smoke detection device'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=smokeDetector.Enums.smokeEnum)


@dataclass
class relativeHumidityMeasurement(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allow reading the relative humidity from devices that support it'

    class Values:
        @dataclass
        class humidity(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A numerical representation of the relative humidity measurement taken by the device'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, [0, 100])


@dataclass
class sirenMode(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the siren.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • both - 
                • off - 
                • siren - 
                • strobe - '''
            )

        class sirenModeEnum(MXStrEnum):
            both = aauto()
            off = aauto()
            siren = aauto()
            strobe = aauto()

    class Values:
        @dataclass
        class sirenMode(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current mode of the siren'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=sirenMode.Enums.sirenModeEnum)

    class Functions:
        @dataclass
        class setSirenMode(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the siren mode'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class mode(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the siren mode'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=sirenMode.Enums.sirenModeEnum)


@dataclass
class windowControl(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for the control of the window shade.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • closed - closed
                • open - open
                • unknown - unknown'''
            )

        class windowEnum(MXStrEnum):
            closed = aauto()
            open = aauto()
            unknown = aauto()

    class Values:
        @dataclass
        class window(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A string representation of whether the window is open or closed'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=windowControl.Enums.windowEnum)

    class Functions:
        @dataclass
        class open(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Open the window'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class close(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Close the window'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID


@dataclass
class weatherProvider(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Provides weather information'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • thunderstorm - thunderstorm
                • drizzle - drizzle
                • rain - rain
                • snow - snow
                • mist - mist
                • smoke - smoke
                • haze - haze
                • dust - dust
                • fog - fog
                • sand - sand
                • ash - ash
                • squall - squall
                • tornado - tornado
                • clear - clear
                • clouds - clouds'''
            )

        class weatherEnum(MXStrEnum):
            thunderstorm = aauto()
            drizzle = aauto()
            rain = aauto()
            snow = aauto()
            mist = aauto()
            smoke = aauto()
            haze = aauto()
            dust = aauto()
            fog = aauto()
            sand = aauto()
            ash = aauto()
            squall = aauto()
            tornado = aauto()
            clear = aauto()
            clouds = aauto()

    class Values:

        @dataclass
        class temperatureWeather(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current temperature level'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[-470, 10000])

        @dataclass
        class humidityWeather(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current humidity level'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, 100])

        @dataclass
        class pressureWeather(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current pressure level'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, 2000])

        @dataclass
        class pm25Weather(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current pm25 level'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, 10000])

        @dataclass
        class pm10Weather(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current pm10 level'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.DOUBLE, bound=[0, 10000])

        @dataclass
        class weather(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current weather condition'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=weatherProvider.Enums.weatherEnum)

    class Functions:
        @dataclass
        class getWeatherInfo(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Get the current weather information - Return whole weather information, format: "temperature, humidity, pressure, pm25, pm10, weather, weather_string, icon_id, location"'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.STRING

            class Arguments:
                @dataclass
                class lat(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The latitude of the location'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-90, 90])

                @dataclass
                class lon(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The longitude of the location'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-180, 180])


@dataclass
class emailProvider(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Provides email services'

    class Functions:
        @dataclass
        class sendMail(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Send an email'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class toAddress(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The email address of the recipient'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class title(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The title of the email'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class text(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The text of the email'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

        @dataclass
        class sendMailWithFile(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Send an email with an attachment'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class toAddress(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The email address of the recipient'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class title(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The title of the email'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class text(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The text of the email'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class file(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The path to the file to be attached'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.BINARY)


@dataclass
class menuProvider(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Provides menu information services'

    class Functions:
        @dataclass
        class menu(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Get the menu - Return the menu list'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.STRING

            class Arguments:
                @dataclass
                class command(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The command to get the menu - format: [오늘|내일] [학생식당|수의대식당|전망대(3식당)|예술계식당(아름드리)|기숙사식당|아워홈|동원관식당(113동)|웰스토리(220동)|투굿(공대간이식당)|자하연식당|301동식당] [아침|점심|저녁]'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

        @dataclass
        class todayMenu(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Get today\'s menu randomly - Return the menu list'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.STRING

        @dataclass
        class todayPlace(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Get today\'s restaurant randomly - Return the restaurant name'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.STRING


@dataclass
class humidifierMode(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Maintains and sets the state of an humidifier'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • auto -
                • low -
                • medium -
                • high -'''
            )

        class humidifierModeEnum(MXStrEnum):
            auto = aauto()
            low = aauto()
            medium = aauto()
            high = aauto()

    class Values:
        @dataclass
        class humidifierMode(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Current mode of the humidifier'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=humidifierMode.Enums.humidifierModeEnum)

    class Functions:
        @dataclass
        class setHumidifierMode(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the humidifier mode'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class mode(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the humidifier mode to "auto", "low", "medium", or "high" mode'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=humidifierMode.Enums.humidifierModeEnum)


@dataclass
class pumpOperationMode(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Allows for setting the operation mode on a pump.'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • normal - The pump is controlled by a setpoint.
                • minimum - This value sets the pump to run at the minimum possible speed it can without being stopped.
                • maximum - This value sets the pump to run at its maximum possible speed.
                • localSetting - This value sets the pump to run with the local settings of the pump.'''
            )

        class pumpOperationModeEnum(MXStrEnum):
            normal = aauto()
            minimum = aauto()
            maximum = aauto()
            localSetting = aauto()

    class Values:
        @dataclass
        class currentOperationMode(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The current effective operation mode of the pump'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=pumpOperationMode.Enums.pumpOperationModeEnum)

        @dataclass
        class operationMode(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'The operation mode of the pump'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=pumpOperationMode.Enums.pumpOperationModeEnum)

        @dataclass
        class supportedOperationModes(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Supported operation modes for this device to be in: "str|..."'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.LIST, format=List[pumpOperationMode.Enums.pumpOperationModeEnum])

    class Functions:
        @dataclass
        class setOperationMode(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the operation mode'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class operationMode(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The operation mode to set the device to'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=pumpOperationMode.Enums.pumpOperationModeEnum)


@dataclass
class calculator(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Provides calculation services'

    class Functions:
        @dataclass
        class add(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Add two numbers'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.DOUBLE

            class Arguments:
                @dataclass
                class a(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The first number to add'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])

                @dataclass
                class b(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The second number to add'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])

        @dataclass
        class sub(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Subtract two numbers'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.DOUBLE

            class Arguments:
                @dataclass
                class a(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The first number to subtract'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])

                @dataclass
                class b(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The second number to subtract'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])

        @dataclass
        class mul(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Multiply two numbers'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.DOUBLE

            class Arguments:
                @dataclass
                class a(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The first number to multiply'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])

                @dataclass
                class b(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The second number to multiply'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])

        @dataclass
        class div(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Divide two numbers'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.DOUBLE

            class Arguments:
                @dataclass
                class a(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The first number to divide'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])

                @dataclass
                class b(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The second number to divide'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])

        @dataclass
        class mod(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Modulo two numbers'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.DOUBLE

            class Arguments:
                @dataclass
                class a(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The first number to modulo'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])

                @dataclass
                class b(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The second number to modulo'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[-INFINITY, INFINITY])


@dataclass
class fallDetection(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Detects if a fall has occurred'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • fall - fall detected
                • normal - no fall detected'''
            )

        class fallEnum(MXStrEnum):
            fall = aauto()
            normal = aauto()

    class Values:
        @dataclass
        class fall(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Whether or not a fall was detected'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=fallDetection.Enums.fallEnum)


@dataclass
class fallDetection(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'Detects if a fall has occurred'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                • fall - fall detected
                • normal - no fall detected'''
            )

        class fallEnum(MXStrEnum):
            fall = aauto()
            normal = aauto()

    class Values:
        @dataclass
        class fall(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Whether or not a fall was detected'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=fallDetection.Enums.fallEnum)


@dataclass
class alarm(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'The Alarm skill allows for interacting with devices that serve as alarms'

    class Enums:
        @MXClassproperty
        def descriptor(cls) -> str:
            return textwrap.dedent(
                '''\
                # alarm
                • both - if the alarm is strobing and sounding the alarm
                • off - if the alarm is turned off
                • siren - if the alarm is sounding the siren
                • strobe - if the alarm is strobing
                
                # alarmVolume
                • mute - 
                • low - 
                • medium - 
                • high - '''
            )

        class alarmEnum(MXStrEnum):
            both = aauto()
            off = aauto()
            siren = aauto()
            strobe = aauto()

        class alarmVolumeEnum(MXStrEnum):
            mute = aauto()
            low = aauto()
            medium = aauto()
            high = aauto()

    class Values:
        @dataclass
        class alarm(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A string representation of whether the switch is on or off'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=alarm.Enums.alarmEnum)

        @dataclass
        class alarmVolume(SkillValue):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'A string representation of the volume of the alarm'

            @MXClassproperty
            def value_type(cls) -> MXValueType:
                return MXValueType(MXType.ENUM, format=alarm.Enums.alarmVolumeEnum)

    class Functions:
        @dataclass
        class both(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Strobe and sound the alarm'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class off(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Turn the alarm (siren and strobe) off'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class siren(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Sound the siren on the alarm'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class strobe(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Strobe the alarm'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

        @dataclass
        class setAlarmVolume(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set the volume of the alarm'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class alarmVolume(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'Set the volume of the alarm to "mute", "low", "medium", or "high"'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.ENUM, format=alarm.Enums.alarmVolumeEnum)


@dataclass
class timer(Skill):

    @MXClassproperty
    def descriptor(cls) -> str:
        return 'The Timer allows for interacting with devices that serve as timers'

    class Enums:
        pass

    class Values:
        pass

    class Functions:
        @dataclass
        class add(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Add a timer'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class name(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The time name'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class timeout(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The time at which the timer should expire'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class set(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Set a timer'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class name(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The time name'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

                @dataclass
                class timeout(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The time at which the timer should expire'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.DOUBLE, bound=[0, INFINITY])

        @dataclass
        class start(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Start a timer'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class name(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The time name'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

        @dataclass
        class reset(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Reset a timer'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.VOID

            class Arguments:
                @dataclass
                class name(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The time name'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

        @dataclass
        class isSet(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Check if a timer is set'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.BOOL

            class Arguments:
                @dataclass
                class name(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The time name'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)

        @dataclass
        class isExist(SkillFunction):
            @MXClassproperty
            def descriptor(cls) -> str:
                return 'Check if a timer is exist'

            @MXClassproperty
            def return_type(cls) -> MXType:
                return MXType.BOOL

            class Arguments:
                @dataclass
                class name(SkillFunctionArgument):
                    @MXClassproperty
                    def descriptor(cls) -> str:
                        return 'The time name'

                    @MXClassproperty
                    def argument_type(cls) -> MXValueType:
                        return MXValueType(MXType.STRING)