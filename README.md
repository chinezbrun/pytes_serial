### PYTES E-BOX 48100R / PYLONTECH to Home Assistant / MariaDB 
Program is reading RS232 serial port of PYTES and PYLONTECH LiFePo4 batteries.

### How does this software work?
 "pwr" and "bat" commands are used.
Program reads serial port with a specific freqvency, parsing the data and saving a JSON file that can be used in further automation. 

Configurable OPTIONS:
- record data to MariaDB
- send data via MQTT
- events monitoring - when power_events, battery_events or system faults occured a log file is created with cells details 
- cell monitoring - read cells details for all batteries in bank. Three levels of details can be selected in config file.
  more details/explanation can be found [here](/docs/configuration_details.txt)
  
These options can be activated / dezactivated in configuration file (pytes_serial.cfg)

When MQTT transmition is activated:
- JSON file is send as payload to the following topic: 'homeassistant/sensor/pytes/state'
- program has build-in integration with Home Assisant where the following sensors will be automatic created for each battery:"current", "voltage", "temperature", "soc", "status".
   The battery number is embeded at the end of each sensor (i.e current_1, current_2...).

   When cell monitoring is activated an additional device will be created in Home Assistant with sufix "_cells" with all associated sensors. The battery and cell number is embeded at the end of each sensor ( i.e. voltage_102 means voltage for battery 1 cell 2).
   Basic statistics is implemented too. Therefore, additional sensors will be available for min, max and delta for cells voltage and temperature. 
   (i.e. pytes_cells_voltage_max_1 means max cells voltage for battery 1)  
  
  If more sensors will be needed, they can be added manually as per Home Assistant documentation [MQTT sensor](https://www.home-assistant.io/integrations/sensor.mqtt/) and the example in docs folder [here](/docs/home_assistant_add_sensor.txt).

You have more [examples](/examples) for better understanding of what program does.

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

3. reaname pytes_serial.cfg.example in pytes_serial.cfg and configure it as per your needs (do not remark or delete lines in sections just do the configuration)
4. make sure that all required pyton modules are installed see [requirements](/REQUIREMENTS.md)
5. go to the folder where the program is located (i.e cd /home/pi/Documents/pytes)
6. execute pytes_serial.sh to have a separate terminal instance (works for Linux/Raspberry) or python3 pytes_serial.py directly from console.
   if you need setup an autostart of the program on reboot more info [here](/docs/) 

A lighter version written in Micropython for ESP32 is available here:[pytes_esp](https://github.com/chinezbrun/pytes_esp)

enjoy
