#!/bin/bash
set -euo pipefail

# Package Lists
OFFICIAL_PACKAGES=(
  gnome-keyring rofi swaync nwg-look pavucontrol blueman
  ttf-nerd-fonts-symbols-common ttf-nerd-fonts-symbols-mono
  ttf-jetbrains-mono ttf-dejavu noto-fonts-emoji noto-fonts-cjk noto-fonts-extra
  ttf-fira-code ttf-sourcecodepro-nerd adw-gtk-theme ffmpeg 7zip jq poppler
  fd ripgrep fzf zoxide resvg imagemagick breeze breeze-icons qt6ct
  brightnessctl easyeffects git base-devel hyprpaper hyprlock hypridle
  hyprpolkitagent python-pip polkit-kde-agent spotify-launcher python
  pyright lua-language-server ncdu impala gvfs gvfs-mtp gvfs-gphoto2
  gvfs-smb hyprshot hyprpicker neovim lsp-plugins lazygit luarocks lua51
  plasma-workspace kde-cli-tools btop eza imv tesseract tesseract-data-eng
  grim slurp rofi-emoji wtype fastfetch bat bluetui
  cmatrix calf mda.lv2 zam-plugins-lv2 x42-plugins-lv2 kio-admin kvantum-qt5 rust
  kcolorchooser github-cli yazi mpv gimp
)

AUR_PACKAGES=(
  ttf-jetbrains-mono-nerd clipvault tree-sitter-cli qrc waybar-git localsend-bin
  rofi-calc
)

LOG_FILE="/tmp/arch_hyprland_install.log"
echo "=== Arch Hyprland Install - $(date) ===" >"$LOG_FILE"

echo "Arch Hyprland Installer"
echo

sudo -v

# System update
echo "Updating system..."
sudo pacman -Syu --noconfirm 2>&1 | tee -a "$LOG_FILE"

# Official packages
echo "Installing official repo packages..."
sudo pacman -S --needed --noconfirm "${OFFICIAL_PACKAGES[@]}" 2>&1 | tee -a "$LOG_FILE"

# yay (AUR helper)
if ! command -v yay &>/dev/null; then
  echo "Installing yay..."
  git clone https://aur.archlinux.org/yay.git --depth=1 /tmp/yay-install
  cd /tmp/yay-install
  makepkg -si --noconfirm 2>&1 | tee -a "$LOG_FILE"
  cd /
  rm -rf /tmp/yay-install
fi

# AUR packages
echo "Installing AUR packages..."
yay -S --needed --noconfirm "${AUR_PACKAGES[@]}" 2>&1 | tee -a "$LOG_FILE"

# spotify-adblock
echo "Building spotify-adblock..."
cd ~
git clone https://github.com/abba23/spotify-adblock.git
cd spotify-adblock
make 2>&1 | tee -a "$LOG_FILE"
sudo make install 2>&1 | tee -a "$LOG_FILE"
cd ..
rm -rf spotify-adblock/

# logind.conf - power key handling
echo "Configuring power key handling..."
sudo tee /etc/systemd/logind.conf.d/power-key.conf >/dev/null <<'CONF'
[Login]
HandlePowerKey=ignore
HandlePowerKeyLongPress=poweroff
CONF

# Default applications
echo "Setting default applications..."

# Text/Code -> nvim
for mime in text/plain text/markdown text/x-c text/x-c++src text/x-python text/x-shellscript text/x-lua text/css text/html application/json application/xml; do
  xdg-mime default nvim.desktop "$mime"
done

# Images -> imv
for mime in image/jpeg image/png image/gif image/webp; do
  xdg-mime default imv.desktop "$mime"
done

# Video -> mpv
for mime in video/mp4 video/x-matroska video/webm; do
  xdg-mime default mpv.desktop "$mime"
done

# KDE terminal
kwriteconfig6 --file kdeglobals --group General --key TerminalApplication kitty
XDG_MENU_PREFIX=plasma- kbuildsycoca6

echo "Reloading Hyprland..."
hyprctl reload
