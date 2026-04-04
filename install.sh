#!/bin/bash

set -e  # stop on error

echo "Installing official repo packages..."

sudo pacman -S --needed gnome-keyring rofi swaync nwg-look pavucontrol blueman zed \
  ttf-nerd-fonts-symbols-common ttf-nerd-fonts-symbols-mono \
  ttf-jetbrains-mono ttf-dejavu noto-fonts-emoji noto-fonts-cjk noto-fonts-extra \
  ttf-fira-code ttf-sourcecodepro-nerd \
  adw-gtk-theme ffmpeg 7zip jq poppler fd ripgrep fzf zoxide resvg imagemagick \
  breeze breeze-icons qt6ct qt5ct kvantum kvantum-qt5 \
  git base-devel

echo "Installing yay (AUR helper)..."

if ! command -v yay &> /dev/null; then
git clone https://aur.archlinux.org/yay.git --depth=1
cd yay
makepkg -si --noconfirm
cd ..
rm -rf yay
fi

echo "Installing AUR packages..."

yay -S --needed nerd-fonts-jetbrains-mono nerd-fonts-fira-code nerd-fonts-hack ttf-jetbrains-mono-nerd wlogout

echo "Done!"
