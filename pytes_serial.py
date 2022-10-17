#!/usr/bin/python
import serial
import time, datetime
import json
import mysql.connector as mariadb
from configparser import ConfigParser

# ---------------------------variables initialization----------
config                = ConfigParser()
config.read('pytes_serial.cfg')

serial_port           = config.get('serial', 'serial_port') 
serial_baudrate       = int(config.get('serial', 'serial_baudrate'))
reading_freq          = int(config.get('serial', 'reading_freq'))
powers                = int(config.get('general', 'powers'))
output_path           = config.get('general', 'output_path') 

SQL_active            = config.get('Maria DB connection', 'SQL_active')  
host                  = config.get('Maria DB connection', 'host')  
db_port               = config.get('Maria DB connection', 'db_port')  
user                  = config.get('Maria DB connection', 'user')  
password              = config.get('Maria DB connection', 'password')  
database              = config.get('Maria DB connection', 'database')  

start_time      = time.time()
up_time         = time.time()
pwr             = []                                  # used to serialise JSON data

print('PytesSerial build: v0.1.4_20221016')
errors = 'false'

# ------------------------functions area------------------------
def parsing_serial():
    global errors
    for power in range (1, powers+1):                                 #do the loop for each battery
        try:
            # parsing pwr 1 commmand - reading power bank1   
            line_str       = ""                                       #clear line_str
            power_bytes    = bytes(str(power), 'ascii')               # convert to bytes
            ser.write(b'pwr '+ power_bytes + b'\n');                  # write on serial port 'pwr x' command
            time.sleep(.1)                                            # calm down a bit ...

            while True:
                line = ser.readline();
                if line:
                    line_str = ''.join(chr(i) for i in line)
                else:
                    print('...nothing received, trying again')
                    break
                if line_str[1:18] == 'Voltage         :': voltage      = int(line_str[-17:-11])/1000
                if line_str[1:18] == 'Current         :': current      = int(line_str[-17:-11])/1000
                if line_str[1:18] == 'Temperature     :': temp         = int(line_str[-17:-11])/1000
                if line_str[1:18] == 'Coulomb         :': soc          = int(line_str[-17:-11])
                if line_str[1:18] == 'Basic Status    :': basic_st     = line_str[-11:-5]        
                if line_str[1:18] == 'Volt Status     :': volt_st      = line_str[-11:-5]      
                if line_str[1:18] == 'Current Status  :': current_st   = line_str[-11:-5]     
                if line_str[1:18] == 'Tmpr. Status    :': temp_st      = line_str[-11:-5]     
                if line_str[1:18] == 'Coul. Status    :': coul_st      = line_str[-11:-5]
                if line_str[1:18] == 'Soh. Status     :': soh_st       = line_str[-11:-5]
                if line_str[1:18] == 'Heater Status   :': heater_st    = line_str[-10:-5]
                if line_str[1:18] == 'Bat Events      :': bat_events   = int(line_str[-15:-10],16)
                if line_str[1:18] == 'Power Events    :': power_events = int(line_str[-15:-10],16)
                if line_str[1:18] == 'System Fault    :': sys_events   = int(line_str[-15:-10],16)       
                if line_str[1:18]  == 'Command completed':
                    #ser.close()
                    
                    break

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
            print ('...serial parsing: ok')
            
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
                
            #print (pwr_array)                                        #DPO debug
            pwr.append(pwr_array)
        
        except Exception as e:
            print("...serial parsing error: " + str(e))
            errors = 'true'
    return

def json_serialize():
    global errors
    try:
        json_data={'relay_local_time':TimeStamp, 'serial_uptime':uptime, 'pytes':pwr}
        with open(output_path + 'pytes_status.json', 'w') as outfile:
            json.dump(json_data, outfile)
        print('...json creation:  ok')    
    except Exception as e:
        print('...json serailization error: ' + str(e))
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
        print('...mariadb writing error: ')

# --------------------------serial initialization-------------- 
try:
    ser = serial.Serial(port=serial_port,baudrate=serial_baudrate,\
          parity=serial.PARITY_NONE,\
          stopbits=serial.STOPBITS_ONE,\
          bytesize=serial.EIGHTBITS,\
          timeout=0)
    print('...connected to: ' + ser.portstr)
    
except:
    print('...serial connection error')
    
print('...initialisation completed starting main loop')

#-----------------------------main loop------------------------------
while True:
    if (time.time() - start_time) > reading_freq:                     #try every x sec
        now            = datetime.datetime.now()
        TimeStamp      = now.strftime("%Y-%m-%d %H:%M:%S")       
        print ('relay local time:', TimeStamp)
        
        start_time            = time.time() 
        uptime = round((time.time()- up_time)/86400,3)
        print ('serial uptime   :', uptime)

        if errors == 'false':
            parsing_serial()
        if errors == 'false':
            json_serialize()
        if errors == 'false' and SQL_active == 'true':
            maria_db()

        #clear variables
        pwr = []
        errors = 'false'