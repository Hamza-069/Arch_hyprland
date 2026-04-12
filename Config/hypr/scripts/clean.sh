#!/bin/bash

echo "Starting system cleanup..."
notify-send "SYSTEM" "Starting system cleanup..."

echo "Cleaning journal logs..."
notify-send "SYSTEM" "Cleaning journal logs"
sudo journalctl --vacuum-time=3d

# Clean temporary files
echo "Cleaning /tmp..."
notify-send "SYSTEM" "Cleaning /tmp"
sudo rm -rf /tmp/*

notify-send "SYSTEM" "Cleanup Complete!!"
echo "Cleanup complete!"
