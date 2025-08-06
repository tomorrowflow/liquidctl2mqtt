#!/bin/bash
# Setup script for liquidctl2mqtt cronjob

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set up the crontab entry
echo "Setting up liquidctl2mqtt cronjob to run every minute..."

# Add to crontab using crontab -l and pipe to crontab
(crontab -l 2>/dev/null; echo "* * * * * $SCRIPT_DIR/liquidctl_mqtt_wrapper.py") | crontab -

echo "Cronjob setup complete!"
echo "To verify: crontab -l"
echo "To remove: crontab -l | grep -v 'liquidctl_mqtt_wrapper.py' | crontab -"