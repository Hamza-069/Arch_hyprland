#!/bin/bash
if pacman -Q fish &>/dev/null; then
    echo "Fish is already installed"
else
    sudo pacman -S fish
fi

chsh -s /usr/bin/fish
