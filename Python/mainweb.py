#!/usr/bin/python3

import time
from datetime import datetime, timedelta
import logging
#import hashlib
#import config as c
import RPi.GPIO as GPIO
import terrariumlib as t
from sunrise_sunset import SunriseSunset
from flask import Flask, flash, redirect, request, render_template, url_for, session, escape

#https://bitbucket.org/MattHawkinsUK/rpispy-pool-monitor/
#src/748ad80b7331c9f9d7803273bc42356ad376c09f/poollib.py?at=master&fileviewer=file-view-default

mySensorIDs = []
configs = []
#myPumpMode = ''
#myPumpStatus = False
current_temperature = 0.00
config_max_temperature = 0.00
config_min_temperature = 0.00
config_night_max_temperature = 0.00
config_temperature_measurement = ""
config_curr_location = ""
config_sunrise = ""
config_sunset = ""
config_tomorrow_sunrise = ""
config_tomorrow_sunset = ""
config_gpio_light = 0
config_gpio_heater = 0
heaterRecoveryTime = 0
desc_curr_location = ""
desc_max_temperature = ""
desc_min_temperature = ""
desc_temperature_measurement = ""
desc_sunrise = ""
desc_sunset = ""
desc_gpio_heater = ""
desc_gpio_light = ""
desc_night_max_temperature = ""
desc_heaterRecoveryTime = ""
desc_tomorrow_sunrise = ""
desc_tomorrow_sunset = ""
desc_tempSunrise = ""
desc_tempSunset = ""

# Default username and password hash
# Use hashgenerator.py in utils to create hash for your password
USERNAME = 'admin'
USERHASH = 'c7f9e589934a99848f2dba75a70b49dca6149988730389671d730e9376701adf'

# Flask needs a secret key or phrase to handle login cookie
FLASKSECRET = '7e8031df78fd55cba971df8d9f5740be'

app = Flask(__name__)
app.secret_key = FLASKSECRET


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
        logging.basicConfig(filename='/home/pi/Terrarium/terrariumweb.log', level=logging.INFO)
        logging.info(("{0}: {1} - {2}".format(now.strftime("%Y-%m-%d %I:%M:%S %p"), severity, message)))
    else:
        print(("{0}: {1} - {2}".format(now.strftime("%Y-%m-%d %I:%M:%S %p"), severity, message)))
    return


def get_configs():
    """
    get_configs
    Retrieves the configuration values from the database and stores them as global variables
    """
    global configs, sensors, config_curr_location, config_max_temperature
    global config_min_temperature, config_temperature_measurement
    global config_sunrise, config_sunset, config_gpio_heater
    global config_gpio_light, config_night_max_temperature, heaterRecoveryTime
    global config_tomorrow_sunrise, config_tomorrow_sunset
    global desc_curr_location, desc_max_temperature
    global desc_min_temperature, desc_temperature_measurement
    global desc_sunrise, desc_sunset, desc_gpio_heater
    global desc_gpio_light, desc_night_max_temperature, desc_heaterRecoveryTime
    global desc_tomorrow_sunrise, desc_tomorrow_sunset, desc_tempSunrise, desc_tempSunset

    configs.clear()
    configs = t.get_config_values()
    for c in configs:
        if c["name"] == "Max Temperature":
            config_max_temperature = c["value"]
            desc_max_temperature = c["comment"]

        if c["name"] == "Min Temperature":
            config_min_temperature = c["value"]
            desc_min_temperature = c["comment"]

        if c["name"] == "Temperature Measurement":
            config_temperature_measurement = c["value"]
            desc_temperature_measurement = c["comment"]

        if c["name"] == "Location":
            config_curr_location = c["value"]
            desc_curr_location = c["comment"]

        if c["name"] == "Heater GPIO":
            config_gpio_heater = int(c["value"])
            desc_gpio_heater = c["comment"]

        if c["name"] == "Light GPIO":
            config_gpio_light = int(c["value"])
            desc_gpio_light = c["comment"]

        if c["name"] == "Night Time Max Temperature":
            config_night_max_temperature = c["value"]
            desc_night_max_temperature = c["comment"]

        if c["name"] == "Heater Recovery Time":
            heaterRecoveryTime = c["value"]
            desc_heaterRecoveryTime = c["comment"]

        if c["name"] == "Sunrise":
            tempSunrise = c["value"]
            desc_tempSunrise = c["comment"]

        if c["name"] == "Sunset":
            tempSunset = c["value"]
            desc_tempSunset = c["comment"]

    debug_logging("Information", "Retrieving latest sensor")
    #sensors.clear()
    #sensors = t.get_sensors()
    #for s in sensors:
        #debug_logging(
            #"Information",
            #(
                #"Added Sensor ID: {0}, Sensor Name: {1}, Device ID: {2}"
                #.format(s["id"], s["name"], s["folder_id"])
            #)
        #)

    if(config_curr_location != ""):
        curr_lat, curr_long = t.get_location_lat_long(config_curr_location)
        ro = SunriseSunset(datetime.now(), latitude=curr_lat, longitude=curr_long, localOffset=9.5)
        rise_time, set_time = ro.calculate()
        config_sunrise = rise_time.strftime("%I:%M %p")
        config_sunset = set_time.strftime('%I:%M %p')

        debug_logging("Information",
            ("The sun will rise at {0} and will set at {1} for the lcation {2}, {3}"
            .format(rise_time.strftime("%I:%M %p"), set_time.strftime('%I:%M %p'), curr_lat, curr_long)))

        ro = SunriseSunset(datetime.now() + timedelta(days=1),
            latitude=curr_lat, longitude=curr_long, localOffset=9.5)
        rise_time, set_time = ro.calculate()
        config_tomorrow_sunrise = rise_time.strftime("%I:%M %p")
        config_tomorrow_sunset = set_time.strftime('%I:%M %p')
    else:
        config_sunrise = tempSunrise
        config_sunset = tempSunset

        debug_logging("Information",
            ("No location value retrieved from database, using database sunrise ({0}) and sunset ({1}) values"
            .format(tempSunrise, tempSunset)))


@app.route('/')
def index():
    global mySensorIDs, config_temperature_measurement

    #if 'username' in session:
    if len(mySensorIDs) > 0:
        temp1 = round(t.get_temperature(config_temperature_measurement, mySensorIDs[0]["folder_id"]), 1)
        if len(mySensorIDs) > 1:
            temp2 = round(t.get_temperature(config_temperature_measurement, mySensorIDs[1]["folder_id"]), 1)

    timeStamp = '{0:%Y-%m-%d %H:%M:%S}'.format(datetime.now())
    nowTime = datetime.now()

    if(config_temperature_measurement == "celsius"):
        tempMeasurement = "C"
    else:
        tempMeasurement = "F"

    gpio_light_state = GPIO.input(config_gpio_light)
    gpio_heat_state = GPIO.input(config_gpio_heater)

    if gpio_light_state == 0:
        light_icon = "lightOff.png"
    else:
        light_icon = "lightOn.png"

    if gpio_heat_state == 0:
        heater_icon = "heaterOff.jpg"
    else:
        heater_icon = "heaterOn.jpg"

    if nowTime.strftime("%I:%M %p") > config_sunrise:
        next_sunrise = config_tomorrow_sunrise
    else:
        next_sunrise = config_sunrise

    if nowTime.strftime("%I:%M %p") > config_sunset:
        next_sunset = config_tomorrow_sunset
    else:
        next_sunset = config_sunset

    if 'username' in session:
        user = escape(session['username'])
    else:
        user = ""

    data = {'t1': temp1,
        't2': temp2,
        'tempMeasurement': tempMeasurement,
        'lightStatus': light_icon,
        'heaterStatus': heater_icon,
        'sunrise': next_sunrise,
        'sunset': next_sunset,
        'ts': timeStamp,
        'user': user}
    return render_template('index.html', data=data)
    #else:
        #return redirect(url_for('login'))


@app.route('/settings/', methods=['GET', 'POST'])
def settings():
    #global mySensorIDs, myPumpStatus, myPumpMode

    configs = get_configs()
    locations = t.get_locations()

    if 'username' in session:
        user = escape(session['username'])
    else:
        user = ""

    if heaterRecoveryTime:
        heaterRecoveryMins = int(int(heaterRecoveryTime) / 60)

    data = {'user': user,
            'configs': configs,
            'tempMeasurement': config_temperature_measurement,
            'descTempMeasurement': desc_temperature_measurement,
            'minTemperature': config_min_temperature,
            'descMinTemperature': desc_min_temperature,
            'maxTemperature': config_max_temperature,
            'descMaxTemperature': desc_max_temperature,
            'location': config_curr_location,
            'descLocation': desc_curr_location,
            'sunrise': config_sunrise,
            'descSunrise': desc_sunrise,
            'sunset': config_sunset,
            'descSunset': desc_sunset,
            'heaterGPIO': config_gpio_heater,
            'descHeaterGPIO': desc_gpio_heater,
            'lightGPIO': config_gpio_light,
            'descLightGPIO': desc_gpio_light,
            'maxNightTemp': config_night_max_temperature,
            'descMaxNightTemp': desc_night_max_temperature,
            'heaterRecoveryMins': str(heaterRecoveryMins),
            'descHeaterRecoveryMins': desc_heaterRecoveryTime,
            'locations_list': locations}

    #if request.method == 'POST':
        #p.saveSchedule(myHours)
        #flash('Schedule saved', 'info')

    return render_template('settings.html', data=data)


@app.route('/debug/')
def debug():
    global mySensorIDs, myPumpStatus, myPumpMode
    temp1, temp2 = t.get_temperature(config_temperature_measurement, mySensorIDs)
    #hours = p.getSchedule()
    timeStamp = '{0:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
    data = {'id1': mySensorIDs[0],
          'id2': mySensorIDs[1],
          't1': temp1,
          't2': temp2,
          #'pm': myPumpMode,
          #'ps': myPumpStatus,
          #'hrs': hours,
          'ts': timeStamp
         }
    return render_template('debug.html', data=data)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get username and password from submitted form
        userName = escape(request.form['username'])
        #passWord = escape(request.form['password'])
        # Convert password to hash and compare to stored hash
        #passWordHash = hashlib.sha256(passWord.encode('utf-8')).hexdigest()
        if userName == USERNAME:
            # and passWordHash == USERHASH:
            session['username'] = 'admin'
            return redirect(url_for('index'))
        else:
            time.sleep(2)
            session.pop('username', None)
            flash('Sorry. Better luck next time.', 'danger')
    else:
        flash('Please enter your details.', 'info')
    return render_template('login.html')


@app.route('/logout')
def logout():
    # Remove username from the session
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    get_configs()
    t.setup_gpio("UVLight", int(config_gpio_light))
    t.setup_gpio("Heater", int(config_gpio_heater))
    mySensorIDs = t.get_sensors()
    #myPumpMode, myPumpStatus = p.getStatus()
    app.run(host='0.0.0.0', debug=True)