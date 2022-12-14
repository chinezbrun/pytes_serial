### pytes_serial
 Program is reading RS232 serial port of PYTES and PYLONTECH LiFePo4 batteries
 
### How does this software work?
 "pwr" commands is used.
Program reads serial port with a specific freqvency, parsing the data and saving a JSON file that can be used in further automation. 

Optional, there is the possibility to save data to MariaDB database or to send them via MQTT.
These options can be activated / dezactivated in configuration file (pytes_serial.cfg)

When MQTT transmition is activated:
- JSON file is send as payload to the following topic: 'homeassistant/sensor/pytes/state'
- program has build-in integration with Home Assisant where the following sensors will be created for each battery:
  "pytes_current", "pytes_voltage", "pytes_temperature", "pytes_soc", "pytes_status"
   the battery number is embeded at the end of each sensor (i.e pytes_current_1, pytes_current_2...) 

You have some [examples](/examples) for better understanding of what program does.

### Installation and Execution
Serial cable must be connected to battery 1 (master).
1. copy current repository 
2. optional:
   a. if you want to use MariaDB:
      - MariaDB database must be installed (MariaDB documentaion is out of this project scope)
      - use sql/pytes_mariadb.sql to import required database and tables
      
   b. if you want to use MQTT / MQTT integration in Home Assistant:
    - MQTT broker must be installed (MQTT documentation is out of this project scope)
    - if you use Home Assistant, make sure that MQTT auto discovery is set true and sensors will be auto discovered when program will start

3. configure pyteys_serial.cfg as per your needs (do not remark or delete lines in sections just do the configuration)
4. make sure that all required pyton modules are installed see [requirements](/REQUIREMENTS.md)
5. go to the folder where the program is located (i.e cd /home/pi/Documents/pytes)
6. execute pytes_serial.sh to have a separate terminal instance (works for Linux/Raspberry) or python3 pytes_serial.py directly from console

enjoy

Thanks to [valimircea-popescu](https://github.com/valimircea-popescu) for conducting the testing on Pylontech batteries.