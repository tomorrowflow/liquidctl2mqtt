# liquidctl2mqtt Wrapper Plan

## Overview
Create a Python script that:
1. Executes the `liquidctl` command-line tool to gather sensor data from liquid cooling systems
2. Parses the output data
3. Publishes the data to an MQTT broker with appropriate topic structure
4. Can be scheduled as a cronjob to run every minute

## System Architecture

### Data Flow
```
[liquidctl command] --> [parse output] --> [MQTT publish] --> [MQTT broker]
```

### Requirements Analysis

#### 1. liquidctl Command
Based on liquidctl documentation, it's typically used with commands like:
- `liquidctl status` - to get current sensor readings
- `liquidctl monitor` - to get monitoring data (if available)

The output is usually in CSV or JSON format, depending on the command and flags used.

#### 2. MQTT Publishing Structure

##### Topic Naming Convention
We'll use a hierarchical topic structure:
```
liquidctl/{device_name}/{sensor_type}/{sensor_name}
```

Example topics:
- `liquidctl/kraken_x73/temperature/cpu_core`
- `liquidctl/kraken_x73/fan/pump_speed`
- `liquidctl/kraken_x73/liquid/temperature`
- `liquidctl/kraken_x73/power/consumption`

##### Data Format
MQTT messages will be JSON formatted:
```json
{
  "timestamp": "2025-08-06T19:00:00Z",
  "sensor_type": "temperature",
  "sensor_name": "cpu_core",
  "value": 37.5,
  "unit": "°C"
}
```

Or for multiple sensors:
```json
{
  "timestamp": "2025-08-06T19:00:00Z",
  "sensors": {
    "cpu_core": {"value": 37.5, "unit": "°C"},
    "pump_speed": {"value": 2400, "unit": "RPM"}
  }
}
```

#### 3. Python Script Implementation Requirements

- Execute liquidctl command via subprocess
- Parse liquidctl output (CSV or JSON format)
- Handle different devices and their sensors dynamically
- Connect to MQTT broker at localhost:1883 
- Publish data to appropriate MQTT topics
- Include error handling and logging
- Support for environment variables or config file for MQTT credentials

#### 4. Cronjob Configuration

- Run every minute
- Execute with proper environment (PATH, etc.)
- Logging output to file
- Handle potential errors gracefully

## Implementation Steps

1. Create a Python script that executes liquidctl status command
2. Parse the output data to extract sensor readings
3. Set up MQTT connection and publish logic
4. Implement error handling and logging
5. Create cronjob configuration
6. Test with sample data

## File Structure
```
liquidctl2mqtt/
├── liquidctl_mqtt_wrapper.py     # Main wrapper script
├── config.json                 # Configuration for MQTT details (if needed)
├── README.md                   # Documentation
└── cronjob_setup.sh          # Cron setup script
```

## Technology Stack
- Python 3.x
- paho-mqtt library for MQTT communication
- subprocess module to execute liquidctl
- argparse or environment variables for configuration

## Design Considerations
1. The script should be robust and handle cases where liquidctl fails or returns unexpected output
2. Topic names should be standardized and hierarchical for easy consumption by MQTT clients
3. Error logging should capture both liquidctl execution issues and MQTT publish failures
4. Should handle multiple devices if connected
5. Timestamps should be included in all messages for proper data tracking