# hyprland_backup

sudo pacman -S fish

chsh -s /usr/bin/fish

sudo pacman -S waybar firefox kitty rofi swaync pcmanfm adw-gtk-theme nwg-look libnotify ttf-nerd-fonts-symbols-common ttf-nerd-fonts-symbols-mono ffmpeg 7zip jq poppler fd ripgrep fzf zoxide resvg imagemagick ttf-jetbrains-mono ttf-dejavu noto-fonts-emoji noto-fonts-cjk noto-fonts-extra ttf-jetbrains-mono ttf-fira-code ttf-source-code-pro

**App:** 
sudo pacman -S waybar firefox kitty rofi swaync pcmanfm nwg-look pavucontrol blueman blueman-manager


**Fonts:**
sudo pacman -S ttf-nerd-fonts-symbols-common ttf-nerd-fonts-symbols-mono ttf-jetbrains-mono ttf-dejavu noto-fonts-emoji noto-fonts-cjk noto-fonts-extra ttf-jetbrains-mono ttf-fira-code ttf-source-code-pro


**Others:**
sudo pacman -S adw-gtk-theme ffmpeg 7zip jq poppler fd ripgrep fzf zoxide resvg imagemagick 



sudo pacman -S --needed git base-devel
git clone https://aur.archlinux.org/yay.git --depth=1
cd yay
makepkg -si

yay -S vscodium-bin vscodium-bin-marketplace nerd-fonts-jetbrains-mono nerd-fonts-fira-code nerd-fonts-hack
