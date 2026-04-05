#!/bin/bash

set -e  # stop on error

echo "Installing official repo packages..."

sudo pacman -S --needed gnome-keyring rofi swaync nwg-look pavucontrol blueman zed \
  ttf-nerd-fonts-symbols-common ttf-nerd-fonts-symbols-mono \
  ttf-jetbrains-mono ttf-dejavu noto-fonts-emoji noto-fonts-cjk noto-fonts-extra \
  ttf-fira-code ttf-sourcecodepro-nerd \
  adw-gtk-theme ffmpeg 7zip jq poppler fd ripgrep fzf zoxide resvg imagemagick \
  breeze breeze-icons qt6ct qt5ct kvantum kvantum-qt5 \
  git base-devel hyprpaper hyprlock hypridle hyprpolkitagent python-pip polkit-kde-agent \
  spotify-launcher python pyright lua-language-server

echo "Installing yay (AUR helper)..."

if ! command -v yay &> /dev/null; then
git clone https://aur.archlinux.org/yay.git --depth=1
cd yay
makepkg -si --noconfirm
cd ..
rm -rf yay
fi

echo "Installing AUR packages..."

yay -S --needed nerd-fonts-jetbrains-mono nerd-fonts-fira-code nerd-fonts-hack ttf-jetbrains-mono-nerd wlogout clipvault


./install_fish.sh
echo "Done Installing!"

cp -r ~/.config ~/Config-backup
echo "Saved a Config-backup"


backup_dir=$(find ~ -type d -name "Arch_hyprland_backup" | head -n 1)

if [[ -z "$backup_dir" ]]; then
    echo "Backup folder not found!"
    exit 1
fi

mv "$backup_dir/Config/"* ~/.config/

read -p "Reboot now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo reboot
fi
