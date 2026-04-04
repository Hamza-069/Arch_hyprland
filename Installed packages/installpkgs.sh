#!/bin/bash

sudo pacman -S --needed - < pkglist.txt
yay -S --needed - < aurlist.txt
