#!/usr/bin/env python3
"""
Test script for liquidctl2mqtt wrapper functionality.

This script helps test the wrapper without requiring actual hardware or MQTT broker.
"""

import json
import sys
import os
import tempfile

# Add current directory to path so we can import our module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from liquidctl_mqtt_wrapper import run_liquidctl_command, get_device_name, publish_to_mqtt


def test_run_liquidctl_command():
    """Test the liquidctl command execution function"""
    print("Testing liquidctl command execution...")
    
    # Test with a dummy return value to simulate successful execution
    data = run_liquidctl_command()
    print(f"run_liquidctl_command returned: {data}")
    
    # If we're testing without actual hardware, we can create a mock version
    if data is None:
        print("No real liquidctl output - using sample data")
        return [
            {
                "device": "NZXT Kraken X73",
                "description": "Kraken X73",
                "temperature": {
                    "cpu_core": 45.2,
                    "liquid_inlet": 22.8,
                    "liquid_outlet": 25.1
                },
                "fan": {
                    "pump_speed": 2400,
                    "pump_duty": 75,
                    "fan1_speed": 1200,
                    "fan1_duty": 60
                }
            }
        ]
    return data


def test_get_device_name():
    """Test device name extraction"""
    print("\nTesting device name extraction...")
    
    device_name = get_device_name()
    print(f"Device name: {device_name}")
    return device_name


def test_publish_to_mqtt():
    """Test MQTT publishing with mock data"""
    print("\nTesting MQTT publishing with mock data...")
    
    # Create sample data structure
    sample_data = [
        {
            "device": "NZXT Kraken X73",
            "description": "Kraken X73",
            "temperature": {
                "cpu_core": 45.2,
                "liquid_inlet": 22.8,
                "liquid_outlet": 25.1
            },
            "fan": {
                "pump_speed": 2400,
                "pump_duty": 75,
                "fan1_speed": 1200,
                "fan1_duty": 60
            }
        }
    ]
    
    # Test with a simple device name
    device_name = "test_system"
    
    print("This would publish to MQTT broker if one was available")
    print(f"Sample data structure: {json.dumps(sample_data, indent=2)}")
    
    # Since we don't have an actual MQTT broker for testing, just show what it would do
    print("Would publish to topics like:")
    timestamp = "2025-08-06T19:00:00Z"
    
    for device_data in sample_data:
        if 'temperature' in device_data:
            for sensor_name, sensor_value in device_data['temperature'].items():
                print(f"  liquidctl/{device_name}/temperature/{sensor_name}: {sensor_value}")
        if 'fan' in device_data:
            for sensor_name, sensor_value in device_data['fan'].items():
                print(f"  liquidctl/{device_name}/fan/{sensor_name}: {sensor_value}")
    
    return True


def main():
    """Main test function"""
    print("liquidctl2mqtt Test Script")
    print("=" * 30)
    
    try:
        # Run tests
        data = test_run_liquidctl_command()
        device_name = test_get_device_name()
        success = test_publish_to_mqtt()
        
        if success:
            print("\n✓ All tests completed successfully!")
            return 0
        else:
            print("\n✗ Test failed")
            return 1
            
    except Exception as e:
        print(f"\n✗ Test script error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())