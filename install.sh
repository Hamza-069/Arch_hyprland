#!/bin/bash

#set -e  # stop on error

sudo pacman -Syu
echo
echo "Installing official repo packages..."
echo
sudo pacman -S --needed gnome-keyring rofi swaync nwg-look pavucontrol blueman zed \
  ttf-nerd-fonts-symbols-common ttf-nerd-fonts-symbols-mono \
  ttf-jetbrains-mono ttf-dejavu noto-fonts-emoji noto-fonts-cjk noto-fonts-extra \
  ttf-fira-code ttf-sourcecodepro-nerd \
  adw-gtk-theme ffmpeg 7zip jq poppler fd ripgrep fzf zoxide resvg imagemagick \
  breeze breeze-icons qt6ct brightnessctl easyeffects \
  git base-devel hyprpaper hyprlock hypridle hyprpolkitagent python-pip polkit-kde-agent \
  spotify-launcher python pyright lua-language-server ncdu impala gvfs gvfs-mtp gvfs-gphoto2 gvfs-smb hyprshot hyprpicker neovim \
  lsp-plugins lazygit luarocks lua51 plasma-workspace kde-cli-tools btop

echo
echo "Installing yay (AUR helper)..."
echo
if ! command -v yay &>/dev/null; then
  git clone https://aur.archlinux.org/yay.git --depth=1
  cd yay
  makepkg -si --noconfirm
  cd ..
  rm -rf yay
fi
echo
echo "Installing AUR packages..."
echo
yay -S --needed --noconfirm sddm-silent-theme ttf-jetbrains-mono-nerd wlogout clipvault tree-sitter-cli

echo "Running fish install..."
echo
find . -name "install_fish.sh" -execdir bash {} \;
echo
echo "Done Installing!"
echo
echo "Changing dotfiles"
echo

cp -r ~/.config ~/Config-backup
echo "Saved a Config-backup"
echo

backup_dir=$(find /home -type d -name "Arch_hyprland_backup" | head -n 1)

if [[ -z "$backup_dir" ]]; then
  echo "Backup folder not found!"
fi

echo
echo "Changing dotfiles"
echo

mv "$backup_dir/Config/"* ~/.config/

echo "reloading hyprland"
hyprctl reload
echo "reloading hyprland"
hyprctl reload

kbuildsycoca6

read -p "Reboot now? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  sudo reboot
fi
