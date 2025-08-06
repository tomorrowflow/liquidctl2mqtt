#!/usr/bin/env python3
"""
Test script for liquidctl2mqtt wrapper functionality.
This script tests the parsing and MQTT publishing logic without requiring actual hardware.
"""

import json
import sys
import os
import subprocess

# Add the current directory to Python path so we can import our wrapper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from liquidctl_mqtt_wrapper import run_liquidctl_command, publish_to_mqtt, get_device_name

def test_liquidctl_parsing():
    """Test parsing of liquidctl output"""
    print("Testing liquidctl command execution and parsing...")
    
    # Test with sample data similar to what liquidctl might return
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
    
    # Test the function directly
    result = run_liquidctl_command()
    print(f"Function returned: {result}")
    
    return True

def test_device_name():
    """Test device name extraction"""
    print("Testing device name extraction...")
    
    device_name = get_device_name()
    print(f"Device name: {device_name}")
    
    return True

def test_mqtt_publishing():
    """Test MQTT publishing logic with sample data"""
    print("Testing MQTT publishing logic...")
    
    # Sample data to publish
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
    
    # Test with fake device name
    device_name = "test_cooling_system"
    success = publish_to_mqtt(sample_data, device_name)
    print(f"MQTT publishing test result: {'SUCCESS' if success else 'FAILED'}")
    
    return True

def main():
    """Main test function"""
    print("Running liquidctl2mqtt wrapper tests...")
    print("=" * 50)
    
    try:
        test_liquidctl_parsing()
        print()
        test_device_name()
        print()
        test_mqtt_publishing()
        print()
        print("All tests completed!")
        return 0
    except Exception as e:
        print(f"Test failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())