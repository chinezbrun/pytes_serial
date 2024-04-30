# Follow below steps if you want to install Pytes_Serial as a background service

## 1. Copy the example service to `/etc/systemd/system/`
```
sudo cp examples/pytes_serial.service /etc/systemd/system/
```

## 2. Change the configuration file with an editor (e.g. nano)
```
sudo nano /etc/systemd/system/pytes_serial.service
```

The default file assumes this repository was cloned in `/home/pi/pytes_serial`. Change these paths according to the installation.

If you created a Python virtual environment, make sure you call the script using the executable in the environment (e.g. `/home/pi/pytes_serial/.venv/bin/python`) instead of the system one (`/usr/bin/python3`).

## 3. Notify the system that it has a new service
```
sudo systemctl daemon-reload
```

## 4. Configure the Pytes_Serial service to start in the background at boot
```
sudo systemctl enable pytes_serial
```

## 5. (optional) Start the Pytes_Serial service and check that it's running
```
sudo systemctl start pytes_serial
sudo systemctl status pytes_serial
```

There are more useful command you can use with `systemctl`:
- `enable`/`disable` are used to configure whether the service should start at boot or not
- `start`/`stop` are used to run and close the program
- `status` can be used to determine at a glance whether the program is running or not

## 6. (optional) Check the console output
To check the past output starting from the most recent, use
```
sudo journalctl -eu pytes_serial
```

To start printing the console output in real-time, use
```
sudo journalctl -fu pytes_serial
```
