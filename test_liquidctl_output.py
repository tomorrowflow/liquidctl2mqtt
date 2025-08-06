#!/usr/bin/env python3
"""
Test script to simulate liquidctl output for development and testing purposes.
This creates sample JSON output that mimics what liquidctl would return.
"""

import json
import sys
import random
from datetime import datetime

def generate_sample_data():
    """Generate sample liquidctl sensor data"""
    
    # Sample devices with different types of sensors
    sample_devices = [
        {
            "device": "NZXT Kraken X73",
            "description": "Kraken X73",
            "temperature": {
                "cpu_core": random.uniform(25.0, 85.0),
                "liquid_inlet": random.uniform(20.0, 45.0),
                "liquid_outlet": random.uniform(22.0, 50.0)
            },
            "fan": {
                "pump_speed": random.randint(1000, 3000),
                "pump_duty": random.randint(0, 100),
                "fan1_speed": random.randint(800, 2000),
                "fan1_duty": random.randint(0, 100)
            },
            "power": {
                "consumption": random.uniform(50.0, 150.0)
            }
        },
        {
            "device": "Corsair Hydro X7",
            "description": "Hydro X7",
            "temperature": {
                "gpu_core": random.uniform(30.0, 90.0),
                "liquid_temperature": random.uniform(25.0, 40.0)
            },
            "fan": {
                "pump_rpm": random.randint(1200, 2800),
                "fan_speed": random.randint(900, 2200)
            }
        }
    ]
    
    # Return the data
    return sample_devices

def main():
    """Main function to output sample JSON"""
    data = generate_sample_data()
    
    # Print as JSON (this mimics what liquidctl --json would output)
    print(json.dumps(data, indent=2))
    
    return 0

if __name__ == "__main__":
    sys.exit(main())