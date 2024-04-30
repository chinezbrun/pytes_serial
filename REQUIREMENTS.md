- Python >3.5 (tested 3.10)
- Install the required Python modules:
    - Option A - System install:
        ```
        sudo python3 -m pip install -r requirements.txt
        ```
    - Option B - Virtual environment:
        ```
        sudo python3 -m pip install virtualenv
        python3 -m virtualenv .venv
        source .venv/bin/activate
        pip install -r requirements.txt
        ```
- MariaDB database (optional)
- MQTT broker i.e Mosquitto (optional)
