#!/bin/bash

if pacman -Q zsh &>/dev/null; then
  echo "Zsh is already installed"
else
  sudo pacman -S zsh zsh-autosuggestions zsh-syntax-highlighting zsh-completions zsh-history-substring-search --noconfirm --needed
fi

echo 'source "$HOME/.config/zsh/.zshrc"' >~/.zshrc

mv ~/Downloads/arch_hyprland/Config/zsh/ ~/.config/zsh/.zshrc

chsh -s /bin/zsh
echo "Reboot."
