#!/usr/bin/python
import logging
from logging.handlers import RotatingFileHandler
import serial
import time, datetime
import json
import mysql.connector as mariadb
from configparser import ConfigParser
import paho.mqtt.publish as publish

# ---------------------------variables initialization---------- 
config                = ConfigParser()
config.read('pytes_serial.cfg')

serial_port           = config.get('serial', 'serial_port') 
serial_baudrate       = int(config.get('serial', 'serial_baudrate'))
reading_freq          = int(config.get('serial', 'reading_freq'))
output_path           = config.get('general', 'output_path')
powers                = int(config.get('battery_info', 'powers'))        
dev_name              = config.get('battery_info', 'dev_name')
manufacturer          = config.get('battery_info', 'manufacturer')
model                 = config.get('battery_info', 'model')
sw_ver                = "PytesSerial v0.6.0_20231007"
version               = sw_ver 

if reading_freq < 10  : reading_freq = 10

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

events_monitoring      = config.get('events', 'events_monitoring')
cells                  = int(config.get('events', 'cells'))
cells_details          = config.get('events', 'cells_details')
cells_details_level    = config.get('events', 'cells_details_level')

start_time            = time.time()                         # init time
up_time               = time.time()                         # used to calculate uptime
pwr                   = []                                  # used to serialise JSON data
loops_no              = 0                                   # used to count no of loops and to calculate % of errors
errors_no             = 0                                   # used to count no of errors and to calculate %
trials                = 0                                   # used to improve data reading accuracy -- def parsing_serial
errors                = 'false'
line_str_array        = []                                  # used to get line strings from serial
bat_events_no         = 0                                   # used to count numbers of battery events
pwr_events_no         = 0                                   # used to count numbers of power events
sys_events_no         = 0                                   # used to count numbers of system events

power_events_list = {
0:["info","0x0","No events"],    
1:["warning","0x1","Overvoltage alarm"],
2:["warning","0x2","High voltage alarm"],
4:["info","0x4","*tbc*The voltage is normal"],
8:["warning","0x8","*tbc*Low voltage alarm"],
16:["warning","0X10","*tbc*Under voltage alarm"],
32:["warning","0x20","*tbc*Cell sleep"],
64:["warning","0X40","*tbc*Battery life alarm 1"],
128:["warning","0x80","*tbc*System startup"],
256:["warning","0x100","*tbc*Over temperature alarm"],
512:["warning","0x200","*tbc*High temperature alarm"],
1024:["warning","0x400","*tbc*Temperature is normal"],
2048:["warning","0x800","*tbc*Low temperature alarm"],
4096:["warning","0x1000","*tbc*Under temperature alarm"],
8192:["warning","0x2000","*tbc*Full charge"],
16384:["warning","0x4000","*tbc*Normal power"],
32768:["warning","0x8000","*tbc*Low power"],
65536:["warning","0x10000","*tbc*Short circuit protection"],
131072:["warning","0x20000","*tbc*Discharge overcurrent protection 2"],
262144:["warning","0x40000","*tbc*Charging overcurrent protection 2"],
524288:["warning","0x80000","*tbc*Discharge overcurrent protection"],
1048576:["warning","0x100000","*tbc*Charging overcurrent protection"],
2097152:["info","0x200000","System idle"],
4194304:["info","0x400000","Charging"],
8388608:["info","0x800000","Discharging"],
16777216:["warning","0x1000000","*tbc*System power failure"],
33554432:["warning","0x2000000","*tbc*System idle"],
67108864:["warning","0x4000000","*tbc*Charging"],
134217728:["warning","0x8000000","*tbc*Discharging"],
268435456:["warning","0x10000000","*tbc*System error"],
536870912:["warning","0x20000000","*tbc*System hibernation"],
1073741824:["warning","0x40000000","*tbc*System shutdown"],
2147483648:["warning","0x80000000","*tbc*Battery life alarm 2"]
}

sys_events_list = {
0:["info","0x0","No events"],    
1:["warning","0x1","Reverse connection of external power input"],
2:["warning","0x2","External power input overvoltage"],
4:["warning","0x4","Current detection error"],
8:["warning","0x8","OZ abnormal"],
16:["warning","0x10","Sleep module abnormal"],
32:["warning","0x20","temperature sensor error"],
64:["warning","0x40","Voltage detection error"],
128:["warning","0x80","I2C bus error"],
256:["warning","0x100","CAN bus address assignment error"],
512:["warning","0x200","Internal CAN bus communication error"],
1024:["warning","0x400","Charge MOS FAIL"],
2048:["warning","0x800","Discharge MOS FAIL"]
}

print("software version:",version)

# ------------------------logging definiton ----------------------------
formatter = logging.Formatter('%(asctime)s| %(levelname)7s| %(message)s ',datefmt='%Y%m%d %H:%M:%S') # logging formating
def setup_logger(name, log_file, level=LOGGING_LEVEL_FILE):
    
    """To setup as many loggers as you want"""
    handler = RotatingFileHandler(log_file, mode='a', maxBytes=LOGGING_FILE_MAX_SIZE*1000, backupCount=LOGGING_FILE_MAX_FILES, encoding=None, delay=0)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)  
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

pytes_serial_log    = setup_logger('pytes_serial', 'pytes_serial.log')
battery_events_log  = setup_logger('battery_events', 'battery_events.log')

# ------------------------functions area----------------------------
def serial_write(req, size):
    try:
        loop_time = time.time()
        
        if ser.is_open != True:
            ser.open()
            time.sleep(0.5)
            print ('...open serial')
            
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        bytes_req = bytes(str(req), 'latin-1')
        ser.write(bytes_req + b'\n')
        ser.flush()
        time.sleep(0.1)

        while True:
            if ser.in_waiting > size:
                print ('...writing complete, in buffer: ', ser.in_waiting , round((time.time() - loop_time),2))                
                return "true"            

            elif (time.time() - loop_time) > 1:
                return "false"

            elif ser.in_waiting < 100 and (time.time() - loop_time) > 0.4:
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.write(bytes_req + b'\n')
                ser.flush()
                time.sleep(0.25)
                
            else:
                ser.write(b'\n')
                time.sleep(0.1)            
 
    except Exception as e:
        print('...serial write error: '+ str(e))
        pytes_serial_log.warning ('SERIAL WRITE - error handling message: '+ str(e))
        
def serial_read(start,stop):
    try:
        global line_str_array
        line_str        = ""
        line_str_array  = []
        
        if ser.is_open != True:
            ser.open()
            time.sleep(0.5)
            print ('...open serial')
            
        while True:
            if ser.in_waiting > 0:
                line          = ser.read()
                line_str      = line_str + line.decode('latin-1')
                
                if line == b'\n':
                    if start == 'none' or start in line_str:
                        start = 'true'
               
                    if start == 'true' and stop != 'true':
                        line_str_array.append(line_str)
                        
                    if start == 'true' and stop in line_str:
                        stop = 'true'
                    
                    line_str = ""
                    
            else:
                 break
                
        return stop
    
    except Exception as e:
        print('...serial read error: ' + str(e))
        pytes_serial_log.warning ('SERIAL READ - error handling message: ' + str(e))
        pytes_serial_log.debug ('SERIAL READ - line:' + str(line)  + ' line_str_array: ' + str(line_str_array))
            
        line_str_array = []
        
def parsing_serial():
    try:
        global line_str_array
        global errors
        global trials
        global pwr                                                                                 
        volt_st      = None                                                                        
        current_st   = None   
        temp_st      = None     
        coul_st      = None
        soh_st       = None
        heater_st    = None
        bat_events   = None
        power_events = None
        sys_events   = None

        data_set           = 0
        pwr                = []
        line_str_array_bak = []
        
        for power in range (1, powers + 1):
            req  = ('pwr '+ str(power))
            size = 800                                     
            rw_trials = 0
            
            while True:
                write_return = serial_write(req,size)
                
                if write_return == 'true':
                    read_return = serial_read(req,'Command completed')
                    
                    if line_str_array and read_return == 'true':
                        rw_trials = 0
                        break
                    
                    else:
                        pass
                
                elif rw_trials <= 5:
                    rw_trials  = rw_trials +1
                    buffer     = ser.in_waiting
                    
                    serial_read('none','none')
                    pytes_serial_log.debug ('PARSING SERIAL - power:' + str(power)  + ' rw_trial:' + str(rw_trials) + ' err_no:' + str(errors_no) + \
                         ' timeout in_buffer:' + str(buffer) + ' < ' + str(size) + ' line_str_array: ' + str(line_str_array))
                        
                    line_str_array  = []

                else:
                    errors = 'true'
                    buffer     = ser.in_waiting
                    
                    print ('...timeouts -> close serial, skip set')
                    pytes_serial_log.error ('PARSING SERIAL - power:' + str(power)  + ' rw_trial:' + str(rw_trials) + ' err_no:' + str(errors_no) + \
                    ' timeouts -> close serial in_buffer:' + str(buffer) + ' < ' + str(size) + ' line_str_array: ' + str(line_str_array))
                    
                    if ser.is_open == True:
                        ser.close()
                        
                    return

            decode             = 'false'
            line_str_array_bak = line_str_array             # for debug purpose only
            
            for line_str in line_str_array:              
                if req in line_str:                         # search for pwr X in line and mark begining of the block                        
                    decode ='true'
                    
                #parsing data   
                if decode =='true':
                    if line_str[1:18] == 'Voltage         :': voltage      = round(int(line_str[19:27])/1000, 2)
                    if line_str[1:18] == 'Current         :': current      = round(int(line_str[19:27])/1000, 2)
                    if line_str[1:18] == 'Temperature     :': temp         = round(int(line_str[19:27])/1000, 1)
                    if line_str[1:18] == 'Coulomb         :': soc          = int(line_str[19:27])
                    if line_str[1:18] == 'Basic Status    :': basic_st     = line_str[19:27]        
                    if line_str[1:18] == 'Volt Status     :': volt_st      = line_str[19:27]      
                    if line_str[1:18] == 'Current Status  :': current_st   = line_str[19:27]    
                    if line_str[1:18] == 'Tmpr. Status    :': temp_st      = line_str[19:27]     
                    if line_str[1:18] == 'Coul. Status    :': coul_st      = line_str[19:27]
                    if line_str[1:18] == 'Soh. Status     :': soh_st       = line_str[19:27]
                    if line_str[1:18] == 'Heater Status   :': heater_st    = line_str[19:27]
                    if line_str[1:18] == 'Bat Events      :': bat_events   = int(line_str[19:27],16)
                    if line_str[1:18] == 'Power Events    :': power_events = int(line_str[19:27],16)
                    if line_str[1:18] == 'System Fault    :': sys_events   = int(line_str[19:27],16)
                    
                    if line_str[1:18] == 'Command completed':   # mark end of the block
                        try:
                            decode ='false' 
                            print ('power           :', power)
                            print ('voltage         :', voltage)    
                            print ('current         :', current)
                            print ('temperature     :', temp)
                            print ('soc [%]         :', soc)
                            print ('basic_st        :', basic_st)         
                            print ('volt_st         :', volt_st)      
                            print ('current_st      :', current_st)     
                            print ('temp_st         :', temp_st)     
                            print ('coul_st         :', coul_st)
                            print ('soh_st          :', soh_st)
                            print ('heater_st       :', heater_st)
                            print ('bat_events      :', bat_events)
                            print ('power_events    :', power_events)
                            print ('sys_fault       :', sys_events)              
                            print ('---------------------------')
                            
                            pwr_array = {
                                        'power': power,
                                        'voltage': voltage,
                                        'current': current,
                                        'temperature': temp,
                                        'soc': soc,
                                        'basic_st': basic_st,
                                        'volt_st': volt_st,
                                        'current_st': current_st,
                                        'temp_st':temp_st,
                                        'soh_st':soh_st,
                                        'coul_st': coul_st,
                                        'heater_st': heater_st,
                                        'bat_events': bat_events,
                                        'power_events': power_events,
                                        'sys_events': sys_events}
                                    
                            data_set       = data_set +1
                            pwr.append(pwr_array)
                            line_str_array = []
                            line_str       = ""
                            
                            break
                        
                        except Exception as e:
                            pytes_serial_log.warning ('PARSING SERIAL - error handling message: '+str(e))
                                
            if data_set != power:
                break
                     
        if data_set == powers:
            statistics()
            errors='false'
            trials=0
            
            print ('...serial parsing: ok')

        else:
            errors = 'true'
            trials = trials+1
                
            if trials <= 3:                                                                                       
                print ('...incomplete data sets -> try again')
                pytes_serial_log.debug ('PARSING SERIAL - power:' + str(power) + ' trial:' + str(trials) + ' err_no:' + str(errors_no) + ' incomplete data sets data set:' + str(data_set)  + ' line_str_array:' + str(line_str_array_bak))
                
                parsing_serial()

            else:
                print ('...incomplete data set -> not solved, close serial, skip set')
                pytes_serial_log.error ('PARSING SERIAL - power:' + str(power) + ' trial:' + str(trials) + ' err_no:'+str(errors_no) + ' incomplete data sets: ' + str(data_set)  + ' line_str_array:' + str(line_str_array_bak))
                
                if ser.is_open == True:
                    ser.close()
                    
                return
                    
    except Exception as e:
        errors = 'true'
           
        print('...parsing serial error: ' + str(e))
        pytes_serial_log.error ('PARSING SERIAL - error handling message: '+str(e))
        
        if ser.is_open == True:
            ser.close()
            print ('...close serial')
            
        return
    
def statistics():
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
        sys_voltage       = sys_voltage + pwr[power-1]['voltage']             # voltage will be the average of all batteries
        sys_current       = round((sys_current + pwr[power-1]['current']),1)  # current will be sum of all banks          
        sys_soc           = sys_soc + pwr[power-1]['soc']                     # soc will be the average of all batteries
        sys_temp          = sys_temp + pwr[power-1]['temperature']            # temperature will be the average of all batteries
   
    sys_voltage  = round((sys_voltage / powers), 1)    
    sys_soc      = int(sys_soc / powers)   
    sys_basic_st = pwr[0]['basic_st']                                         # status will be the master status
    sys_temp     = round((sys_temp / powers), 1)
    
def json_serialize():
    global parsing_time
    global loops_no
    global errors_no
    global errors
    global json_data
    global bat_events_no
    global pwr_events_no
    global sys_events_no
    try:
        json_data={'relay_local_time':TimeStamp,                   
                   'powers' : powers,
                   'voltage': sys_voltage,
                   'current': sys_current,
                   'temperature': sys_temp,
                   'soc': sys_soc,
                   'basic_st': sys_basic_st,
                   'devices':pwr,
                   'serial_stat': {'uptime':uptime,
                                   'loops':loops_no,
                                   'errors': errors_no,
                                   'bat_events_no': bat_events_no,
                                   'pwr_events_no': pwr_events_no,
                                   'sys_events_no': sys_events_no,
                                   'efficiency' :round((1-(errors_no/loops_no))*100,2),
                                   'ser_round_trip':round(parsing_time,2)}
                   }
        
        with open(output_path + dev_name + '_status.json', 'w') as outfile:
            json.dump(json_data, outfile)
        print('...json creation:  ok')
        
    except Exception as e:
        print('...json serialization error: ' + str(e))
        pytes_serial_log.error ('JSON SERIALIZATION - error handling message: ' + str(e))
        
        errors = 'true'
        
def maria_db():
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
                     pwr[power-1]['temp_st'],
                     pwr[power-1]['coul_st'],
                     pwr[power-1]['soh_st'],
                     pwr[power-1]['heater_st'],
                     pwr[power-1]['bat_events'],
                     pwr[power-1]['power_events'],
                     pwr[power-1]['sys_events'])

            sql="INSERT INTO pwr_data\
            (power,\
            voltage,current,\
            temperature,\
            soc,\
            basic_st,\
            volt_st,\
            current_st,\
            temp_st,\
            coul_st,\
            soh_st,\
            heater_st,\
            bat_events,\
            power_events,\
            sys_events) \
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            mycursor = mydb.cursor()
            mycursor.execute(sql, values)
            mydb.commit()

        mycursor.close()
        mydb.close()
        print ('...mariadb upload: ok')
        
    except Exception as e:
        print('...mariadb writing error: '+ str(e))
        pytes_serial_log.warning ('MARIADB WRITING - error handling message: '+ str(e))
        
def mqtt_discovery():
    try:
        MQTT_auth = None
        if len(MQTT_username) > 0:
            MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }

        msg          ={} 
        config       = 1
        names        =["current", "voltage" , "temperature", "soc", "status"]
        ids          =["current", "voltage" , "temperature", "soc", "basic_st"] 
        dev_cla      =["current", "voltage", "temperature", "battery","None"]
        stat_cla     =["measurement","measurement","measurement","measurement","None"]
        unit_of_meas =["A","V","°C", "%","None"]

        # define system sensors 
        for n in range(5):
            state_topic          = "homeassistant/sensor/" + dev_name + "/" + str(config) + "/config"
            msg ["name"]         = names[n]      
            msg ["stat_t"]       = "homeassistant/sensor/" + dev_name + "/state"
            msg ["uniq_id"]      = dev_name + "_" + ids[n]
            if dev_cla[n]  != "None":
                msg ["dev_cla"]  = dev_cla[n]
            if stat_cla[n] != "None":
                msg ["stat_cla"] = stat_cla[n]
            if unit_of_meas[n] != "None":
                msg ["unit_of_meas"] = unit_of_meas[n]
                
            msg ["val_tpl"]      = "{{ value_json." + ids[n]+ "}}"
            msg ["dev"]          = {"identifiers": [dev_name],"manufacturer": manufacturer,"model": model,"name": dev_name,"sw_version": sw_ver}            
            message              = json.dumps(msg)
            
            publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)

            b = "...mqtt auto discovery initialization :" + str(round(config/(5*powers+5)*100)) +" %"
            print (b, end="\r")
            
            msg                  ={}
            config               = config +1
            time.sleep(2)
        
        # define individual batteries sensors
        for power in range (1, powers+1):
            for n in range(5):
                state_topic          ="homeassistant/sensor/" + dev_name + "/" + str(config) + "/config"
                msg ["name"]         = names[n]+"_"+str(power)         
                msg ["stat_t"]       = "homeassistant/sensor/" + dev_name + "/state"
                msg ["uniq_id"]      = dev_name + "_" +ids[n]+"_"+str(power)
                if dev_cla[n] != "None":
                    msg ["dev_cla"]  = dev_cla[n]
                if stat_cla[n] != "None":
                    msg ["stat_cla"]  = stat_cla[n]                    
                if unit_of_meas[n] != "None":
                    msg ["unit_of_meas"] = unit_of_meas[n]
                    
                msg ["val_tpl"]      = "{{ value_json.devices[" + str(power-1) + "]." + ids[n]+ "}}"
                msg ["dev"]          = {"identifiers": [dev_name],"manufacturer": manufacturer,"model": model,"name": dev_name,"sw_version": sw_ver}  
                message              = json.dumps(msg)
                
                publish.single(state_topic, message, hostname=MQTT_broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)

                b = "...mqtt auto discovery initialization :" + str(round(config/(5*powers+5)*100)) +" %"
                print (b, end="\r")
                
                msg                  ={}
                config               = config +1
                time.sleep(2)
                
        print("...mqtt auto discovery initialization completed")
        
    except Exception as e:
        print('...mqtt_discovery error: ' + str(e))    
        pytes_serial_log.warning ('MQTT DISCOVERY - error handling message: '  + str(e))
        
def mqtt_publish():
    try:
        MQTT_auth = None
        if len(MQTT_username) >0:
            MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
        state_topic = "homeassistant/sensor/" + dev_name + "/state"
        message     = json.dumps(json_data)
        publish.single(state_topic, message, hostname=MQTT_broker, port=MQTT_port, auth=MQTT_auth)
        print ('...mqtt publish  : ok')
        
    except Exception as e:
        print ('...mqtt publish error: ' + str(e))
        pytes_serial_log.warning ('MQTT PUBLISH - error handling message: ' + str(e))
        
def check_events ():
    global pwr
    global bat_events_no
    global pwr_events_no
    global sys_events_no
    
    try:
        for power in range (1, powers+1):
            cell_data_req = "false"
            
            if pwr[power-1]['bat_events'] != 0 and (power_events_list[pwr[power-1]['bat_events']][0] == cells_details_level or cells_details_level =="info"):
                print('...bat_event logged  :', str(power_events_list[pwr[power-1]['bat_events']][1]))
                battery_events_log.info ('CHECK EVENTS - bat_events:' +  str(power_events_list[pwr[power-1]['bat_events']][1]) + \
                    ' details:' + str(pwr[power-1]))
                
                cell_data_req = "true"
                bat_events_no = bat_events_no + 1
                
            if pwr[power-1]['power_events'] != 0 and (power_events_list[pwr[power-1]['power_events']][0] == cells_details_level or cells_details_level =="info"):
                print('...power_event logged:', str(power_events_list[pwr[power-1]['power_events']][1]))
                battery_events_log.info ('CHECK EVENTS - power_events:' + str(power_events_list[pwr[power-1]['power_events']][1]) + \
                    ' details:' + str(pwr[power-1]))
                
                cell_data_req = "true"
                pwr_events_no = pwr_events_no + 1
                
            if pwr[power-1]['sys_events'] != 0 and (sys_events_list[pwr[power-1]['sys_events']][0] == cells_details_level or cells_details_level =="info"):
                print('...sys_event logged  :', str(sys_events_list[pwr[power-1]['sys_events']][2]))
                battery_events_log.info ('CHECK EVENTS - sys_events:' + str(sys_events_list[pwr[power-1]['sys_events']][2]) + \
                    ' details:' + str(pwr[power-1]))
                
                cell_data_req = "true"
                sys_events_no = sys_events_no + 1
                
            if cell_data_req == "true":
                if cells_details =='true' and parsing_bat(power)=="true":
                    pass
                else:
                    battery_events_log.info ('CHECK EVENTS - power_'+ str(power)+' cells details:cells data could not be read')
                
    except Exception as e:
        pytes_serial_log.warning ('CHECK EVENTS - error handling message: ' + str(e))
        
def parsing_bat(power):
    global line_str_array
    bat = []
    cells_data =[]
        
    try:
        req  = ('bat '+ str(power))
        size = 1000
        write_return = serial_write(req,size)
        
        if write_return == 'true':
            read_return = serial_read('Battery','Command completed')
            
        if line_str_array and read_return == 'true':
            for line_str in line_str_array:
                if line_str[1:18] == 'Command completed':
                    decode ='false'
                    
                if line_str[0:6].startswith('Batt'):
                    power_idx   = line_str.find('Batt')
                    volt_idx    = line_str.find('Volt ')
                    curr_idx    = line_str.find('Curr ')
                    temp_idx    = line_str.find('Tempr ')
                    base_st_idx = line_str.find('Base State')
                    volt_st_idx = line_str.find('Volt.')
                    curr_st_idx = line_str.find('Curr.')
                    temp_st_idx = line_str.find('Temp.')
                    if cells == 15:
                        coulomb_idx = line_str.find('SOC')         # pylon
                    else:                        
                        coulomb_idx = line_str.find('Coulomb')     # pytes
                        
                    decode      = 'true'

                if decode =='true' and not line_str[base_st_idx:base_st_idx+7].startswith('Absent') and not line_str[0:6].startswith('Batt'):
                    cell         = int(line_str[0:2])
                    voltage      = int(line_str[volt_idx:volt_idx+7])/1000
                    current      = int(line_str[curr_idx:curr_idx+7])/1000
                    temp         = int(line_str[temp_idx:temp_idx+7])/1000
                    basic_st     = line_str[base_st_idx:base_st_idx+8]                    
                    volt_st      = line_str[volt_st_idx:volt_st_idx+8]
                    current_st   = line_str[curr_st_idx:curr_st_idx+8]
                    temp_st      = line_str[temp_st_idx:temp_st_idx+8]
                    coulomb      = line_str[coulomb_idx:coulomb_idx+4]
                    
                    cells_data = {
                                'cell':cell,
                                'voltage': voltage,
                                'current': current,
                                'temp   ': temp,
                                'basic_st': basic_st,
                                'volt_st': volt_st,
                                'curr_st': current_st,
                                'temp_st':temp_st,
                                'SOC':coulomb}

                    bat.append(cells_data)
                    
            print("------------------------------------------------------")
            
            headers     = list(bat[0].keys())
            headers_str = (f'{headers[0].capitalize(): <5}|\
    {headers[1].capitalize(): <8}|\
    {headers[2].capitalize(): <8}|\
    {headers[3].capitalize(): <8}|\
    {headers[4].capitalize(): <9}|\
    {headers[5].capitalize(): <8}|\
    {headers[6].capitalize(): <8}|\
    {headers[7].capitalize(): <8}|\
    {headers[8].capitalize(): <8}')
            
            print(headers_str)
            battery_events_log.info (headers_str)
            
            for n in range(cells):
                cell_data = list (bat[n].values())
                cell_data_str = (f'{cell_data[0]: <5}|\
    {cell_data[1]: <8}|\
    {cell_data[2]: <8}|\
    {cell_data[3]: <8}|\
    {cell_data[4]: <9}|\
    {cell_data[5]: <8}|\
    {cell_data[6]: <8}|\
    {cell_data[7]: <8}|\
    {cell_data[8]: <8}\
    ')                
                print(cell_data_str)
                battery_events_log.info (cell_data_str)
                
            print("------------------------------------------------------")
            return "true"
        
        else:
            return "false"
            
    except Exception as e:
        pytes_serial_log.info ('PARSING BAT - error handling message: ' + str(e))
        
# --------------------------serial initialization------------------- 
try:
    ser = serial.Serial (port=serial_port,\
          baudrate=serial_baudrate,\
          parity=serial.PARITY_NONE,\
          stopbits=serial.STOPBITS_ONE,\
          bytesize=serial.EIGHTBITS,\
          timeout=10)
    
    print('...connected to: ' + ser.portstr)
    
except Exception as e:
    print('...serial connection error: ' + str(e))
    pytes_serial_log.error ('OPEN SERIAL - error handling message: ' + str(e))
    print('...program initialisation failed -- exit')
    
    exit()
    
# --------------------------mqtt auto discovery (HA)----------------
if MQTT_active =='true':  mqtt_discovery()

#-----------------------------main loop-----------------------------
print('...program initialisation completed starting main loop')

pytes_serial_log.info ('START - ' + version)
battery_events_log.info ('START - ' + version)

while True:
    if (time.time() - start_time) > reading_freq:                       
        
        loops_no       = loops_no +1                                    
        
        now            = datetime.datetime.now()
        TimeStamp      = now.strftime("%Y-%m-%d %H:%M:%S")       
        print ('relay local time:', TimeStamp)
        
        uptime = round((time.time()- up_time)/86400, 3)
        print ('serial uptime   :', uptime)
        start_time = time.time()
        
        if errors == 'false':
            parsing_time = time.time()
            parsing_serial()
            parsing_time = time.time() - parsing_time
            
        if events_monitoring=='true' and errors == 'false':
            check_events()
            
        if errors == 'false':
            json_serialize()
            
        if errors == 'false' and SQL_active == 'true':
            maria_db()
            
        if errors == 'false' and MQTT_active == 'true':
            mqtt_publish()
            
        if errors != 'false' :
            errors_no = errors_no + 1
            
        print ('...serial stat   :', 'loops:' , loops_no, 'errors:', errors_no, 'efficiency:', round((1-(errors_no/loops_no))*100, 2))
        print ('...serial stat   :', 'bat events_no:' , bat_events_no, 'pwr events_no:', pwr_events_no, 'sys events_no:', sys_events_no) 
        print ('...serial stat   :', 'parsing round-trip:' , round(parsing_time, 2)) 
        print ('------------------------------------------------------')
        
        #clear variables
        pwr        = []
        errors     = 'false'
        trials     = 0