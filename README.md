# pytes_serial
 Program is reading RS232 serial port of PYTES LiFePo4 batteries
 
### How does this software work?
 "pwr" commands is used.
Program reads PYTES serial with a specific freqvency, parsing the data and saving a JSON file that
can be used in further automation. 

Optional, with proper configuration, there is the possibility to save data to MariaDB database.

### Installation and Execution
Serial cable must be connected to battery 1 (master).
1. copy current repository 
3. if you need to use MariaDB:
   - database must be installed
   - use sql/pytes_mariadb.sql to import required database and tables
3. configure pytes_serial.cfg as per your needs
4. make sure that required pyton modules are installed
5. run pytes_serial.py
enjoy