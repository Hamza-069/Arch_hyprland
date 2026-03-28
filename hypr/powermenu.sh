#!/bin/bash
# powermenu.sh - simple power menu

options="Shutdown\nReboot\nSuspend\nLogout"

choice=$(echo -e "$options" | wofi --dmenu --prompt "Power Menu")

case $choice in
    "Shutdown")
        systemctl poweroff
        ;;
    "Reboot")
        systemctl reboot
        ;;
    "Suspend")
        loginctl suspend
        ;;
    "Logout")
        hyprctl dispatch exit
        ;;
esac
