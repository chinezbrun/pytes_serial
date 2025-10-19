### PYTES E-BOX 48100R / PYLONTECH to Home Assistant / MariaDB 
The program reads the RS232 serial port of PYTES and PYLONTECH LiFePO4 batteries.

### How does this software work?
The "pwr" and "bat" commands are used.  
The program reads the serial port at a specific frequency, parses the data, and saves a JSON file that can be used for further automation.  

Configurable OPTIONS:
- record data to MariaDB  
- send data via MQTT  
- events monitoring – when power events, battery events, or system faults occur, a log file is created with cell details  
- cell monitoring – read cell details for all batteries in the bank. Three levels of detail can be selected in the config file.  
  More details can be found [here](/docs/configuration_details.txt)  

These options can be activated or deactivated in the configuration file (`pytes_serial.cfg`).  

When MQTT transmission is activated:
- The JSON file is sent as a payload to the following topic:  
  `homeassistant/sensor/pytes/state`
- The program has built-in integration with Home Assistant, where the following sensors are automatically created for each battery: `current`, `voltage`, `temperature`, `soc`, and `status`.  
  The battery number is appended at the end of each sensor (e.g. `current_1`, `current_2...`).  

When cell monitoring is activated, an additional device will be created in Home Assistant with the suffix `_cells`, with all associated sensors. The battery and cell number are appended at the end of each sensor (e.g. `voltage_102` means voltage for battery 1 cell 2).  
Basic statistics are also implemented. Therefore, additional sensors will be available for min, max, and delta values of cell voltage and temperature.  
(e.g. `pytes_cells_voltage_max_1` means max cell voltage for battery 1).  

If more sensors are needed, they can be added manually according to the Home Assistant documentation: [MQTT sensor](https://www.home-assistant.io/integrations/sensor.mqtt/) and the example in the docs folder [here](/docs/home_assistant_add_sensor.txt).  

An experimental feature is implemented that allows recording a specific event (power events, system events) in the log file when needed. The file `events_config.json` is a list of all known events. Changing in the file the level from 'info' to 'warning' will do the trick. 

You can find more [examples](/examples) for a better understanding of what the program does.  

---

### Installation and Execution
The serial cable must be connected to battery 1 (master).  

1. Copy the current repository.  
2. Optional:  
   a. If you want to use MariaDB:  
      - MariaDB must be installed (MariaDB documentation is outside this project's scope).  
      - Use `sql/pytes_mariadb.sql` to import the required database and tables.  
   b. If you want to use MQTT / MQTT integration in Home Assistant:  
      - An MQTT broker must be installed (MQTT documentation is outside this project's scope).  
      - If you use Home Assistant, make sure that MQTT auto-discovery is enabled so sensors will be auto-discovered when the program starts.  
3. Rename `pytes_serial.cfg.example` to `pytes_serial.cfg` and configure it as needed (do not remove or comment out lines in sections, just set the values).  
4. Make sure that all required Python modules are installed – see [requirements](/REQUIREMENTS.md).  
5. Go to the folder where the program is located (e.g. `cd /home/pi/Documents/pytes`).  
6. Execute `pytes_serial.sh` to run in a separate terminal instance (Linux/Raspberry) or run `python3 pytes_serial.py` directly from the console.  
   - For autostart on reboot, see more info [here](/docs/).
   
---

A lighter version written in MicroPython for ESP32 is available here: [pytes_esp](https://github.com/chinezbrun/pytes_esp).  

Enjoy!
