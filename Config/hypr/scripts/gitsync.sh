#!/usr/bin/env bash

set -euo pipefail

REPO="$HOME/Downloads/arch_hyprland"
CONFIG="$REPO/Config"

if [ ! -d "$REPO/.git" ]; then
  echo "Error: $REPO is not a git repository."
  exit 1
fi

rm -rf ~/Downloads/arch_hyprland/Config/*

cp -a \
  "$HOME/.config/clipvault" \
  "$HOME/.config/fastfetch" \
  "$HOME/.config/fish" \
  "$HOME/.config/hypr" \
  "$HOME/.config/kitty" \
  "$HOME/.config/nvim" \
  "$HOME/.config/rofi" \
  "$HOME/.config/swaync" \
  "$HOME/.config/waybar" \
  "$HOME/.config/yazi" \
  "$HOME/.config/zsh/" \
  "$HOME/.config/mpv" \
  "$CONFIG"

cd "$REPO"

echo
echo "=== Git Status ==="
git status
echo

read -rp "Commit and push these changes? [y/N] " answer

if [[ "$answer" =~ ^[Yy]$ ]]; then
  if [ -n "$(git status --porcelain)" ]; then
    git add .
    read -rp "Write a custom commit message? [y/N] " custom_msg
    if [[ "$custom_msg" =~ ^[Yy]$ ]]; then
      read -rp "Enter commit message: " msg
      git commit -m "$msg"
    else
      git commit -m "Update dotfiles: $(date '+%Y-%m-%d %I:%M')"
    fi
    echo
    echo "==================== git pull ===================="
    git pull --rebase
    echo
    echo "==================== git push ===================="

    git push
  else
    echo "No changes to commit."
  fi
else
  echo "exited."
fi
