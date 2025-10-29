Smart Warehouse Simulation
==========================

Run the multi-agent warehouse simulation (Tkinter GUI) using Python 3.10.

Prerequisites
- Python 3.10 installed and available on PATH
- Windows PowerShell (instructions below)

Quick start (PowerShell)
-------------------------
```powershell
# create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install requirements
pip install -r requirements.txt

# run the simulation (change num-robots as desired)
python main.py --num-robots 4
```

Notes
- The simulation uses the public MQTT broker `broker.hivemq.com` by default for broadcasting cell reservations. If you want to run disconnected or without MQTT, you can modify `mqtt_manager.py` to bypass network calls.
- If Tkinter is not installed with your Python distribution, install a standard Windows Python installer from python.org that includes Tkinter.
