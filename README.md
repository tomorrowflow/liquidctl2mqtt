# liquidctl2mqtt

A wrapper script that executes `liquidctl` commands to gather sensor data from liquid cooling systems and publishes it to an MQTT broker.

## Features

- Automatically detects connected liquid cooling devices
- Parses sensor data from liquidctl output
- Publishes data to MQTT with structured topics
- Runs as a cronjob every minute
- Handles errors gracefully with logging

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure `liquidctl` is installed and working on your system:
   ```bash
   liquidctl --version
   ```

3. Configure MQTT broker connection details (see Configuration section)

## Configuration

Set environment variables for MQTT connection:

```bash
export MQTT_HOST=localhost
export MQTT_PORT=1883
export MQTT_USER=your_username  # optional
export MQTT_PASSWORD=your_password  # optional
export LIQUIDCTL_DEVICE_NAME=my_cooling_system  # optional custom device name
```

## Usage

Run manually:
```bash
python liquidctl_mqtt_wrapper.py
```

Or schedule with cron:
```bash
# Add to crontab for minute-by-minute execution
* * * * * /usr/bin/python3 /path/to/liquidctl2mqtt/liquidctl_mqtt_wrapper.py
```

## MQTT Topics

Data is published to topics in the format:
```
liquidctl/{device_name}/{sensor_type}/{sensor_name}
```

Examples:
- `liquidctl/kraken_x73/temperature/cpu_core`
- `liquidctl/kraken_x73/fan/pump_speed`
- `liquidctl/kraken_x73/liquid/temperature`

## Data Format

Each message is a JSON object containing:
```json
{
  "timestamp": "2025-08-06T19:00:00Z",
  "sensor_type": "temperature",
  "sensor_name": "cpu_core", 
  "value": 37.5,
  "unit": "°C"
}
```

## Logging

Logs are written to `/var/log/liquidctl2mqtt.log` and stdout.

## Prerequisites

- Python 3.x
- liquidctl installed on system
- MQTT broker running at localhost:1883 (configurable via environment variables)