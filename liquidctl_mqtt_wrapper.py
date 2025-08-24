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
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
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


class NvidiaSmiError(Exception):
    """Custom exception for nvidia-smi command errors."""
    pass


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


def get_gpu_metrics():
    """
    Executes nvidia-smi command, parses output for GPU name, temperatures, and power, and returns them.

    Returns:
        list: A list of dictionaries, each containing 'name' (str), 'temperature' (int) and 'power' (float) for a GPU.

    Raises:
        NvidiaSmiError: If nvidia-smi command fails or returns unexpected output.
    """
    try:
        command = ['nvidia-smi', '--query-gpu=name,temperature.gpu,power.draw', '--format=csv,noheader,nounits']
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=True
        )

        gpu_metrics = []
        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if line:
                try:
                    # Example: "NVIDIA GeForce RTX 3090, 45, 120.50" (name, temperature, power)
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) == 3:
                        name, temp_str, power_str = parts
                        temperature = int(temp_str)
                        power = float(power_str)
                        gpu_metrics.append({'name': name, 'temperature': temperature, 'power': power})
                    else:
                        logger.warning(f"Could not parse GPU metrics from line (expected 3 parts): '{line}'")
                except ValueError as ve:
                    logger.warning(f"Could not parse GPU metrics from line '{line}': {ve}")
        return gpu_metrics
    except FileNotFoundError:
        logger.warning("Command 'nvidia-smi' not found. Assuming no NVIDIA GPUs or drivers.")
        return []
    except subprocess.CalledProcessError as e:
        raise NvidiaSmiError(
            f"nvidia-smi command failed with exit code {e.returncode}. "
            f"Error: {e.stderr.strip()}"
        ) from e
    except subprocess.TimeoutExpired:
        raise NvidiaSmiError("nvidia-smi command timed out.")
    except Exception as e:
        raise NvidiaSmiError(f"An unexpected error occurred while getting GPU metrics: {e}") from e


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
            'password': '',
            'mqtt_topic_base': 'home/liquidctl', # Default topic base for liquidctl
            'nvidia_gpu_topic_base': 'home/nvidia_gpu' # Default topic base for NVIDIA GPU
        },
        'liquidctl': {
            'device_name': 'my_cooling_system',
            'units_enabled': False
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


def publish_to_mqtt(client, data, device_name, timestamp, units_enabled, mqtt_topic_base, nvidia_gpu_topic_base):
    """
    Publish sensor data to MQTT broker.
    This function expects an already connected MQTT client.
    
    Args:
        client: MQTT client instance.
        data (Union[dict, list]): Sensor data to publish.
        device_name (str): Name of the cooling device. Used for topic construction.
        timestamp (str): ISO timestamp for messages.
        units_enabled (bool): Whether to include units in the payload.
        mqtt_topic_base (str): Base topic for liquidctl data.
        nvidia_gpu_topic_base (str): Base topic for NVIDIA GPU data.
    """
    if isinstance(data, list):
        for device_data in data:
            publish_device_sensors(client, device_data, device_name, timestamp, units_enabled, mqtt_topic_base, nvidia_gpu_topic_base)
    else:
        publish_device_sensors(client, data, device_name, timestamp, units_enabled, mqtt_topic_base, nvidia_gpu_topic_base)
    logger.info("Data queued for publishing")


def publish_device_sensors(client, device_data, device_name, timestamp, units_enabled, mqtt_topic_base, nvidia_gpu_topic_base):
    """
    Publish all sensors from a single device
    
    Args:
        client: MQTT client instance
        device_data (dict): Data for one device
        device_name (str): The logical device name (e.g., 'nvidia_gpu' or the liquidctl device name).
        timestamp (str): ISO timestamp for messages
        units_enabled (bool): Whether to include units in the payload
        mqtt_topic_base (str): The base topic for liquidctl MQTT messages
        nvidia_gpu_topic_base (str): The base topic for NVIDIA GPU MQTT messages
    """
    # Determine the topic base to use based on the `device_name` passed to this function.
    # `device_name` here will be either the liquidctl device name or a specific GPU device_id (e.g., 'nvidia_geforce_rtx_3090_gpu_0').
    # We check if the device_name matches the pattern for GPU devices to use the correct topic base.
    is_gpu_device = device_name.startswith('nvidia_') and '_gpu_' in device_name
    current_topic_base = nvidia_gpu_topic_base if is_gpu_device else mqtt_topic_base
    
    # Extract topic_device_id. If it's a GPU device, use the device_name directly as it's already unique.
    if is_gpu_device:
        topic_device_id = device_name
    elif 'device' in device_data:
        topic_device_id = device_data['device'].replace(' ', '_').lower()
    elif 'description' in device_data:
        topic_device_id = device_data['description'].replace(' ', '_').lower()
    else:
        topic_device_id = device_name.replace(' ', '_').lower() # Fallback

    # Handle liquidctl status format with 'status' array or GPU data
    if 'status' in device_data and isinstance(device_data['status'], list):
        for sensor in device_data['status']:
            if isinstance(sensor, dict) and 'key' in sensor and 'value' in sensor:
                sensor_key = sensor['key']
                sensor_value = sensor['value']
                sensor_unit = sensor.get('unit', '')
                
                # For liquidctl data, categorize sensor key to get type, then clean name
                if not is_gpu_device:
                    sensor_type = categorize_sensor(sensor_key)
                    sensor_name = sensor_key.lower().replace(' ', '_')
                else: # For GPU data, key is already sensor_type/name (e.g., 'temperature', 'power')
                    sensor_type = sensor_key.lower()
                    sensor_name = sensor_key.lower()


                # Create payload with conditional unit information
                payload = {
                    "timestamp": timestamp,
                    "sensor_type": sensor_type,
                    "sensor_name": sensor_name,
                    "value": sensor_value,
                    "original_key": sensor_key # Keep original key for debugging/reference
                }
                
                # Add unit field only if units are enabled
                if units_enabled and sensor_unit:
                    payload["unit"] = sensor_unit
                
                # Create topic with hierarchical structure
                # For GPU, this will now be: home/nvidia_gpu/{gpu_device_id}/{sensor_type}
                # For liquidctl, it remains: home/liquidctl/{aquacomputer_quadro}/{sensor_type}/{sensor_name}
                if is_gpu_device:
                    topic = f"{current_topic_base}/{topic_device_id}/{sensor_type}"
                else:
                    topic = f"{current_topic_base}/{topic_device_id}/{sensor_type}/{sensor_name}"
                
                try:
                    unit_display = f" {sensor_unit}" if units_enabled and sensor_unit else ""
                    logger.info(f"Publishing to {topic}: {sensor_value}{unit_display}")
                    client.publish(topic, json.dumps(payload), qos=1)
                except Exception as e:
                    logger.error(f"Failed to publish sensor {sensor_name} to topic {topic}: {e}")
    else:

        # Fallback for unexpected data structure or direct sensor values, not typically used for current GPU data format.
        logger.warning(f"Unexpected data format in publish_device_sensors (no 'status' list): {device_data}. Attempting generic publish.")
        for key, value in device_data.items():
            if key in ['device', 'description', 'bus', 'address']:
                continue
            publish_single_sensor(client, topic_device_id, 'general', key, value, timestamp, units_enabled, current_topic_base)


def categorize_sensor(sensor_key):
    """
    Categorize sensor based on its key name
    
    Args:
        sensor_key (str): The sensor key name
        
    Returns:
        str: Category for the sensor
    """
    key_lower = sensor_key.lower()
    
    if 'temp' in key_lower or '°c' in key_lower:
        return 'temperature'
    elif 'fan' in key_lower and ('speed' in key_lower or 'rpm' in key_lower):
        return 'fan_speed'
    elif 'fan' in key_lower and 'power' in key_lower:
        return 'fan_power'
    elif 'fan' in key_lower and 'voltage' in key_lower:
        return 'fan_voltage'
    elif 'fan' in key_lower and 'current' in key_lower:
        return 'fan_current'
    elif 'flow' in key_lower:
        return 'flow'
    elif 'pump' in key_lower:
        return 'pump'
    elif 'voltage' in key_lower:
        return 'voltage'
    elif 'current' in key_lower:
        return 'current'
    elif 'power' in key_lower:
        return 'power'
    else:
        return 'sensor'


def publish_single_sensor(client, device_name, sensor_type, sensor_name, sensor_value, timestamp, units_enabled, target_mqtt_topic_base):
    """
    Publish a single sensor reading to MQTT
    
    Args:
        client: MQTT client instance
        device_name (str): Device name for topics
        sensor_type (str): Type of sensor (temperature, fan, etc.)
        sensor_name (str): Name of specific sensor
        sensor_value: Value of the sensor reading
        timestamp (str): ISO timestamp for messages
        units_enabled (bool): Whether to include units in the payload
        target_mqtt_topic_base (str): The base topic to use for MQTT messages (either liquidctl or nvidia_gpu)
    """
    # For GPU metrics, sensor_type is already the category (e.g., 'temperature', 'power').
    # We want the topic to be: home/nvidia_gpu/{gpu_name_gpu_X}/{sensor_type}
    # So, effectively, sensor_name should be omitted from the topic if it's identical to sensor_type.
    # We'll use the device_name derived from the GPU for the topic_device_id and sensor_type directly.
    
    # Create topic with hierarchical structure
    topic = f"{target_mqtt_topic_base}/{device_name}/{sensor_type}/{sensor_name}"
    
    # Prepare message payload
    payload = {
        "timestamp": timestamp,
        "sensor_type": sensor_type,
        "sensor_name": sensor_name,
        "value": sensor_value
    }
    
    # Note: This function doesn't have access to unit information from the original sensor data
    # Units are primarily handled in publish_device_sensors for the main liquidctl status format
    
    try:
        logger.info(f"Publishing to {topic}: {sensor_value}")
        client.publish(topic, json.dumps(payload), qos=1)
    except Exception as e:
        logger.error(f"Failed to publish sensor {sensor_name} to topic {topic}: {e}")


def main():
    """Main execution function"""
    logger.info("Starting liquidctl2mqtt wrapper")

    # Load configuration
    config = load_config()
    
    # MQTT Configuration - prioritize environment variables over config file
    mqtt_host = os.environ.get('MQTT_HOST', config['mqtt']['host'])
    mqtt_port = int(os.environ.get('MQTT_PORT', config['mqtt']['port']))
    mqtt_user = os.environ.get('MQTT_USER', config['mqtt']['username']) or None
    mqtt_password = os.environ.get('MQTT_PASSWORD', config['mqtt']['password']) or None
    mqtt_topic_base = os.environ.get('MQTT_TOPIC_BASE', config['mqtt']['mqtt_topic_base'])
    nvidia_gpu_topic_base = os.environ.get('NVIDIA_GPU_TOPIC_BASE', config['mqtt']['nvidia_gpu_topic_base'])

    # Units configuration - prioritize environment variable over config file
    units_enabled = os.environ.get('LIQUIDCTL_UNITS_ENABLED', str(config['liquidctl']['units_enabled'])).lower() in ('true', '1', 'yes', 'on')

    # Generate timestamp for all messages
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    liquidctl_device_name = get_device_name()
    
    # Run liquidctl command
    liquidctl_data = run_liquidctl_command()
    
    if liquidctl_data is None:
        logger.info("No data retrieved from liquidctl.")
        liquidctl_data = [] # Ensure it's an empty list if no liquidctl data
    elif not isinstance(liquidctl_data, list):
        liquidctl_data = [liquidctl_data] # Ensure liquidctl_data is a list for consistent processing

    # Get GPU metrics
    gpu_data_list = []
    try:
        gpu_metrics = get_gpu_metrics()
        if gpu_metrics:
            for i, metrics in enumerate(gpu_metrics):
                gpu_name_base = metrics.get('name', 'nvidia_gpu').replace(' ', '_').lower()
                unique_gpu_device_id = f"{gpu_name_base}_gpu_{i}"
                
                gpu_status_list = []
                gpu_status_list.append({'key': 'temperature', 'value': metrics['temperature'], 'unit': '°C'})
                gpu_status_list.append({'key': 'power', 'value': metrics['power'], 'unit': 'W'})
                
                gpu_data_list.append({
                    'device': unique_gpu_device_id,
                    'description': f'NVIDIA GPU {i} Metrics',
                    'status': gpu_status_list
                })
            logger.info(f"Successfully retrieved GPU metrics: {gpu_metrics}")
    except NvidiaSmiError as e:
        logger.error(f"Failed to get GPU metrics: {e}. Returning empty list for GPU metrics.")
    except Exception as e:
        logger.error(f"Unexpected error while getting GPU metrics: {e}. Returning empty list for GPU metrics.")

    # Check if we have any data to publish
    if not liquidctl_data and not gpu_data_list:
        logger.error("No data (liquidctl or GPU) retrieved, exiting.")
        return 1

    # Create MQTT client with compatibility for different paho-mqtt versions
    client = None
    try:
        # Try new API first (paho-mqtt >= 2.0) - use VERSION2 to avoid deprecation warning
        client = mqtt.Client(CallbackAPIVersion.VERSION2)
    except (AttributeError, TypeError):
        try:
            # Try VERSION1 if VERSION2 is not available (paho-mqtt < 2.0)
            client = mqtt.Client(CallbackAPIVersion.VERSION1)
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
        
        # Publish liquidctl data
        if liquidctl_data:
            logger.info("Publishing liquidctl data to MQTT")
            publish_to_mqtt(client, liquidctl_data, liquidctl_device_name, timestamp, units_enabled, mqtt_topic_base, nvidia_gpu_topic_base)
        
        # Publish GPU data
        if gpu_data_list:
            logger.info("Publishing NVIDIA GPU data to MQTT")
            # Since gpu_data_list now contains one entry per GPU, with its unique device ID,
            # we iterate through it and publish each GPU's data individually.
            # The 'device_name' argument to publish_to_mqtt is expected to be a single string for the primary device.
            # For GPU data, each entry in gpu_data_list itself represents a distinct 'device' for topic construction,
            # so we'll pass the 'device' from each list item directly.
            for gpu_device_data in gpu_data_list:
                actual_gpu_device_name = gpu_device_data.get('device', 'nvidia_gpu')
                publish_to_mqtt(client, gpu_device_data, actual_gpu_device_name, timestamp, units_enabled, mqtt_topic_base, nvidia_gpu_topic_base)

        # Give time for messages to be sent before disconnecting
        time.sleep(1)
        
        # Stop the loop and disconnect
        client.loop_stop()
        client.disconnect()
        
        logger.info("All relevant data successfully published to MQTT")
        return 0
        
    except Exception as e:
        logger.error(f"Failed to publish to MQTT: {e}")
        if client:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
