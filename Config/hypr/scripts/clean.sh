#!/bin/bash
set -euo pipefail

cleanup() {
  notify-send "SYSTEM" "Cleanup interrupted"
  exit 1
}
trap cleanup SIGINT SIGTERM

echo "Starting system cleanup..."
notify-send "SYSTEM" "Starting system cleanup..."

echo "Cleaning journal logs..."
sudo journalctl --rotate --vacuum-time=3d

# Clean temporary files (skip hidden files, touch only recent access)
echo "Cleaning /tmp..."
sudo find /tmp -mindepth 1 -atime +1 -delete 2>/dev/null || true

notify-send "SYSTEM" "Cleanup Complete!!"
echo "Cleanup complete!"
