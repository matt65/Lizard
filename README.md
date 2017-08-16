# Lizzard
Lizzard Terrarium environment monitor

This project is to create a system to monitor the environment of our pet lizzard.  The aims of this project was to:

* Monitor the temperature on the hot and cold side of the enclosure
* Turn on and off the UV light according to the sunrise and sunset
* Maintain as close to a constant temperature as possible while also having a day time and night time temperature setting

This was my first foray into the world of Python, I quite enjoyed learning the language and really enjoyed developing this project.

I have had this code running for nearly a month, it has worked nicely and I am really happy with how well it is working.

This project consists of the Python code, which itself has the main program which queries two DS18B20 waterproof temperature probes to get regular temperature reads from the hot and cold sides and uses two PowerSwith SSR Tails to turn on and off the UV light and the heat lamp.
I have also developed a PCB to interface the temperature probes and SSR tails to the Raspberry Pi, it is my plan to eventually build an enclosure (or print one), this PCB has RJ12 modular ports to make connecting and disconneting the devices much easier and less pernament.

I wasn't able to achieve it in this initial release, but I would like to add AC Zero Cross support to this project so that I could use PID ( Proportional, Integrating and Different) to maintain an ideal temperature and perhaps cause less damage to the heat lamp and use less power, currently I am cycling on and off the heat lamp, which works OK.



http://www.powerswitchtail.com/powerssr-tail
https://www.adafruit.com/product/381
