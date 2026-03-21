# hyprland_backup

sudo pacman -S fish waybar firefox kitty rofi swaync adw-gtk-theme nwg-look libnotify ttf-nerd-fonts-symbols-common ttf-nerd-fonts-symbols-mono ffmpeg 7zip jq poppler fd ripgrep fzf zoxide resvg imagemagick

sudo pacman -S --needed git base-devel
git clone https://aur.archlinux.org/yay.git --depth=1
cd yay
makepkg -si

yay -S vscodium-bin vscodium-bin-marketplace 
