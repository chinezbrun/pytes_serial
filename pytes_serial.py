#!/usr/bin/env python
import logging
from logging.handlers import RotatingFileHandler
import serial
import time, datetime
import json
import mysql.connector as mariadb
from configparser import ConfigParser
import paho.mqtt.publish as publish
import re

# -------------------- VARIABLES INITIALIZATION ---------------------
config                = ConfigParser()
config.read('pytes_serial.cfg')
serial_port           = config.get('serial', 'serial_port')
serial_baudrate       = int(config.get('serial', 'serial_baudrate'))
reading_freq          = int(config.get('serial', 'reading_freq'))
output_path           = config.get('general', 'output_path')
powers                = int(config.get('battery_info', 'powers'))
cells                  = int(config.get('battery_info', 'cells'))
dev_name              = config.get('battery_info', 'dev_name')
manufacturer          = config.get('battery_info', 'manufacturer')
model                 = config.get('battery_info', 'model')
sw_ver                = "PytesSerial v2.0.0_20260805"
version               = sw_ver

SQL_active            = config.get('Maria DB connection', 'SQL_active')
host                  = config.get('Maria DB connection', 'host')
db_port               = config.get('Maria DB connection', 'db_port')
user                  = config.get('Maria DB connection', 'user')
password              = config.get('Maria DB connection', 'password')
database              = config.get('Maria DB connection', 'database')

MQTT_active           = config.get('MQTT', 'MQTT_active')
MQTT_broker           = config.get('MQTT', 'MQTT_broker')
MQTT_port             = int(config.get('MQTT', 'MQTT_port'))
MQTT_username         = config.get('MQTT', 'MQTT_username')
MQTT_password         = config.get('MQTT', 'MQTT_password')

LOGGING_LEVEL          = config.get('logging', 'LOGGING_LEVEL')
log_level_info = {'logging.DEBUG': logging.DEBUG,
                'logging.INFO': logging.INFO,
                'logging.WARNING': logging.WARNING,
                'logging.ERROR': logging.ERROR,
                }
LOGGING_LEVEL_FILE     = (log_level_info[LOGGING_LEVEL])
LOGGING_FILE_MAX_SIZE  = int(config.get('logging', 'LOGGING_FILE_MAX_SIZE'))
LOGGING_FILE_MAX_FILES = int(config.get('logging', 'LOGGING_FILE_MAX_FILES'))

cells_monitoring       = config.get('cells_monitoring', 'cells_monitoring')
cells_mon_level        = config.get('cells_monitoring', 'monitoring_level')

start_time            = time.time()                           # initialization time
up_time               = time.time()                           # used to calculate uptime
pwr                   = []                                    # used to serialize JSON data
bat                   = []                                    # used to record cells data -- def parse_bat
bats                  = []                                    # used to serialize JSON data -- def check_cells
loops_no              = 0                                     # used to count number of loops and to calculate % of errors
errors_no             = 0                                     # used to count number of errors and to calculate %
trials                = 0                                     # used to improve data reading accuracy -- def parse_pwr
errors                = 'false'
line_str_array        = []                                    # type: list[str] # used to get line strings from serial
END_MARKERS           = [ "PYTES>" , "PYTES_debug>" , "pylon>" , "pylon_debug>",] # used for end of transmition

print("software version:",version)

# -------------------- LOGGING DEFINITION ---------------------------
formatter = logging.Formatter('%(asctime)s| %(levelname)7s| %(message)s ',datefmt='%Y%m%d %H:%M:%S')   # logging formatting
def setup_logger(name, log_file, level=LOGGING_LEVEL_FILE):

    """To setup as many loggers as you want"""
    handler = RotatingFileHandler(log_file, mode='a', maxBytes=LOGGING_FILE_MAX_SIZE*1000, backupCount=LOGGING_FILE_MAX_FILES, encoding=None, delay=False)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

pytes_serial_log    = setup_logger('pytes_serial', 'pytes_serial.log')

# -------------------- FUNCTIONS ------------------------------------
def write_serial(req, size):
    try:
        loop_time     = time.time()
        recovery_used = False

        if ser.is_open != True:
            ser.open()
            time.sleep(0.5)
            print('...open serial')

        bytes_req = bytes(str(req), 'latin-1')

        # Normal command
        ser.write(bytes_req + b'\n')
        ser.flush()

        # Wait up to 0.5 s for normal response
        while (time.time() - loop_time) < 0.5:
            if ser.in_waiting > size:
                return "true"

            time.sleep(0.005)

        # Recovery
        while True:
            if ser.in_waiting > size:
                return "true"

            elif (time.time() - loop_time) > 1.2:
                return "false"

            elif (
                ser.in_waiting < 100
                and (time.time() - loop_time) > 0.8
            ):
                if recovery_used == False:
                    recovery_used = True

                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.write(bytes_req + b'\n')
                ser.flush()
                time.sleep(0.3)

            else:
                if recovery_used == False:
                    recovery_used = True
                    ser.write(b'\n')

                time.sleep(0.1)

    except Exception as e:
        print('...serial write error: ' + str(e))
        pytes_serial_log.warning(
            'SERIAL WRITE - error handling message: ' + str(e)
        )

def read_serial(start, stop):
    try:
        global line_str_array

        raw_bytes      = b''
        line_str_array = []

        idle_timeout  = 0.2
        total_timeout = 5.0

        if ser.is_open != True:
            ser.open()
            time.sleep(0.5)
            print('...open serial')

        if stop != 'none':
            stop_bytes = [marker.encode('latin-1') for marker in stop]
        else:
            stop_bytes = []

        start_time     = time.monotonic()
        last_data_time = None

        while True:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)

                raw_bytes += data
                last_data_time = time.monotonic()

                # Exit immediately when an end marker is detected.
                if stop != 'none':
                    if any(marker in raw_bytes for marker in stop_bytes):
                        break

            else:
                # Used only to drain the input buffer.
                # Exit only after the line stayed quiet for idle_timeout.
                if start == 'none' and stop == 'none':

                    now = time.monotonic()

                    if last_data_time is None:
                        last_data_time = now

                    elif now - last_data_time >= idle_timeout:
                        break

            now = time.monotonic()

            # No new data received for idle_timeout seconds.
            if last_data_time != None:
                if now - last_data_time >= idle_timeout:
                    break

            # Safety timeout.
            if now - start_time >= total_timeout:
                break

            time.sleep(0.005)

        # Split the response into lines.
        # Keep the last fragment even if it has no '\n'
        # (e.g. "PYTES>").
        parts = raw_bytes.split(b'\n')

        start_found = start == 'none'
        stop_found  = stop  == 'none'

        for i, part in enumerate(parts):
            if i < len(parts) - 1:
                line_str = (part + b'\n').decode('latin-1')
            elif part:
                line_str = part.decode('latin-1')
            else:
                continue
            if start != 'none' and start in line_str:
                start_found = True

            if start_found:
                line_str_array.append(line_str)

            if stop != 'none':
                if any(marker in line_str for marker in stop):
                    stop_found = True

        if start_found and stop_found:
            if start != 'none':
                print(
                    '...reading complete, start:', start,
                    'bytes:', len(raw_bytes),
                    'time:', round(time.monotonic() - start_time, 3)
                )
            return 'true'

        pytes_serial_log.debug(
            'SERIAL READ - incomplete response'
            + ' start_found:' + str(start_found)
            + ' stop_found:' + str(stop_found)
            + ' bytes:' + str(len(raw_bytes))
            + ' raw_bytes:' + repr(raw_bytes)
            + ' line_str_array:' + str(line_str_array)
        )

        return 'false'

    except Exception as e:
        print('...serial read error: ' + str(e))

        pytes_serial_log.warning(
            'SERIAL READ - error handling message: ' + str(e)
        )

        pytes_serial_log.debug(
            'SERIAL READ - line_str_array: ' + str(line_str_array)
        )

        line_str_array = []

        return 'false'

def parse_pwr():
    try:
        global line_str_array
        global errors
        global trials
        global pwr

        data_set           = 0
        pwr                = []
        line_str_array_bak = []

        req       = 'pwr'
        start     = 'Power Volt'
        size      = 800
        rw_trials = 0

        while True:
            write_return = write_serial(req, size)

            if write_return == 'true':
                read_return = read_serial(start, END_MARKERS)

                if line_str_array and read_return == 'true':
                    rw_trials = 0
                    break

            rw_trials = rw_trials + 1
            buffer = ser.in_waiting

            if rw_trials <= 5:
                read_serial('none', 'none')

                if write_return != 'true':
                    rw_failure = 'write:false'
                else:
                    rw_failure = 'read:false'

                pytes_serial_log.debug(
                    'PARSING PWR - pwr ' + rw_failure
                    + ' rw_trial:' + str(rw_trials)
                    + ' err_no:' + str(errors_no)
                    + ' in_buffer:' + str(buffer)
                )

                line_str_array = []

            else:
                errors = 'true'

                print('...timeouts -> close serial, skip set')

                pytes_serial_log.error(
                    'PARSING PWR - pwr'
                    + ' rw_trial:' + str(rw_trials)
                    + ' err_no:' + str(errors_no)
                    + ' timeouts -> close serial in_buffer:' + str(buffer)
                    + ' line_str_array:' + str(line_str_array)
                )

                if ser.is_open == True:
                    ser.close()

                return

        line_str_array_bak = line_str_array

        power_idx     = -1
        volt_idx      = -1
        curr_idx      = -1
        temp_idx      = -1
        basic_st_idx  = -1
        volt_st_idx   = -1
        curr_st_idx   = -1
        temp_st_idx   = -1
        soc_idx       = -1
        header_valid  = False

        for i, line_str in enumerate(line_str_array):

            if line_str.strip().startswith('Command completed'):
                break

            # First line is the pwr table header.
            # split() is used because Pytes/Pylontech headers do not always
            # use two spaces between every column name.
            if i == 0:
                line = line_str.strip().split()

                for j, value in enumerate(line):
                    if value == 'Power':
                        power_idx = j
                    elif value == 'Volt':
                        volt_idx = j
                    elif value == 'Curr':
                        curr_idx = j
                    elif value == 'Tempr':
                        temp_idx = j
                    elif value == 'Base.St':
                        basic_st_idx = j
                    elif value == 'Volt.St':
                        volt_st_idx = j
                    elif value == 'Curr.St':
                        curr_st_idx = j
                    elif value == 'Temp.St':
                        temp_st_idx = j
                    elif value == 'Coulomb':
                        soc_idx = j

                if (
                    power_idx != -1
                    and volt_idx != -1
                    and curr_idx != -1
                    and temp_idx != -1
                    and basic_st_idx != -1
                    and volt_st_idx != -1
                    and curr_st_idx != -1
                    and temp_st_idx != -1
                    and soc_idx != -1
                ):
                    header_valid = True
                else:
                    break

            else:
                if header_valid != True:
                    break

                line = line_str.strip().split()

                if not line or not line[0].isdigit():
                    continue

                power = int(line[power_idx])

                if power > powers:
                    continue

                if power != data_set + 1:
                    break

                if line[basic_st_idx] == 'Absent':
                    break

                try:
                    voltage    = round(int(line[volt_idx]) / 1000, 2)
                    current    = round(int(line[curr_idx]) / 1000, 2)
                    temp       = round(int(line[temp_idx]) / 1000, 1)
                    soc        = int(line[soc_idx].replace('%', ''))
                except ValueError as e:
                    pytes_serial_log.debug(
                        'PARSING PWR - pwr invalid data: ' + str(e)
                    )
                    break

                basic_st   = line[basic_st_idx]
                volt_st    = line[volt_st_idx]
                current_st = line[curr_st_idx]
                temp_st    = line[temp_st_idx]

                print('power           :', power)
                print('voltage         :', voltage)
                print('current         :', current)
                print('temperature     :', temp)
                print('soc [%]         :', soc)
                print('basic_st        :', basic_st)
                print('volt_st         :', volt_st)
                print('current_st      :', current_st)
                print('temp_st         :', temp_st)
                print('---------------------------')

                pwr_array = {
                    'power': power,
                    'voltage': voltage,
                    'current': current,
                    'temperature': temp,
                    'soc': soc,
                    'basic_st': basic_st,
                    'volt_st': volt_st,
                    'current_st': current_st,
                    'temp_st': temp_st
                }

                data_set = data_set + 1
                pwr.append(pwr_array)

        if data_set == powers:
            statistics()
            errors = 'false'
            trials = 0

            print('...serial parsing: ok')

        else:
            errors = 'true'
            trials = trials + 1

            if trials <= 3:
                print('...incomplete data sets -> try again')
                pytes_serial_log.debug(
                    'PARSING PWR - trial:' + str(trials)
                    + ' err_no:' + str(errors_no)
                    + ' incomplete data sets data_set:' + str(data_set)
                    + ' line_str_array:' + str(line_str_array_bak)
                )

                parse_pwr()

            else:
                print('...incomplete data set -> not solved, close serial, skip set')
                pytes_serial_log.error(
                    'PARSING PWR - trial:' + str(trials)
                    + ' err_no:' + str(errors_no)
                    + ' incomplete data sets:' + str(data_set)
                    + ' line_str_array:' + str(line_str_array_bak)
                )

                if ser.is_open == True:
                    ser.close()

                return

    except Exception as e:
        errors = 'true'

        print('...PARSING PWR error: ' + str(e))
        pytes_serial_log.error('PARSING PWR - error handling message: '+str(e))

        if ser.is_open == True:
            ser.close()
            print('...close serial')

        return

def statistics():
    try:
        global sys_voltage
        global sys_current
        global sys_soc
        global sys_temp
        global sys_basic_st
        sys_voltage  = 0
        sys_current  = 0
        sys_soc      = 0
        sys_temp     = 0
        sys_basic_st = ""

        for power in range (1, powers+1):
            sys_voltage       = sys_voltage + pwr[power-1]['voltage']               # voltage will be the average of all batteries
            sys_current       = round((sys_current + pwr[power-1]['current']),1)    # current will be sum of all banks
            sys_soc           = sys_soc + pwr[power-1]['soc']                       # soc will be the average of all batteries
            sys_temp          = sys_temp + pwr[power-1]['temperature']              # temperature will be the average of all batteries

        sys_voltage  = round((sys_voltage / powers), 1)
        sys_soc      = int(sys_soc / powers)
        sys_basic_st = pwr[0]['basic_st']                                           # status will be the master status
        sys_temp     = round((sys_temp / powers), 1)

    except Exception as e:
        errors = 'true'
        print('...json serialization error: ' + str(e))

def serialize_json():
    try:
        global parsing_time
        global loops_no
        global errors_no
        global errors
        global json_data
        global json_data_old
        global bats

        json_data_old = json_data
        json_data={'relay_local_time':TimeStamp,
                   'powers' : powers,
                   'voltage': sys_voltage,
                   'current': sys_current,
                   'temperature': sys_temp,
                   'soc': sys_soc,
                   'basic_st': sys_basic_st,
                   'devices':pwr,
                   'cells_data':bats,
                   'serial_stat': {'uptime':uptime,
                                   'loops':loops_no,
                                   'errors': errors_no,
                                   'efficiency' :round((1-(errors_no/loops_no))*100,2),
                                   'ser_round_trip':round(parsing_time,2)}
                   }

        with open(output_path + dev_name + '_status.json', 'w') as outfile:
            json.dump(json_data, outfile)
        print('...json creation:  ok')

    except Exception as e:
        print('...json serialization error: ' + str(e))
        pytes_serial_log.error('JSON SERIALIZATION - error handling message: ' + str(e))

        errors = 'true'

def write_mariadb():
    try:
        mydb = mariadb.connect(host=host,port=db_port,user=user,password=password,database=database)

        for power in range (1, powers+1):
            values= (pwr[power-1]['power'],
                     pwr[power-1]['voltage'],
                     pwr[power-1]['current'],
                     pwr[power-1]['temperature'],
                     pwr[power-1]['soc'],
                     pwr[power-1]['basic_st'],
                     pwr[power-1]['volt_st'],
                     pwr[power-1]['current_st'],
                     pwr[power-1]['temp_st'])

            sql="INSERT INTO pwr_data\
            (power,\
            voltage,current,\
            temperature,\
            soc,\
            basic_st,\
            volt_st,\
            current_st,\
            temp_st) \
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            mycursor = mydb.cursor()
            mycursor.execute(sql, values)
            mydb.commit()

        mycursor.close()
        mydb.close()
        print('...mariadb upload: ok')

    except Exception as e:
        print('...mariadb writing error: '+ str(e))
        pytes_serial_log.warning('MARIADB WRITING - error handling message: '+ str(e))

def mqtt_discovery():
    try:
        config    = 1
        max_config= 0
        msg       = {}
        MQTT_auth = None   # type: publish.AuthParameter | None

        if len(MQTT_username) > 0:
            MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }

        # define system sensors
        names        =["current",       "voltage" ,     "temperature",  "soc",          "status"]
        ids          =["current",       "voltage" ,     "temperature",  "soc",          "basic_st"]
        dev_cla      =["current",       "voltage",      "temperature",  "battery",      None]
        stat_cla     =["measurement",   "measurement",  "measurement",  "measurement",  None]
        unit_of_meas =["A",             "V",            "°C",           "%",            None]
        precision    =[2,               2,              1,              0,              None]

        max_config   = max_config + len(ids)

        for n in range(len(ids)):
            msg ["uniq_id"]      = dev_name + "_" + ids[n]
            state_topic          = "homeassistant/sensor/" + dev_name + "/" + msg["uniq_id"] + "/config"
            msg ["name"]         = names[n]
            msg ["stat_t"]       = "pytes_serial/" + dev_name + "/" + ids[n]
            if dev_cla[n]  != None:
                msg ["dev_cla"]  = dev_cla[n]
            if stat_cla[n] != None:
                msg ["stat_cla"] = stat_cla[n]
            if unit_of_meas[n] != None:
                msg ["unit_of_meas"] = unit_of_meas[n]
            if precision[n] != None:
                msg ["suggested_display_precision"] = precision[n]

            msg ["val_tpl"]      = "{{ value_json.value }}"
            msg ["dev"]          = {"identifiers": [dev_name],"manufacturer": manufacturer,"model": model,"name": dev_name,"sw_version": sw_ver}
            message              = json.dumps(msg)

            publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)

            b = "...mqtt auto discovery - system sensors:" + str(round(config/max_config *100)) +" %"
            print(b, end="\r")

            msg                  = {}
            config               = config +1

        print("...mqtt auto discovery")

        # define individual batteries sensors
        names        =["current",       "voltage" ,     "temperature",  "soc",          "status"]
        ids          =["current",       "voltage" ,     "temperature",  "soc",          "basic_st"]
        dev_cla      =["current",       "voltage",      "temperature",  "battery",      None]
        stat_cla     =["measurement",   "measurement",  "measurement",  "measurement",  None]
        unit_of_meas =["A",             "V",            "°C",           "%",            None]
        precision    =[2,               2,              1,              0,              None]

        max_config   = max_config + powers*len(ids)

        for power in range (1, powers+1):
            for n in range(len(ids)):
                msg ["uniq_id"]      = dev_name + "_" + ids[n] +"_" + str(power)
                state_topic          = "homeassistant/sensor/" + dev_name + "/" + msg["uniq_id"] + "/config"
                msg ["name"]         = names[n]+"_"+str(power)
                msg ["stat_t"]       = "pytes_serial/" + dev_name + "/" + str(power-1) + "/" + ids[n]
                if dev_cla[n] != None:
                    msg ["dev_cla"]  = dev_cla[n]
                if stat_cla[n] != None:
                    msg ["stat_cla"]  = stat_cla[n]
                if unit_of_meas[n] != None:
                    msg ["unit_of_meas"] = unit_of_meas[n]
                if precision[n] != None:
                    msg ["suggested_display_precision"] = precision[n]

                msg ["val_tpl"]      = "{{ value_json.value }}"
                msg ["dev"]          = {"identifiers": [dev_name],"manufacturer": manufacturer,"model": model,"name": dev_name,"sw_version": sw_ver}
                message              = json.dumps(msg)

                publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)

                b = "...mqtt auto discovery - battery sensors:" + str(round(config/max_config *100)) +" %"
                print(b, end="\r")

                msg                  ={}
                config               = config +1

        print("...mqtt auto discovery")

        # define individual cells sensors
        if cells_monitoring == 'true':
            # individual sensors based on monitoring level
            if cells_mon_level == 'high':
                names        =["voltage",       "temperature",  "soc",          "status",   "volt_st",  "curr_st",  "temp_st"]
                ids          =["voltage",       "temperature",  "soc",          "basic_st", "volt_st",  "curr_st",  "temp_st"]
                dev_cla      =["voltage",       "temperature",  "battery",      None,       None,       None,       None]
                stat_cla     =["measurement",   "measurement",  "measurement",  None,       None,       None,       None]
                unit_of_meas =["V",             "°C",           "%",            None,       None,       None,       None]
                precision    =[3,               1,              0,              None,       None,       None,       None]

            elif cells_mon_level == 'medium':
                names        =["voltage",       "temperature",  "volt_st"]
                ids          =["voltage",       "temperature",  "volt_st"]
                dev_cla      =["voltage",       "temperature",       None]
                stat_cla     =["measurement",   "measurement",       None]
                unit_of_meas =["V",             "°C",                None]
                precision    =[3,               1,                   None]

            else:
                names        =["voltage"]
                ids          =["voltage"]
                dev_cla      =["voltage"]
                stat_cla     =["measurement"]
                unit_of_meas =["V"]
                precision    =[3]

            max_config   = max_config + powers*len(ids)*cells

            for power in range (1, powers+1):
                for n in range(len(ids)):
                    for cell in range(1, cells+1):
                        if cell < 10:
                            cell_no ="0" + str(cell)
                        else:
                            cell_no ="" + str(cell)

                        msg ["uniq_id"]      = dev_name + "_" + ids[n] + "_" + str(power) + cell_no
                        state_topic          = "homeassistant/sensor/" + dev_name + "/" + msg["uniq_id"] + "/config"
                        msg ["name"]         = names[n]+"_"+str(power) + cell_no
                        msg ["stat_t"]       = "pytes_serial/" + dev_name + "/" + str(power-1) + "/cells/" + str(cell-1) + "/" + ids[n]
                        if dev_cla[n] != None:
                            msg ["dev_cla"]  = dev_cla[n]
                        if stat_cla[n] != None:
                            msg ["stat_cla"]  = stat_cla[n]
                        if unit_of_meas[n] != None:
                            msg ["unit_of_meas"] = unit_of_meas[n]
                        if precision[n] != None:
                            msg ["suggested_display_precision"] = precision[n]

                        msg ["val_tpl"]      = "{{ value_json.value }}"
                        msg ["dev"]          = {"identifiers": [dev_name+"_cells"],"manufacturer": manufacturer,"model": model,"name": dev_name+"_cells","sw_version": sw_ver}
                        message              = json.dumps(msg)

                        publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)

                        b = "...mqtt auto discovery - cell sensors:" + str(round(config/max_config *100)) +" %"
                        print(b, end="\r")

                        msg                  ={}
                        config               = config +1

            # only for medium and high monitoring level
            if cells_mon_level == 'medium' or cells_mon_level == 'high':

                print("...mqtt auto discovery")

                # define individual cells sensors -- statistics
                names        =["voltage_delta", "voltage_min",  "voltage_max",  "temperature_delta",    "temperature_min",  "temperature_max"]
                ids          =["voltage_delta", "voltage_min",  "voltage_max",  "temperature_delta",    "temperature_min",  "temperature_max"]
                dev_cla      =["voltage",       "voltage",      "voltage",      "temperature",          "temperature",      "temperature"]
                stat_cla     =["measurement",   "measurement",  "measurement",  "measurement",          "measurement",      "measurement"]
                unit_of_meas =["V",             "V",            "V",            "°C",                   "°C",               "°C"]
                precision    =[3,               3,              3,              1,                      1,                  1]

                max_config   = max_config + powers*len(ids)

                for power in range (1, powers+1):
                    for n in range(len(ids)):
                        msg ["uniq_id"]      = dev_name + "_" + ids[n] + "_" + str(power)
                        state_topic          = "homeassistant/sensor/" + dev_name + "/" + msg["uniq_id"] + "/config"
                        msg ["name"]         = names[n]+"_"+str(power)
                        msg ["stat_t"]       = "pytes_serial/" + dev_name + "/" + str(power-1) + "/cells/" + ids[n]
                        if dev_cla[n] != None:
                            msg ["dev_cla"]  = dev_cla[n]
                        if stat_cla[n] != None:
                            msg ["stat_cla"]  = stat_cla[n]
                        if unit_of_meas[n] != None:
                            msg ["unit_of_meas"] = unit_of_meas[n]
                        if precision[n] != None:
                            msg ["suggested_display_precision"] = precision[n]

                        msg ["val_tpl"]      = "{{ value_json.value }}"
                        msg ["dev"]          = {"identifiers": [dev_name+"_cells"],"manufacturer": manufacturer,"model": model,"name": dev_name+"_cells","sw_version": sw_ver}
                        message              = json.dumps(msg)

                        publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)

                        b = "...mqtt auto discovery - statistics sensors:" + str(round(config/max_config *100)) +" %"
                        print(b, end="\r")

                        msg                  ={}
                        config               = config +1

        print("...mqtt auto discovery")

    except Exception as e:
        print('...mqtt_discovery error: ' + str(e))
        pytes_serial_log.warning('MQTT DISCOVERY - error handling message: '  + str(e))

def mqtt_publish():
    try:
        MQTT_auth = None   # type: publish.AuthParameter | None
        if len(MQTT_username) >0:
            MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }

        # Publish system topics
        for key, value in json_data.items():
            # We will publish these later
            if key in ["devices", "cells_data"]:
                continue

            # If the value was published before, skip it
            if json_data_old and value == json_data_old[key]:
                continue

            state_topic = "pytes_serial/" + dev_name + "/" + key
            if isinstance(value, dict) or isinstance(value, list):
                message = json.dumps(value)
            else:
                message = json.dumps({'value': value})

            publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)

        # Publish device topics
        for device in json_data["devices"]:
            device_idx = str(device["power"] - 1)

            for key, value in device.items():
                # Do not publish these
                if key in ["power"]:
                    continue

                # If the value was published before, skip it
                if (
                    json_data_old and
                    len(json_data["devices"]) == powers and
                    len(json_data_old["devices"]) == powers and
                    value == json_data_old["devices"][device["power"] - 1][key]
                ):
                    continue

                state_topic = "pytes_serial/" + dev_name + "/" + device_idx + "/" + key
                if isinstance(value, dict) or isinstance(value, list):
                    message = json.dumps(value)
                else:
                    message = json.dumps({'value': value})

                publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)

        if cells_monitoring == 'true':
            for device in json_data["cells_data"]:
                device_idx = str(device["power"] - 1)

                # Publish cell statistics
                # low
                for key, value in device.items():
                    # Do not publish these
                    if key in ["power", "cells"]:
                        continue

                    # If the value was published before, skip it
                    if (
                        json_data_old and
                        len(json_data["cells_data"]) == powers and
                        len(json_data_old["cells_data"]) == powers and
                        value == json_data_old["cells_data"][device["power"] - 1][key]
                    ):
                        continue

                    state_topic = "pytes_serial/" + dev_name + "/" + device_idx + "/cells/" + key
                    if isinstance(value, dict) or isinstance(value, list):
                        message = json.dumps(value)
                    else:
                        message = json.dumps({'value': value})

                    publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0)

                # Publish cell topics
                for cell in device["cells"]:
                    cell_idx = str(cell["cell"] - 1)

                    for key, value in cell.items():
                        # Do not publish these
                        if key in ["power", "cell"]:
                            continue

                        # If the value was published before, skip it
                        if(
                            json_data_old and
                            len(json_data["cells_data"]) == powers and
                            len(json_data_old["cells_data"]) == powers and
                            len(json_data["cells_data"][device["power"] - 1]["cells"]) == cells and
                            len(json_data_old["cells_data"][device["power"] - 1]["cells"]) == cells and
                            value == json_data_old["cells_data"][device["power"] - 1]["cells"][cell["cell"] - 1].get(key)
                        ):
                            continue

                        state_topic = "pytes_serial/" + dev_name + "/" + device_idx + "/cells/" + cell_idx + "/" + key
                        if isinstance(value, dict) or isinstance(value, list):
                            message = json.dumps(value)
                        else:
                            message = json.dumps({'value': value})

                        publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0)

        print('...mqtt publish  : ok')

    except Exception as e:
        print('...mqtt publish error: ' + str(e))
        pytes_serial_log.warning('MQTT PUBLISH - error handling message: ' + str(e))

def parse_bat(power, retry=0):
    try:
        global line_str_array
        global bat
        bat = []

        req  = ('bat '+ str(power))
        size = 1000
        write_return = write_serial(req,size)

        if write_return != 'true':
            return "false"

        read_return = read_serial('Battery', END_MARKERS)

        if read_return != 'true' or not line_str_array:
            return "false"

        cell_idx        = -1
        volt_idx        = -1
        curr_idx        = -1
        temp_idx        = -1
        base_st_idx     = -1
        volt_st_idx     = -1
        curr_st_idx     = -1
        temp_st_idx     = -1
        soc_idx         = -1
        coulomb_idx     = -1
        is_pylontech    = False

        for i, line_str in enumerate(line_str_array):

            # Last line is command completed message
            if line_str.strip().startswith('Command completed'):
                break

            # First line is table header
            elif i == 0:
                line = re.split(r'\s{2,}', line_str.strip())   # type: list[str] # Each column is delimited by at least 2 spaces

                for j, l in enumerate(line):
                    if l == 'Battery':
                        cell_idx = j
                    elif l == 'Volt':
                        volt_idx = j
                    elif l == 'Curr':
                        curr_idx = j
                    elif l == 'Tempr':
                        temp_idx = j
                    elif l == 'Base State':
                        base_st_idx = j
                    elif l == 'Volt. State':
                        volt_st_idx = j
                    elif l == 'Curr. State':
                        curr_st_idx = j
                    elif l == 'Temp. State':
                        temp_st_idx = j
                    elif l == 'SOC':
                        soc_idx = j
                    elif l == 'Coulomb':
                        coulomb_idx = j

                # Workaround for Pytes firmware missing SOC column in the header
                if soc_idx == -1 and coulomb_idx != -1:
                    soc_idx = coulomb_idx
                    coulomb_idx = coulomb_idx + 1

            # All the other lines are cell data
            # Parameters are selected based on monitoring level
            else:
                line = re.split(r'\s{2,}', line_str.strip())   # Each column is delimited by at least 2 spaces
                cell_data = {}   # type: dict[str, int|float|str]

                cell_data['power']              = power

                if cell_idx != -1:
                    cell_data['cell']           = int(line[cell_idx]) + 1
                if volt_idx != -1:
                    cell_data['voltage']        = int(line[volt_idx]) / 1000              # V
                if cells_mon_level=='high' and curr_idx != -1:
                    cell_data['current']        = int(line[curr_idx]) / 1000              # A
                if (cells_mon_level=='medium' or cells_mon_level=='high') and temp_idx != -1:
                    cell_data['temperature']    = int(line[temp_idx]) / 1000              # deg C
                if cells_mon_level=='high' and base_st_idx != -1:
                    cell_data['basic_st']       = line[base_st_idx]
                if (cells_mon_level=='medium' or cells_mon_level=='high') and volt_st_idx != -1:
                    cell_data['volt_st']        = line[volt_st_idx]
                if cells_mon_level=='high' and curr_st_idx != -1:
                    cell_data['curr_st']        = line[curr_st_idx]
                if cells_mon_level=='high' and temp_st_idx != -1:
                    cell_data['temp_st']        = line[temp_st_idx]
                if cells_mon_level=='high' and soc_idx != -1:
                    cell_data['soc']            = int(line[soc_idx][:-1])                 # %
                if cells_mon_level=='high' and coulomb_idx != -1:
                    cell_data['coulomb']        = int(line[coulomb_idx][:-4]) / 1000      # Ah

                bat.append(cell_data)

        return "true"

    except (ValueError, IndexError) as e:
        if retry < 3:
            pytes_serial_log.debug(
                'PARSING BAT - power:' + str(power)
                + ' retry:' + str(retry + 1)
                + ' invalid data: ' + str(e)
            )
            return parse_bat(power, retry + 1)

        pytes_serial_log.warning(
            'PARSING BAT - power:' + str(power)
            + ' invalid data after retries: ' + str(e)
        )
        return "false"

    except Exception as e:
        pytes_serial_log.warning('PARSING BAT - error handling message: ' + str(e))
        return "false"

def check_cells():
    try:
        global bats

        for power in range (1, powers+1):
            if parse_bat(power)=="true":

                # statistics available only for medium and high monitoring level
                if cells_mon_level=='medium' or cells_mon_level=='high':
                   # statistics -- calculate min,mix of cells data of each power
                    output = {
                        "voltage" : [float('inf'),float('-inf')],
                        "temperature" : [float('inf'),float('-inf')]
                    }

                    for item in bat:
                        for each in output.keys():
                            if item[each]<output[each][0]:
                                output[each][0] = item[each]

                            if item[each]>output[each][1]:
                                output[each][1] = item[each]

                    stat = {
                        'power':power,
                        'voltage_delta':round(output['voltage'][1] - output['voltage'][0],3),
                        'voltage_min':output['voltage'][0],
                        'voltage_max':output['voltage'][1],
                        'temperature_delta': round(output['temperature'][1] - output['temperature'][0],3),
                        'temperature_min':output['temperature'][0],
                        'temperature_max':output['temperature'][1],
                        'cells':bat
                    }

                else:
                    # statistics not available for 'low' level monitoring
                    stat = {
                        'power':power,
                        'cells':bat
                    }

                bats.append(stat)

            else:
                pass

    except Exception as e:
        pytes_serial_log.warning('CHECK CELLS - error handling message: ' + str(e))

# -------------------- SERIAL INITIALIZATION ------------------------
try:
    ser = serial.Serial(port=serial_port,\
          baudrate=serial_baudrate,\
          parity=serial.PARITY_NONE,\
          stopbits=serial.STOPBITS_ONE,\
          bytesize=serial.EIGHTBITS,\
          timeout=10)

    if ser.portstr: print('...connected to: ' + ser.portstr)

except Exception as e:
    print('...serial connection error: ' + str(e))
    pytes_serial_log.error('OPEN SERIAL - error handling message: ' + str(e))
    print('...program initialisation failed -- exit')

    exit()

# -------------------- MQTT AUTO DISCOVERY (HA) ---------------------
if MQTT_active =='true':  mqtt_discovery()

# -------------------- MAIN LOOP ------------------------------------
print('...program initialisation completed starting main loop')

pytes_serial_log.info('START - ' + version)

json_data = {}

# define time interval when full set of data will be send
FULL_UPDATE_EVERY_MIN = 5
last_full_update = 0.0

while True:
    time.sleep(0.2)
    if (time.time() - start_time) > reading_freq:

        loops_no       = loops_no +1

        now            = datetime.datetime.now()
        TimeStamp      = now.strftime("%Y-%m-%d %H:%M:%S")
        print('relay local time:', TimeStamp)

        uptime = round((time.time()- up_time)/86400, 3)
        print('serial uptime   :', uptime)
        start_time = time.time()

        if errors == 'false':
            parsing_time = time.time()
            parse_pwr()
            parsing_time = time.time() - parsing_time

        if cells_monitoring == 'true' and errors == 'false':
            check_cells_time = time.time()
            check_cells()
            check_cells_time = (time.time() - check_cells_time)
            parsing_time     = parsing_time + check_cells_time



        if errors == 'false':
            serialize_json()

        if errors == 'false' and SQL_active == 'true':
            write_mariadb()

        if errors == 'false' and MQTT_active == 'true':
            now_ts = time.time()

            # force full publish every X minutes
            if (now_ts - last_full_update) >= FULL_UPDATE_EVERY_MIN * 60:
                json_data_old = None            # disable deduplication once
                last_full_update = now_ts
                pytes_serial_log.debug('MAIN LOOP - MQTT full update triggered')

            mqtt_publish()

        if errors != 'false' :
            errors_no = errors_no + 1

        print('...serial stat   :', 'loops:' , loops_no, 'errors:', errors_no, 'efficiency:', round((1-(errors_no/loops_no))*100, 2))
        print('...serial stat   :', 'parsing round-trip:' , round(parsing_time, 2))
        print('------------------------------------------------------')

        # clear variables
        pwr        = []
        bats       = []
        errors     = 'false'
        trials     = 0

