### 1. Basic service specification

[ALL|OR|Space](#Tag1 ... #TagN).ServiceName

### 1-1. Service Qualifiers *Tag*

Qualifies service mapping candidates through a list of tags.

- Syntax: (#TAGNAME #TAGNAME2 ...)

### 1-2. Range qualifier *Range*

Limits the range of the final mapping if there are multiple mapping candidates.

1. service run
Default (blank): Pick one service and map it.
**ALL**: Map all satisfied services
2. check if conditions are met
Default (blank): True if all candidates satisfy the condition
**OR: True if at least one candidate satisfies the condition

Example service specification
```
(#camera #living_room).capture()
ALL(#camera).capture_with_timeout(10)
```


### 1-3. Assignment

Saves the result of the Function Service to a variable.

If you use the ALL Range qualifier, you cannot substitute.

```
img = (#camera).capture()
```

### 2. Loops

- LOOP (time)
- Time unit: HOUR / MIN / SEC

```cpp
loop (1 sec) {
	...
}
```

### 3. Conditional statements

- IF
- ELSE
```cpp
IF (x == 1) {
	...
} ELSE {
	...
}
```

### 4. Event trigger
- WAIT UNTIL
- Wait for an event to occur.

```
WAIT UNTIL (x == 1);
...
```

### 5. Script example
```
loop (1 SEC) {
  if((#env).sound > 100.0) {
    x = all(#door).take_picture()
    (#mail).send("admin", x)
    wait until(5 SEC)
    (#tts).speak("welcome")
  }
}
```


### Sample scenario

1. �ㅽ썑 6�쒓� �섎㈃, �댁뒪瑜� 諛쏆븘�� �쎌뼱以�
```
loop (24 HOUR)
{
	wait until( (#clock).hour == 18 )
  x = (#news).get_news()
	(#speaker).tts(x)
}
```
��
2. 1�쒓컙留덈떎 �좎뵪 �뚮젮以�
```
loop (1 HOUR)
{
	x = (#util).get_weather()
	(#speaker).tts(x)
}
```

3. �덈갑�� �ㅼ뼱�ㅻ㈃ 遺� 耳쒖쨾
```
loop (1 SEC)
{
  wait until ( (#living_room #movement).detected == 1 )
	(#living_room #light).turn_on()
}
```

4. �붿옱 媛먯��섎㈃, �뚮엺 �몃젮以�
```
loop (1 SEC)
{
  wait until ( (#fire).detected == 1 )
	(#speaker).alarm()
}
```

5. 鍮꾧� �ㅻ㈃, �섍컝 �� �뚮젮以�
```
loop (1 SEC)
{
	if ( (#door #movement).detected == 1 )
	{
		x = (#util).get_weather()
		if (x == "rainy")
		{
			(#door #speaker).tts("鍮� ����")
		}
	}
}
```

6. �щТ�ㅼ씠 �대몢�대뜲 ��吏곸엫�� 媛먯��섎㈃, 遺� 耳쒓퀬 �ъ쭊 李띿뼱�� 硫붿씪濡� 蹂대궡以�
```
loop (1 SEC)
{
	if ( (#office #movement).detected == 1 and (#office).brightness < 50 )
	{
		(#office #light).turn_on()
		x = (#office).take_picture()
		(#util).send_mail("��吏곸엫 媛먯�", x)
	}
}
```

7. �ㅽ썑 10�쒖뿉 �щ엺�� �놁쑝硫� 遺� �� 爰쇱쨾
```
loop (24 HOUR)
{
	wait until ( (#clock).HOUR == 22 and (#person).detected == 0 )
	all(#light).turn_off()
}
```

8. �뺤삤留덈떎 �먯떖 硫붾돱 媛��몄���, �쎌뼱二쇨퀬, 硫붿씪濡� 蹂대궡以�
```
loop (24 HOUR)
{
	wait until ( (#clock).HOUR == 12)
	x = (#util).get_lunch_menu()
	(#speaker).tts(x)
	(#util).send_mail("�먯떖 硫붾돱", x)
}
```

9. �뚯쓽�ㅼ씠 23�� �댄븯硫� �먯뼱而� �꾧퀬, 25�� �섏쑝硫� �먯뼱而� 耳쒖쨾
```
loop (30 SEC)
{
	if ( (#meeting_room).temperature <= 23 )
	{
		(#meeting_room #air_conditioner).turn_off()
	}
	else if ( (#meeting_room).temperature > 25 )
	{
		(#meeting_room #air_conditioner).turn_on()
	}
}
```

10. �� 諛� 癒쇱�媛� �덈Т 留롮쑝硫� 濡쒕큸泥�냼湲� �뚮젮以�
```
loop (10 SEC)
{
	if ( (#euiseok).dust > 100 )
	{
		(#euiseok #vacuum).start_cleaning()
	}
}
```


background knowledge : My email address is "ikess@gmail.com"
11. Let me know the weather every 1 hour
```
loop (1 HOUR)
{
	x = (#util).get_weather()
	(#speaker).tts(x)
}
```

12. If it rains, notify me �쒕퉬 ���붴�� when i am at door
```
loop (1 SEC)
{
	if ( (#door #movement).detected == 1 )
	{
		x = (#util).get_weather()
		if (x == "rainy")
		{
			(#door #speaker).tts("鍮� ����")
		}
	}
}
```

13. If the somewhere is dark and you detect movement, turn on the lights, take a picture, and email it to me.
```
loop (1 SEC)
{
	if ( (#somewhere #movement).detected == 1 and (#somewhere).brightness < 50 )
	{
		(#tag1 #somewhere #light).turn_on()
		x = (#somewhere).take_picture()
		(#util).send_with_file("ikess@gmail.com", "��吏곸엫 媛먯�", "�띿뒪��", x)
	}
}
```

14. Turn off the air conditioning when the room is below 23 degrees, turn it on when it's above 25 degrees.
```
loop (30 SEC)
{
	if ( (#tag1 #room).temperature <= 23 )
	{
		(#tag2 #meeting_room #air_conditioner).turn_off()
	}
	else if ( (#tag3 #meeting_room).temperature > 25 )
	{
		(#air_conditioner).turn_on()
	}
}
```

14. If my room is too dusty, return the robot vacuum.
```
loop (10 SEC)
{
	if ( (#euiseok).dust > 100 )
	{
		(#euiseok #vacuum).start_cleaning()
	}
}
``` 

15. If you detect movement between 12pm and 1pm, turn on the lights.
```
loop (10 SEC)
{
	if ( (#clock).HOUR >= 12 and (#clock).HOUR <= 13 and (#movement).detected == 1)
	{
		(#euiseok #light).turn_on()
	}
}
```
16. dummy
```
loop (1 HOUR)
{
	if ( (#tag1).service1 >= 12 and (#tag2).service2 <= 13 )
	{
		(#tag3 #tag4).servic3()
	}

	x = (#tag5).servic4(arg1, arg2)
	(#tag6).servic5("test", x)
	wait until((#tag7).service6 == 100);
}
```

17. dummy
```��
loop (1 HOUR)
{
    if ((#MovementSensor_0CD02FA8CC84).movement and (#clock).hour >= 13 and (#clock).hour < 14)
    {
        (#camera).capture();
        (#email).send_with_file(address="you@yourmail.com", title="Movement detected!", text="Please see the attached photo.", file="photo.jpg");
        (#Hue_color_lamp_1).on();
    }
    wait until((#clock).minute == 0);
}
```


### Templates
This is Template of SoP lang.  
- `%%%` should be replaced with a tag in the service list.  
- `$$$` should be replaced with a service in the service list.
``` 
loop (3 SEC)
{
	if ( (#%%% #%%%).$$$ == 1 and (#%%%).$$$ < 50 )
	{
		(#%%% #%%%).$$$()
		x = (#%%%).$$$()
		(#%%%).$$$("string_param1", "string_param2", "string_param3", x)
	}
}
```
```
loop (2 SEC)
{
	if ( (#%%% #%%%).$$$ == 1)
	{
		(#%%%).$$$()
	}
}
```
```
loop (1 MIN)
{
	if ( (#%%%).$$$ == 1)
	{
		(#%%% #%%%).$$$("string_param1")
	}
}
```
