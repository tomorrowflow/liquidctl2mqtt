#!/usr/bin/env python3
"""
Setup script for liquidctl2mqtt dependencies
"""

import subprocess
import sys

def install_requirements():
    """Install required Python packages"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Successfully installed required dependencies")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False

if __name__ == "__main__":
    install_requirements()