#!/usr/bin/python

import mysql.connector
import os
#import glob
import logging
import time
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
from sunrise_sunset import SunriseSunset
import terrariumlib as t

# Sleeping for 5 seconds, this is necessary for when the script is ran at
# reboot and MySQL hasn't started yet.  A more elegant solution would be
# to check if the MySQL process is running and if it isn't sleep
#time.sleep(5)

# Initiate 1-wire support for the temperature sensor probe
os.system('/sbin/modprobe w1-gpio')
os.system('/sbin/modprobe w1-therm')

db = mysql.connector.connect(unix_socket="/var/run/mysqld/mysqld.sock",
    database='terrarium',
    user='USERNAME_HERE',
    password='PASSWORD_HERE')

db.autocommit = True
last_config_read_time = datetime(2000, 1, 1, 12, 00)
configs = []
sensors = []
current_temperature = 0.00
config_max_temperature = 0.00
config_min_temperature = 0.00
config_night_max_temperature = 0.00
config_temperature_measurement = ""
config_curr_location = ""
config_sunrise = ""
config_sunset = ""
config_gpio_light = 0
config_gpio_heater = 0
last_heaterDisableTime = datetime.now() - timedelta(days=1)
last_heaterEnableTime = datetime.now() - timedelta(days=1)
heaterRecoveryTime = 0
isNightTime = ""


def cleanup():
    global config_gpio_heater
    global config_gpio_light

    debug_logging("Information", "Cleaning up heater GPIO")
    GPIO.output(int(config_gpio_heater), GPIO.LOW)

    debug_logging("Information", "Cleaning up light GPIO")
    GPIO.output(int(config_gpio_light), GPIO.LOW)


def debug_logging(severity, message, output="file"):
    """
    debug_logging
      Function to log debugging details to log file or stdout
      severity = the severity of the debug message. Should be Information, Debug, or Error
      message = the message to log
      output (default is file) = the output method, can be file or stdout
    """
    now = datetime.now()

    if output == "file":
        logging.basicConfig(filename='/home/pi/Terrarium/terrarium.log', level=logging.INFO)
        logging.info(("{0}: {1} - {2}".format(now.strftime("%Y-%m-%d %I:%M:%S %p"), severity, message)))
    else:
        print(("{0}: {1} - {2}".format(now.strftime("%Y-%m-%d %I:%M:%S %p"), severity, message)))
    return


def get_sensors():
    """

    """
    gs = []

    try:
        sql = 'SELECT id, name, folder_id FROM sensor WHERE isDeleted=0'
        cursor = db.cursor()
        cursor.execute(sql)
        sensor_results = cursor.fetchall()
        #print(sensor_results)
        for row_s in sensor_results:
            ds = {"id": row_s[0], "name": row_s[1], "folder_id": row_s[2]}
            #print("Sensor {0} added".format(row_s[1]))
            gs.append(ds)
        cursor.close()
        return gs
    except:
        raise


def temperature_insert(device_id, val):
    """

    """
    debug_logging("Information", ("Inserting sensor data - Sensor ID {0}, Temperature {1}".format(device_id, val)))
    try:
        sql = 'INSERT INTO `sensor_logging`(`sensor_id`, `data`) VALUES({:d},{:06.3f})'.format(device_id, val)
        #print(sql)
        cursor = db.cursor()
        cursor.execute(sql)
        db.commit()
        cursor.close()
    except:
        raise
        db.rollback()
        #db.close()


def get_configs():
    """
    get_configs
    Retrieves the configuration values from the database and stores them as global variables
    """
    global configs, sensors, config_curr_location, config_max_temperature
    global config_min_temperature, config_temperature_measurement
    global config_sunrise, config_sunset, config_gpio_heater
    global config_gpio_light, config_night_max_temperature, heaterRecoveryTime
    global last_config_read_time

    configs.clear()
    configs = t.get_config_values()
    for c in configs:
        if c["name"] == "Max Temperature":
            config_max_temperature = c["value"]

            debug_logging("Information",
                ("Max temperature value retrieved from database - {0}".format(c["value"])))

        if c["name"] == "Min Temperature":
            config_min_temperature = c["value"]

            debug_logging("Information",
                ("Min temperature value retrieved from database - {0}".format(c["value"])))

        if c["name"] == "Temperature Measurement":
            config_temperature_measurement = c["value"]

            debug_logging("Information",
                ("Temperatue Measurement value retrieved from database - {0}".format(c["value"])))

        if c["name"] == "Location":
            config_curr_location = c["value"]

            debug_logging("Information",
                ("Current Location ID value retrieved from database - {0}".format(c["value"])))

        if c["name"] == "Heater GPIO":
            config_gpio_heater = int(c["value"])

            debug_logging("Information",
                ("GPIO BCM PIN for the heat lamp value retrieved from database - {0}".format(c["value"])))

        if c["name"] == "Light GPIO":
            config_gpio_light = int(c["value"])

            debug_logging("Information",
                ("GPIO BCM PIN for the UV light value retrieved from database - {0}".format(c["value"])))

        if c["name"] == "Night Time Max Temperature":
            config_night_max_temperature = c["value"]

            debug_logging("Information",
                ("Maximum nightly temperature value retrieved from database - {0}".format(c["value"])))

        if c["name"] == "Heater Recovery Time":
            heaterRecoveryTime = c["value"]

            debug_logging("Information",
                ("Heater recovery time value retrieved from database - {0}".format(c["value"])))

        if c["name"] == "Sunrise":
            tempSunrise = c["value"]
        if c["name"] == "Sunset":
            tempSunset = c["value"]

    debug_logging("Information", "Retrieving latest sensor")
    sensors.clear()
    sensors = t.get_sensors()
    for s in sensors:
        debug_logging(
            "Information",
            (
                "Added Sensor ID: {0}, Sensor Name: {1}, Device ID: {2}"
                .format(s["id"], s["name"], s["folder_id"])
            )
        )

    if(config_curr_location != ""):
        curr_lat, curr_long = t.get_location_lat_long(config_curr_location)
        ro = SunriseSunset(datetime.now(), latitude=curr_lat, longitude=curr_long, localOffset=9.5)
        rise_time, set_time = ro.calculate()
        debug_logging("Information",
            ("The sun will rise at {0} and will set at {1} for the lcation {2}, {3}"
            .format(rise_time.strftime("%I:%M %p"), set_time.strftime('%I:%M %p'), curr_lat, curr_long)))

        config_sunrise = rise_time.strftime("%I:%M %p")
        config_sunset = set_time.strftime('%I:%M %p')
    else:
        config_sunrise = tempSunrise
        config_sunset = tempSunset

        debug_logging("Information",
            ("No location value retrieved from database, using database sunrise ({0}) and sunset ({1}) values"
            .format(tempSunrise, tempSunset)))

    last_config_read_time = datetime.now()


def process_light(sunrise, sunset, gpio_pin):
    """
    process_light
      Process the UV light, determine whether it should be on, off, or in a dimming state
      sunrise = the time of today's sunrise
      sunset = the time of today's sunset
      gpio_pin = the GPIO PIN (BCM value) the UV light is connected to
    """
    global isNightTime

    debug_logging(
        "Information",
        ("Determining whether it should off, on, or in a dimming state")
    )

    now = datetime.now()
    gpio_state = GPIO.input(gpio_pin)
    #now_epoch = time.mktime(now.timetuple())
    #sunrise_epoch = time.mktime(sunrise.timetuple())
    #sunset_epoch = time.mktime(sunset.timetuple())
    #timer = int(sunset_epoch - now_epoch) / 60

    debug_logging(
        "Information",
        ("The time now is {0}, today's sunrise is {1}, and today's sunset is {2}")
        .format(now.time(), sunrise.time(), sunset.time()))

    # If NOW is between sunset and sunrise, then it is night time
    if(sunrise.time() <= now.time() <= sunset.time()):
        debug_logging("Information", "Checking if Night Time...False")
        isNightTime = "false"
    else:
        debug_logging("Information", "Checking if Night Time...True")
        isNightTime = "true"

    debug_logging("Information", "The GPIO State for the UV Light on PIN {0} is {1}"
    .format(gpio_pin, gpio_state))

    if(isNightTime == "true" and gpio_state == 1):
        # It is night time and the light is on, turn it off
        debug_logging("Information", "It is night time and the light is on, turning it off")
        GPIO.output(gpio_pin, GPIO.LOW)
        gpio_state = GPIO.input(gpio_pin)
        debug_logging("Information",
            ("The current state of the UV light on GPIO Pin {0} is {1}".format(gpio_pin, gpio_state)))
    elif(isNightTime == "false" and gpio_state == 0):
        # It is day time and the light is off, turn it on
        debug_logging("Information", "It is day time and the light is off, turning it on")
        GPIO.output(gpio_pin, GPIO.HIGH)
        gpio_state = GPIO.input(gpio_pin)
        debug_logging("Information",
            ("The current state of the UV light on GPIO Pin {0} is {1}".format(gpio_pin, gpio_state)))
    else:
        debug_logging("Information",
            ("The UV light on GPIO Pin {0} is {1} is in a correct state, nothing to do")
            .format(gpio_pin, gpio_state))

    #if(gpio_state == 1):
        #debug_logging("Information",
            #("The current state of the UV light on GPIO Pin {0} is ON".format(gpio_pin)))
        ## If NOW is between sunset and sunrise, then turn off the light
        ## The UV Light is on, we'll now turn it off'
        #if(isNightTime == "true"):
            #GPIO.output(gpio_pin, GPIO.LOW)
            #gpio_state = GPIO.input(gpio_pin)
            #debug_logging("Information",
                #("The current state of the UV light on GPIO Pin {0} is {1}".format(gpio_pin, gpio_state)))

        ## If NOW is within 10 mins before sunset, then begin dimming light to 75% dimmed, calculate on
        ##    each pass the minutes between NOW and sunset and suitably decrement
        #elif(timer <= 10 and timer >= 0):

            #debug_logging("Information",
                #(
                    #("The current state of the UV light on GPIO Pin {0} is {1}, sunset is in " +
                    #"{2:.2f} minutes, begining to dim the light")
                #.format(gpio_pin, gpio_state, (int(sunset_epoch - now_epoch) / 60))))

            #### TO DO:

        ## If NOW is past sunset, turn off the light
        #elif(now > sunset):
            #GPIO.output(gpio_pin, GPIO.LOW)

            #debug_logging("Information",
                #(
                    #"It is past sunset, The UV light on GPIO Pin {0} has now been turned off"
                    #.format(gpio_pin)))

        ## Else, light is ON and should be ON, there is nothing to do
        #else:
            #debug_logging("Information",
                #(
                    #"The current state of the UV light on GPIO Pin {0} is {1}, there is nothing to do"
                    #.format(gpio_pin, gpio_state)))

    ## Else, light is OFF, check whether it should be ON
    #else:
        #debug_logging("Information",
            #("The current state of the UV light on GPIO Pin {0} is OFF".format(gpio_pin)))

        ## If NOW is between sunrise and sunset, then the light should be on
        #if(isNightTime == "false"):
            #GPIO.output(gpio_pin, GPIO.HIGH)
            #gpio_state = GPIO.input(gpio_pin)
            #debug_logging("Information",
                #("The current state of the UV light on GPIO Pin {0} is {1}".format(gpio_pin, gpio_state)))

        ## If NOW is within 10 minutes after sunrise, then begin brightening the light until it reaches 100%
        #elif(int(now_epoch - sunrise_epoch) / 60 <= 10):
            #debug_logging("Information",
                #("Sunrise is within 10 minutes, begining to brighten the light until sunrise is reached"))
            ##print((int(now_epoch - sunrise_epoch) / 60))

            #### TO DO:

        ## Else, light is OFF and should be OFF, there is nothing to do
        #else:
            #debug_logging("Information",
                #("The current state of the UV light on GPIO Pin {0} is {1}, there is nothing to do"
                    #.format(gpio_pin, gpio_state)))


def toggle_heater(status, gpio_pin):
    """
    toggle_heater
      Process to turn on or off the heat lamp
      status = ON|OFF - turn heater ON or OFF
      gpio_pin = the pin of the plugged in device
    """
    global last_heaterDisableTime
    global last_heaterEnableTime
    global heaterRecoveryTime

    gpio_state = GPIO.input(gpio_pin)
    debug_logging("Information",
        (
            "Processing heater status, turning {0} heater on GPIO PIN {1}, the device is currently {2}"
            .format(status, gpio_pin, gpio_state)))

    recoveryTime = last_heaterDisableTime + timedelta(seconds=300)

    # status = on, turning on heater
    if status == "on":

        # can't enable heater if it's already on
        if gpio_state == 1:
            debug_logging("Information", "Can't turn on the heater, it is already turned on")
        else:
            # Can't enable heater within the recovery time
            if (datetime.now() < recoveryTime):
                debug_logging("Warning",
                    ("Can't enable the heater, heater is in recovery.  Heater will be in recovery until {0}"
                    .format(recoveryTime)))

            # Enabling the heater
            debug_logging("Information", "Turning on the heater")

            GPIO.output(gpio_pin, GPIO.HIGH)
            last_heaterEnableTime = datetime.now()

            if GPIO.input(gpio_pin) == 1:
                debug_logging("Information", "Turned on the heater")
            else:
                debug_logging("Warning", "There was a problem turning on the heater, it hasn't turned on")

    # status = off, turning off the heater
    elif status == "off" and gpio_state == 1:
        debug_logging("Information", "Turning off the heater")

        GPIO.output(gpio_pin, GPIO.LOW)

        if GPIO.input(gpio_pin) == 0:
            debug_logging("Information", "Turned off the heater")
            last_heaterDisableTime = datetime.now()

        else:
            debug_logging("Warning",
                "There was a problem turning off the heater, it hasn't turned off")

    # heater is already off
    else:
        debug_logging("Information", "Heater is already off, there is nothing for me to do")


def process_temperature(temperature):
    """

    """
    global config_max_temperature
    global config_min_temperature
    global config_night_max_temperature
    global config_gpio_heater
    global isNightTime

    gpio_state = GPIO.input(int(config_gpio_heater))
    maxTemp = 0.00

    # Establish what the Max Temp should be, if night time then use the Max Night Temp
    debug_logging("Information",
        ("isNightTime = {0}, setting max temperature".format(isNightTime)))

    if (isNightTime == "true"):
        maxTemp = config_night_max_temperature

        debug_logging("Information",
            ("It is night time, setting the max temp to max night temp {0}".format(config_night_max_temperature)))

    else:
        maxTemp = config_max_temperature

        debug_logging("Information",
            ("It is day time, setting the max temp to max day temp {0}".format(config_max_temperature)))

    if ((temperature > float(maxTemp))
    and float(maxTemp) >= 0.00):
        debug_logging("Information",
            (
                "Current Temperature {0} exceeds the configured maximum temperature value of {1}"
                .format(temperature, maxTemp)))

        if gpio_state == 1:
            debug_logging("Information",
                ("Heater is ON, calling function to turn OFF the heater on GPIO Pin {0}"
                .format(int(config_gpio_heater))))

            toggle_heater("off", int(config_gpio_heater))

        else:
            debug_logging("Information",
                ("Heater is OFF, there is nothing to do but wait for the temperature to cool down"))

    # If sensor 1's current temperature is within range then there is nothing to do
    #    Also make sure the max OR minimum temperature is not 0.00
    elif ((float(config_min_temperature) <= temperature < float(maxTemp))
    and (float(config_min_temperature) > 0.00 or float(maxTemp) > 0.00)):
        debug_logging("Information",
            (
                """
                Current Temperature of {0} is within the acceptable temperature range,
                checking if heater has been off for long enough
                """
                .format(temperature, maxTemp)))

        toggle_heater("on", int(config_gpio_heater))

    # If sensor 1's current temperature is less than the minimum temp then turn on the heater
    elif (temperature <= float(config_min_temperature)
    and float(config_min_temperature) > 0.00):
        debug_logging("Information",
            (
                "Current Temperature of {0} is lower than the configured minimum temperature of {1}"
                .format(temperature, config_min_temperature)))

        if gpio_state == 0:
            debug_logging("Information",
                ("Heater is OFF, calling function to turn ON the heater on GPIO Pin {0}".
                format(int(config_gpio_heater))))

            toggle_heater("on", int(config_gpio_heater))

        else:
            debug_logging("Information",
                ("Heater is ON, there is nothing to do but wait for the temperature to warm-up"))

    # Else an unexpected condition has been encountered
    else:
        debug_logging("Warning",
            ("An unexpected condition has been encountered when evaluating sensor 1's temperature"))
        debug_logging("Warning",
            (
                "  Current Temperature {0}, Min Temperature {1}, Max Temperature {2}"
                .format(temperature, config_min_temperature, maxTemp)))

debug_logging("Information", "Application Started")

try:
    while True:
        now = datetime.now()
        now_minus_15 = now - timedelta(minutes=15)

        """
        Get the latest configuration values, this should only run every 15 minutes,
          that is so values can be changed while the
          application is running without needing to stop the application
        """
        if last_config_read_time < now_minus_15:
            debug_logging("Information", "Retrieving latest configuration values")
            get_configs()
            t.setup_gpio("UVLight", int(config_gpio_light))
            t.setup_gpio("Heater", int(config_gpio_heater))
        else:
            debug_logging("Information", "Config values retrieved already in the previous 15 minutes, exiting")

        # Check the status of the lights and whether they should be on or off, or be fading
        # Convert the string of the sunrise and sunset times from the DB into a datetime and prefix with today's date
        today_sunrise_time = datetime.strptime(config_sunrise, '%I:%M %p').time()
        today_sunrise = datetime.combine(now, today_sunrise_time)
        today_sunset_time = datetime.strptime(config_sunset, '%I:%M %p').time()
        today_sunset = datetime.combine(now, today_sunset_time)

        debug_logging("Information",
            ("Today's sunrise time is set for {0}".format(today_sunrise)))

        debug_logging("Information",
            ("Today's sunset time is set for {0}".format(today_sunset)))

        process_light(today_sunrise, today_sunset, int(config_gpio_light))

        """
        Get the latest temperature from the sensor(s), application will use
          the current list of sensors, which are retrieved
          every 15 minutes along with the latest configuration values
        """
        for r in sensors:
            current_temperature = t.get_temperature(config_temperature_measurement, r["folder_id"])

            debug_logging("Information",
                ("Current Temperature for {0} is {1}".format(r["name"], current_temperature)))

            temperature_insert(r["id"], current_temperature)

            # If sensor 1's current temp exceeds the set max temp then turn off the heater
            if r["name"] == "Sensor 1":
                debug_logging("Information",
                    ("Current sensor is {0} begin evaluation of temperature".format(r["name"])))
                process_temperature(current_temperature)

        #   Present the user with what the state should be, what it is, and when it will next change

        #   If state doesn't match what it should be, correct the light state
        #   If about to turn off (n -10) begin ramping light intensity down from 100% over the 10 minutes,
        #    or a reduction of 8% per minute, with the remaining 28% being turned off at "sunset"
        #   If time to turn on, begin ramping up by 8% until it reaches full intensity (about 13 minutes later)

        #    Finished processing work, sleeping for 1 minute
        debug_logging("Information", "Sleeping for 1 minute")
        time.sleep(60)

except KeyboardInterrupt:
    debug_logging("Information", "Quiting")
    cleanup()
    pass

except Exception as e:
    debug_logging("ERROR", str(e))
    pass