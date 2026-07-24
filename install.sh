#!/bin/bash

#set -e  # stop on error

# ── Package Lists ────────────────────────────────────────────
# To add a package, simply append it to the relevant array below.

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
  grim slurp tesseract-data-swe rofi-emoji wtype fastfetch bat bluetui
  cmatrix calf mda.lv2 zam-plugins-lv2 x42-plugins-lv2 kio-admin kvantum-qt5 rust

)

AUR_PACKAGES=(
  ttf-jetbrains-mono-nerd clipvault tree-sitter-cli qrc waybar-git localsend
)

BOLD="\033[1m"
DIM="\033[2m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
CYAN="\033[36m"
RESET="\033[0m"

TOTAL_STEPS=5
CURRENT_STEP=0
LOG_FILE="/tmp/arch_hyprland_install.log"

echo "=== Arch Hyprland Install - $(date) ===" >"$LOG_FILE"

spinner() {
  local pid=$1
  local msg=$2
  local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
  local i=0
  while kill -0 "$pid" 2>/dev/null; do
    printf "\r  ${CYAN}${frames[$((i % ${#frames[@]}))]}${RESET} ${DIM}[$CURRENT_STEP/$TOTAL_STEPS]${RESET} $msg"
    i=$((i + 1))
    sleep 0.1
  done
  printf "\r"
}

run_step() {
  local msg=$1
  shift
  CURRENT_STEP=$((CURRENT_STEP + 1))
  "$@" > >(sed 's/\x1b\[[0-9;]*m//g' >>"$LOG_FILE") 2>&1 &
  local pid=$!
  spinner "$pid" "$msg"
  wait "$pid" 2>/dev/null
  local status=$?
  if [ "$status" -eq 0 ]; then
    printf "  ${GREEN}✓${RESET} ${DIM}[$CURRENT_STEP/$TOTAL_STEPS]${RESET} $msg\n"
  else
    printf "  ${RED}✗${RESET} ${DIM}[$CURRENT_STEP/$TOTAL_STEPS]${RESET} ${RED}$msg${RESET} ${DIM}(exit code: %d)${RESET}\n" "$status"
  fi
}

echo -e "${BOLD}${CYAN}Arch Hyprland Installer${RESET}"
echo

sudo -v

# ── Install ──────────────────────────────────────────────────

run_step "${YELLOW}Updating system${RESET}" sudo pacman -Syu --noconfirm

run_step "${YELLOW}Installing official repo packages${RESET}" sudo pacman -S --needed --noconfirm "${OFFICIAL_PACKAGES[@]}"

run_step "${YELLOW}Installing yay (AUR helper)${RESET}" bash -c '
  if ! command -v yay &>/dev/null; then
    git clone https://aur.archlinux.org/yay.git --depth=1 /tmp/yay-install
    cd /tmp/yay-install
    makepkg -si --noconfirm
    cd /
    rm -rf /tmp/yay-install
  fi
'

run_step "${YELLOW}Installing AUR packages${RESET}" yay -S --needed --noconfirm "${AUR_PACKAGES[@]}"

run_step "${YELLOW}Building spotify-adblock${RESET}" bash -c '
  cd ~
  git clone https://github.com/abba23/spotify-adblock.git
  cd spotify-adblock
  make
  cd ..
  rm -rf spotify-adblock/
'
sudo sed -i \
  -e 's/^#\?HandlePowerKey=.*/HandlePowerKey=ignore/' \
  -e 's/^#\?HandlePowerKeyLongPress=.*/HandlePowerKeyLongPress=poweroff/' \
  /etc/systemd/logind.conf

grep -q '^HandlePowerKey=' /etc/systemd/logind.conf ||
  echo 'HandlePowerKey=ignore' | sudo tee -a /etc/systemd/logind.conf >/dev/null

grep -q '^HandlePowerKeyLongPress=' /etc/systemd/logind.conf ||
  echo 'HandlePowerKeyLongPress=poweroff' | sudo tee -a /etc/systemd/logind.conf >/dev/null

echo
echo -e "Reloading Hyprland..."
hyprctl reload
