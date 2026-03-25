description = {
"AirConditioner":
'''Functions : [
    on(),
	off(),
    setTemperature(temperature: int),
    setAirConditionerMode(mode: string {"auto"|"cool"|"heat"})
]
Values : [
	switch : string {"on"|"off"},
    airConditionerMode : string {"auto"|"cool"|"heat"}
]
Tags : []''',

"AirPurifier":
'''Functions : [
    on(),
	off(),
    setAirPurifierFanMode(mode: string {"auto"|"sleep"|"low"|"medium"|"high"|"quiet"|"windFree"|"off"})
]
Values : [
	switch : string {"on"|"off"},
    airPurifierFanMode : string {"auto"|"sleep"|"low"|"medium"|"high"|"quiet"|"windFree"|"off"}
]
Tags : [
    livingroom
]''',

"AirQualityDetector":
'''Functions : []
Values : [
    dustLevel : int [0 ~ ∞] : PM 10 dust level,
    fineDustLevel : int [0 ~ ∞] : PM 2.5 finedust level,
    veryFineDustLevel : int [0 ~ ∞] : PM 1.0 finedust level,
    carbonDioxide : double : CO2 level,
    temperature : int [-460 ~ 10000],
    humidity : double [0 ~ 100],
    tvocLevel : double [0 ~ 1000000] : inert gas concentration
]
Tags : []''',



"Calculator":
'''Functions : [
    add(double, double) : return double,
    sub(double, double) : return double,
    div(double, double) : return double,
    mul(double, double) : return double,
    mod(double, double) : return double
]
Values : []
Tags : []''',

"Camera":
'''Functions : [
    on(),
	off(),
    take() : return binary : storage path for image(photo),
    takeTimelapse(duration: double [0 ~ ∞], speed: double [0 ~ ∞]) : return binary : storage path for timelapse
]
Values : [
	switch : string {"on"|"off"},
    image : binary : the storage path for the most recent image(photo)
]
Tags : []''',

"Clock":
'''Functions : []
Values : [
    day : int [1~31]
    hour : int [0~23]
    minute : int [0~59]
    month : int [1~12]
    second : int [0~59]
    weekday : string {"monday"|"tuesday"|"wednesday"|"thursday"|"friday"|"saturday"|"sunday"}
    year : int [0 ~ 100000]
    isHoliday : bool {true|false}
    timestamp : double : unixTime
]
Tags : []''',

"ContactSensor":
'''Functions : []
Values : [
    contact : string {"open"|"closed"}
]
Tags : []''',

"Curtain":
'''Functions : [
    setCurtainLevel(level: int [0 ~ 100])
]
Values : [
    curtain : string {"closed"|"closing"|"open"|"opening"|"partially"|"paused"|"unknown"},
    curtainLevel : int [0 ~ 100]
]
Tags : []''',

"EmailProvider":
'''Functions : [
    sendMail(toAddress: string , title: string , text: string),
    sendMailWithFile(toAddress: string, title: string, text: string, filePath: string)
]
Values : []
Tags : []''',

"Feeder":
'''Functions : [
    on(),
	off(),
    startFeeding(),
    setFeedPortion(portion: double [0 ~ 2000], unit: string {"grams"|"pounds"|"ounces"|"servings"})
]
Values : [
	switch : string {"on"|"off"},
    feederOperatingState : string {"idle"|"feeding"|"error"}
]
Tags : []''',

"HumiditySensor":
'''Functions : []
Values : [
    humidity : double[0 ~ 100]
]
Tags : []''',

"Light": '''Functions : [
    on(),
	off(),
	setColor(color: string {"{hue}|{saturation}|{brightness}"})
	setLevel(level int [0 ~ 100])
]
Values : [
	switch : string {"on"|"off"},
	light : double
]
Tags : [
    entrance,
    livingroom,
    bedroom
]''',

"MotionSensor":
'''Functions : []
Values : [
    motion : string {"active"|"inactive"}
]
Tags : []''',

"PresenceSensor":
'''Functions : []
Values : [
    presence : string {"present"|"not_present"}
]
Tags : []''',

"RobotCleaner":
'''Functions : [
    on(),
    off(),
    setRobotCleanerCleaningMode(string mode{"auto"|"part"|"repeat"|"manual"|"stop"|"map"})
]
Values : [
    switch : string {"on"|"off"},
    robotCleanerCleaningMode : string {"auto"|"part"|"repeat"|"manual"|"stop"|"map"}

]
Tags : [
    livingroom
]''',

"Siren":
'''Functions : [
    on(),
	off(),
    setSirenMode(mode: string {"both"|"off"|"siren"|"strobe"})
]
Values : [
	switch : string {"on"|"off"},
    sirenMode : string {"both"|"off"|"siren"|"strobe"}
]
Tags : []''',

"SmartPlug":
'''Functions : [
    on(),
	off()
]
Values : [
	switch : string {"on"|"off"},
    chargingState : string {"charging"|"discharging"|"stopped"|"fullyCharged"|"error"},
    voltage : double,
    current : double
]
Tags : []''',

"SoundSensor":
'''Functions : []
Values : [
    sound : string {"detected"|"not_detected"},
	soundPressureLevel : double [0 ~ 194]
]
Tags : []''',

"Speaker":
'''Functions : [
    on(),
	off(),
    pause(),
    stop(),
    play(source: string),
    speak(text: string)
]
Values : [
	switch : string {"on"|"off"},
    playbackStatus : string {"paused"|"playing"|"stopped"|"fast"|"rewinding"|"buffering"}
]
Tags : []''',

"Switch":
'''Functions : [
    on(),
	off()
]
Values : [
	switch : string {"on"|"off"}
]
Tags : []''',

"Television":
'''Functions : [
    on(),
	off(),
	setTvChannel(tvChannel: int),
	channelUp(),
	channelDown(),
    setVolume(volume: int [0 ~ 100]),
    volumeUp(),
    volumeDown(),
	mute() : void, toggle muteStatus

Values : [
	switch : string {"on"|"off"}
	muteStatus : string {"muted"|"unmuted"}
	tvChannel : int
]
Tags : []''',


"WeatherProvider":
'''Functions : [
    getWeatherInfo(double latitude, double longitude): return string {"thunderstorm"|"drizzle"|"rain"|"snow"|"mist"|"smoke"|"haze"|"dust"|"fog"|"sand"|"ash"|"squall"|"tornado"|"clear"|"clouds"}
]
Values : [
    weather : string {"thunderstorm"|"drizzle"|"rain"|"snow"|"mist"|"smoke"|"haze"|"dust"|"fog"|"sand"|"ash"|"squall"|"tornado"|"clear"|"clouds"},
	temperature : int celcius,
	humidity : double,
	pressure : double
]
Tags : []''',
}
