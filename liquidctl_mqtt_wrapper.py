#!/usr/bin/env python3
"""
liquidctl2mqtt - Wrapper script to send liquidctl sensor data to MQTT broker

This script executes liquidctl commands to gather sensor data from liquid cooling systems
and publishes the data to an MQTT broker with a structured topic hierarchy.
"""

import subprocess
import json
import sys
import logging
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import os


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/liquidctl2mqtt.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_liquidctl_command():
    """
    Run liquidctl status command and return the output.
    
    Returns:
        dict: Parsed JSON data from liquidctl or None if error
    """
    try:
        # Run liquidctl status command with JSON output
        result = subprocess.run(
            ['liquidctl', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )
        
        logger.info("Successfully executed liquidctl command")
        return json.loads(result.stdout)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"liquidctl command failed with return code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return None
    except subprocess.TimeoutExpired:
        logger.error("liquidctl command timed out")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse liquidctl JSON output: {e}")
        return None
    except FileNotFoundError:
        logger.error("liquidctl command not found. Please ensure liquidctl is installed and in PATH.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error running liquidctl: {e}")
        return None


def get_device_name():
    """
    Extract device name from liquidctl output or use default.
    
    Returns:
        str: Device name for MQTT topics
    """
    # Load configuration
    config = load_config()
    
    # Try to determine device name from environment, config, or system
    device_name = os.environ.get('LIQUIDCTL_DEVICE_NAME', config['liquidctl']['device_name'])
    
    # If we have data, try to extract more specific device info
    try:
        result = subprocess.run(
            ['liquidctl', 'status', '--json'],
            capture_output=True,
            text=True,
            timeout=30,
            check=False  # Don't raise exception on non-zero exit code
        )
        
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            
            # Try to get device name from the first device in the output
            if isinstance(data, list) and len(data) > 0:
                device_info = data[0]
                if 'device' in device_info:
                    device_name = device_info['device'].replace(' ', '_').lower()
                elif 'description' in device_info:
                    device_name = device_info['description'].replace(' ', '_').lower()
    except Exception as e:
        # If we can't determine a better name, keep the default
        logger.debug(f"Failed to extract device name from liquidctl output: {e}")
        pass
        
    return device_name


def load_config():
    """
    Load configuration from config.json file or use defaults
    
    Returns:
        dict: Configuration dictionary
    """
    config = {
        'mqtt': {
            'host': 'localhost',
            'port': 1883,
            'username': '',
            'password': ''
        },
        'liquidctl': {
            'device_name': 'liquid_cooling_system'
        }
    }
    
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                # Merge file config with defaults
                config.update(file_config)
                logger.info(f"Loaded configuration from {config_path}")
        else:
            logger.info("No config.json found, using defaults and environment variables")
    except Exception as e:
        logger.warning(f"Failed to load config.json: {e}, using defaults")
    
    return config


def publish_to_mqtt(data, device_name):
    """
    Publish sensor data to MQTT broker
    
    Args:
        data (dict): Sensor data from liquidctl
        device_name (str): Name of the cooling device
    """
    # Load configuration
    config = load_config()
    
    # MQTT Configuration - prioritize environment variables over config file
    mqtt_host = os.environ.get('MQTT_HOST', config['mqtt']['host'])
    mqtt_port = int(os.environ.get('MQTT_PORT', config['mqtt']['port']))
    mqtt_user = os.environ.get('MQTT_USER', config['mqtt']['username']) or None
    mqtt_password = os.environ.get('MQTT_PASSWORD', config['mqtt']['password']) or None
    
    # Create MQTT client with compatibility for different paho-mqtt versions
    try:
        # Try new API first (paho-mqtt >= 2.0) - use VERSION2 to avoid deprecation warning
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except (AttributeError, TypeError):
        try:
            # Try VERSION1 if VERSION2 is not available
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        except (AttributeError, TypeError):
            # Fall back to old API (paho-mqtt < 2.0)
            client = mqtt.Client()
    
    # Set credentials if provided
    if mqtt_user and mqtt_password:
        client.username_pw_set(mqtt_user, mqtt_password)
    
    try:
        # Connect to MQTT broker
        logger.info(f"Connecting to MQTT broker at {mqtt_host}:{mqtt_port}")
        client.connect(mqtt_host, mqtt_port, 60)
        
        # Start the loop to handle network traffic
        client.loop_start()
        
        # Publish each sensor reading with appropriate topic structure
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        if isinstance(data, list):
            for device_data in data:
                publish_device_sensors(client, device_data, device_name, timestamp)
        else:
            publish_device_sensors(client, data, device_name, timestamp)
            
        # Give time for messages to be sent
        time.sleep(1)
        
        # Stop the loop and disconnect
        client.loop_stop()
        client.disconnect()
        logger.info("Successfully published data to MQTT broker")
        
    except Exception as e:
        logger.error(f"Failed to publish to MQTT: {e}")
        return False
        
    return True


def publish_device_sensors(client, device_data, device_name, timestamp):
    """
    Publish all sensors from a single device
    
    Args:
        client: MQTT client instance
        device_data (dict): Data for one device
        device_name (str): Device name for topics
        timestamp (str): ISO timestamp for messages
    """
    # Extract device info if available
    if 'device' in device_data:
        device_id = device_data['device']
    elif 'description' in device_data:
        device_id = device_data['description']
    else:
        device_id = device_name
        
    # Handle different sensor types based on structure
    for key, value in device_data.items():
        if key == 'device' or key == 'description':
            continue
            
        # If the value is a dictionary of sensors, publish each one
        if isinstance(value, dict):
            for sensor_type, sensor_values in value.items():
                if isinstance(sensor_values, dict):
                    # Handle nested sensor data like {'temperature': {'cpu_core': 37.5}, 'fan': {'pump_speed': 2400}}
                    for sensor_name, sensor_value in sensor_values.items():
                        publish_single_sensor(client, device_name, sensor_type, sensor_name, sensor_value, timestamp)
                elif isinstance(sensor_values, list):
                    # Handle array of sensors
                    for i, item in enumerate(sensor_values):
                        if isinstance(item, dict) and 'name' in item and 'value' in item:
                            publish_single_sensor(client, device_name, sensor_type, item['name'], item['value'], timestamp)
                else:
                    # Handle direct sensor value
                    publish_single_sensor(client, device_name, sensor_type, key, sensor_values, timestamp)
        elif isinstance(value, list):
            # Handle array of sensors at the top level
            for i, item in enumerate(value):
                if isinstance(item, dict) and 'name' in item and 'value' in item:
                    publish_single_sensor(client, device_name, key, item['name'], item['value'], timestamp)
        else:
            # Handle direct sensor values
            publish_single_sensor(client, device_name, 'general', key, value, timestamp)


def publish_single_sensor(client, device_name, sensor_type, sensor_name, sensor_value, timestamp):
    """
    Publish a single sensor reading to MQTT
    
    Args:
        client: MQTT client instance
        device_name (str): Device name for topics
        sensor_type (str): Type of sensor (temperature, fan, etc.)
        sensor_name (str): Name of specific sensor
        sensor_value: Value of the sensor reading
        timestamp (str): ISO timestamp for messages
    """
    # Create topic with hierarchical structure
    topic = f"liquidctl/{device_name}/{sensor_type}/{sensor_name}"
    
    # Prepare message payload
    payload = {
        "timestamp": timestamp,
        "sensor_type": sensor_type,
        "sensor_name": sensor_name,
        "value": sensor_value
    }
    
    try:
        logger.info(f"Publishing to {topic}: {sensor_value}")
        client.publish(topic, json.dumps(payload), qos=1)
    except Exception as e:
        logger.error(f"Failed to publish sensor {sensor_name} to topic {topic}: {e}")


def main():
    """Main execution function"""
    logger.info("Starting liquidctl2mqtt wrapper")
    
    # Get device name
    device_name = get_device_name()
    
    # Run liquidctl command
    data = run_liquidctl_command()
    
    if data is None:
        logger.error("No data retrieved from liquidctl, exiting")
        return 1
    
    # Publish to MQTT
    success = publish_to_mqtt(data, device_name)
    
    if success:
        logger.info("Data successfully published to MQTT")
        return 0
    else:
        logger.error("Failed to publish data to MQTT")
        return 1


if __name__ == "__main__":
    sys.exit(main())