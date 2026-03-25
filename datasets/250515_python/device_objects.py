from big_thing_py.core.service_model import Objects as Skill
from big_thing_py.core.device_model.DeviceObjects import MXDeviceCategory
from typing import Set, Dict, List, Union, Any


class AirConditioner(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.airConditionerMode,
    }


class AirPurifier(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.airPurifierFanMode,
    }


class AirQualityDetector(MXDeviceCategory):
    skills = {
        Skill.dustSensor,
        Skill.carbonDioxideMeasurement,
        Skill.temperatureMeasurement,
        Skill.relativeHumidityMeasurement,
        Skill.tvocMeasurement,
    }


class Alarm(MXDeviceCategory):
    skills = {
        Skill.alarm,
        Skill.battery,
    }


class Blind(MXDeviceCategory):
    skills = {
        Skill.blind,
        Skill.blindLevel,
    }


class Button(MXDeviceCategory):
    skills = {
        Skill.button,
    }


class Buttonx4(MXDeviceCategory):
    skills = {
        Skill.buttonx4,
    }


class Calculator(MXDeviceCategory):
    skills = {
        Skill.calculator,
    }


class Camera(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.camera,
    }


class Charger(MXDeviceCategory):
    skills = {
        Skill.chargingState,
        Skill.currentMeasurement,
        Skill.voltageMeasurement,
    }


class Clock(MXDeviceCategory):
    skills = {
        Skill.clock,
    }


class ContactSensor(MXDeviceCategory):
    skills = {
        Skill.contactSensor,
    }


class Curtain(MXDeviceCategory):
    skills = {
        Skill.curtain,
    }


class Dehumidifier(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.dehumidifierMode,
    }


class Dishwasher(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.dishwasherMode,
    }


class DoorLock(MXDeviceCategory):
    skills = {
        Skill.doorControl,
    }


class EmailProvider(MXDeviceCategory):
    skills = {
        Skill.emailProvider,
    }


class Fan(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.fanControl,
    }


class Feeder(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.feederOperatingState,
        Skill.feederPortion,
    }


class GasMeter(MXDeviceCategory):
    skills = {
        Skill.gasMeter,
    }


class GasValve(MXDeviceCategory):
    skills = {
        Skill.gasMeter,
        Skill.valve,
    }


class Humidifier(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.humidifierMode,
    }


class HumiditySensor(MXDeviceCategory):
    skills = {
        Skill.relativeHumidityMeasurement,
    }


class Irrigator(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.irrigatorOperatingState,
        Skill.irrigatorPortion,
    }


class LeakSensor(MXDeviceCategory):
    skills = {
        Skill.leakSensor,
    }


class Light(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.switchLevel,
        Skill.colorControl,
    }


class LightSensor(MXDeviceCategory):
    skills = {
        Skill.lightLevel,
    }


class MenuProvider(MXDeviceCategory):
    skills = {
        Skill.menuProvider,
    }


class MotionSensor(MXDeviceCategory):
    skills = {
        Skill.motionSensor,
    }


class PresenceSensor(MXDeviceCategory):
    skills = {
        Skill.presenceSensor,
    }


class Pump(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.pump,
        Skill.pumpOperationMode,
    }


class Refrigerator(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.refrigeration,
    }


class RobotCleaner(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.robotCleanerCleaningMode,
    }


class Shade(MXDeviceCategory):
    skills = {
        Skill.windowShade,
        Skill.windowShadeLevel,
    }


class Siren(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.sirenMode,
    }


class SmartPlug(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.powerMeter,
        Skill.voltageMeasurement,
        Skill.currentMeasurement,
    }


class SmokeDetector(MXDeviceCategory):
    skills = {
        Skill.smokeDetector,
    }


class SoilMoistureSensor(MXDeviceCategory):
    skills = {
        Skill.soilHumidityMeasurement,
    }


class SoundSensor(MXDeviceCategory):
    skills = {
        Skill.soundSensor,
        Skill.soundPressureLevel,
    }


class Speaker(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.mediaPlayback,
    }


class Recorder(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.audioRecord,
    }


class Switch(MXDeviceCategory):
    skills = {
        Skill.switch,
    }


class Television(MXDeviceCategory):
    skills = {
        Skill.switch,
        Skill.tvChannel,
        Skill.audioMute,
        Skill.audioVolume,
    }


class TemperatureSensor(MXDeviceCategory):
    skills = {
        Skill.temperatureMeasurement,
    }


class TestDevice(MXDeviceCategory):
    skills = {
        Skill.testSkill,
    }


class Valve(MXDeviceCategory):
    skills = {
        Skill.valve,
    }


class WeatherProvider(MXDeviceCategory):
    skills = {
        Skill.weatherProvider,
    }


class Window(MXDeviceCategory):
    skills = {
        Skill.windowControl,
    }


class FallDetector(MXDeviceCategory):
    skills = {
        Skill.fallDetection,
    }


class FaceRecognizer(MXDeviceCategory):
    skills = {}


class CloudServiceProvider(MXDeviceCategory):
    skills = {}


class NewsProvider(MXDeviceCategory):
    skills = {}


class OccupancySensor(MXDeviceCategory):
    skills = {
        Skill.presenceSensor,
    }


class Relay(MXDeviceCategory):
    skills = {
        Skill.switch,
    }


class Timer(MXDeviceCategory):
    skills = {
        Skill.timer,
    }


####


class ManagerThing(MXDeviceCategory):
    skills = {
        Skill.manager,
    }


class SuperThing(MXDeviceCategory):
    skills = {}


class Undefined(MXDeviceCategory):
    skills = {}


if __name__ == '__main__':
    print(Window.skills)
