#!/usr/bin/python3

# Terrarium Class
import mysql.connector
#import os
#import glob
import logging
import time
from datetime import datetime
#, timedelta
import RPi.GPIO as GPIO

db = mysql.connector.connect(unix_socket="/var/run/mysqld/mysqld.sock",
    database='terrarium',
    user='USERNAME_HERE',
    password='PASSWORD_HERE')


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


def read_temp_raw(d):
    """
    read_temp_raw
      Reads the temperature probe device file and returns the raw temperature value
      d = 1-Wire device file
    """
    f = open(d, 'r')
    lines = f.readlines()
    f.close()
    return lines


def read_temp_c(p):
    """
    read_temp_c
      Returns the temperature from the probe in degrees celcius
      p = 1-Wire device file
    """
    lines = read_temp_raw(p)
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw(p)

    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_c = float(temp_string) / 1000.0
    return temp_c


def read_temp_f(p):
    """
    read_temp_f
      Returns the temperature from the probe in degrees farenheit
      p = 1-Wire device file
    """
    lines = read_temp_raw(p)
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw(p)

    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos + 2:]
        temp_f = temp_string * 9.0 / 5.0 + 32.0
    return temp_f


def get_temperature(measurement_format, device):
    """

    """
    base_dir = '/sys/bus/w1/devices/'
    device_folder = base_dir + device
    device_file = device_folder + '/w1_slave'

    if measurement_format == 'celsius':
        return read_temp_c(device_file)
    else:
        return read_temp_f(device_file)


def get_sensors():
    """
    get_sensors
    Retrieves a list of configured sensors from the Terrarium database
    """
    gs = []
    global last_config_read_time
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
        last_config_read_time = datetime.now()
        cursor.close()
        return gs
    except:
        raise


def get_locations():
    """
    get_locations
    Retrieves a list of cities, provinces, and countries from the database
    """
    c = []

    try:
        sql = """SELECT cities.id,
        cities.name AS `City`,
        countries.name AS `Country`,
        provinces.name AS `Province`
        FROM cities
        INNER JOIN countries ON countries.id = cities.country_id
        INNER JOIN provinces ON provinces.id = cities.province_id"""
        cursor = db.cursor()
        cursor.execute(sql)
        cities_results = cursor.fetchall()
        #print(sensor_results)
        for row_c in cities_results:
            ds = {"id": row_c[0], "city": row_c[1], "country": row_c[2], "province": row_c[3]}
            #print("Sensor {0} added".format(row_s[1]))
            c.append(ds)
        cursor.close()
        return c
    except:
        raise


def setup_gpio(device, gpio_pin):
    """
    setup_gpio
      Sets up the GPIO devices = heaters, lights, heat cables, etc
      device = name of device, used for debugging messages
      gpio_pin = the GPIO PIN (BCM value) the device is connected to on the RPi
    """
    debug_logging("Information",
        ("Setting up GPIO for {0} on PIN {1}".format(device, gpio_pin)))
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(int(gpio_pin), GPIO.OUT)


def get_config_values(value=None):
    """
    get_config_values
    Queries the configuration table in the database to return all values (when no value is passed to
    the definition) or a single value when a value is passed to the definition
    Vale = the name of a single value to query for
    """
    c = []
    try:
        if value is None:
            sql = 'SELECT id, name, value, comment FROM configuration'
        else:
            sql = 'SELECT id, name, value, comment FROM configuration WHERE name=\'{0}\''.format(value)

        cursor = db.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            d = {"id": row[0], "name": row[1], "value": row[2], "comment": row[3]}
            c.append(d)
        cursor.close()
        return c
    except:
        raise


def get_location_lat_long(loc):
    """

    """
    try:
        sql = 'SELECT `lat`, `long` FROM `cities` WHERE `id`={0}'.format(loc)
        #print(sql)
        cursor = db.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        for row in results:
            return row[0], row[1]
        cursor.close()
    except:
        raise