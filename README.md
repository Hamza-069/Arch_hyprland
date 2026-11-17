# Arch Hyprland Dotfiles

My personal [Arch Linux](https://archlinux.org/) + [Hyprland](https://hypr.land/) setup, including Hyprland, Waybar, Rofi, Kitty, SwayNC, Hyprlock, Fastfetch, Yazi, Neovim, mpv, and Fish/Zsh.

> **⚠️ This is not a universal Arch Linux installer.**
>
> These dotfiles are tailored to my hardware and workflow. They may contain personal paths, hardware-specific settings, and dependencies you don't have.
>
> **Review everything before running it.** `install.sh` installs packages, edits `/etc/systemd/logind.conf`, changes default applications, and reloads Hyprland. `setup.sh` only deploys configs, but it still overwrites files in `~/.config/`.

## 📑 Table of Contents

- [Installation](#-installation)
- [Shell Setup](#-shell-setup)
- [Fonts](#-fonts-optional)
- [Optional Extras](#️-optional-extras)
- [Showcase](#-showcase)
- [Keybindings](#️-keybindings)
- [Customization](#️-customization)
- [Feedback](#-feedback)
- [Credits](#-credits)

---

## 🚀 Installation

The repository has two main scripts:

- **`install.sh`** — installs packages and makes system-wide changes.
- **`setup.sh`** — deploys the configs to `~/.config/` with automatic backups.

For a full setup, follow the steps below in order.

### 1. Clone the repository

```bash
git clone https://github.com/Hamza-069/Arch_hyprland.git
cd Arch_hyprland
```

### 2. Review the configuration

Before applying anything, inspect the scripts and configs and adjust:

- Personal paths
- Usernames
- Hardware-specific settings
- Package dependencies
- Applications used by the configuration

### 3. Install packages (optional)

```bash
./install.sh
```

This script:

- Updates the system with `pacman -Syu`
- Installs the official repo packages listed in the script
- Installs `yay` if needed, then installs the AUR packages
- Builds and installs `spotify-adblock`
- Configures power-key handling in `/etc/systemd/logind.conf`
- Sets default applications for text, images, and video
- Reloads Hyprland

> **⚠️ Only run this after reading it.** It uses `sudo` and makes system-wide changes. The full package list is in [`install.sh`](install.sh).

### 4. Deploy the configs (recommended)

```bash
./setup.sh --dry-run   # preview what will be copied
./setup.sh             # deploy
```

`setup.sh` copies each directory from `Config/` into `~/.config/`, backs up any existing config to `~/.config-backup/<timestamp>/`, and reloads Hyprland when `hyprctl` is available. A log is written to `/tmp/arch_hyprland_setup.log`.

Supported options:

```text
--dry-run    Show what would be done without copying anything
-h, --help   Show help
```

### Manual deployment

If you prefer to copy things yourself, back up what you are about to replace:

```bash
cp -r ~/.config/waybar ~/.config/waybar.backup
```

Then copy the configs you want:

```bash
cp -r Config/hypr ~/.config/
cp -r Config/waybar ~/.config/
cp -r Config/kitty ~/.config/
```

Or, if you know the entire configuration is compatible with your system:

```bash
cp -r Config/* ~/.config/
```

The included configs are:

```text
Config/
├── clipvault/
├── fastfetch/
├── fish/
├── hypr/
├── kitty/
├── mpv/
├── nvim/
├── rofi/
├── swaync/
├── waybar/
├── yazi/
└── zsh/
```

To restart Waybar, Hyprpaper, and Hypridle after copying:

```bash
./Config/hypr/scripts/reload.sh
```

> **⚠️ Do not blindly copy everything.** Some configurations depend on packages, hardware, or paths specific to my system.

---

## 🐚 Shell Setup

The shell configs live in `Config/zsh/` and `Config/fish/` and are deployed by `setup.sh`.

### Zsh

```bash
./install_zsh.sh
```

This installs Zsh with autosuggestions, syntax highlighting, completions, and history substring search, points `~/.zshrc` at `~/.config/zsh/.zshrc`, and sets Zsh as your login shell.

> The script assumes the repository is cloned at `~/Downloads/arch_hyprland`. Adjust the path if you cloned it somewhere else.

### Fish

```bash
./install_fish.sh
```

This installs Fish and sets it as your login shell. The Fish configuration is in `Config/fish/` and is deployed by `setup.sh`.

> Both scripts run `chsh` and change your login shell. Review them first, and reboot or log out and back in afterwards.

---

## 🔤 Fonts (optional)

`install.sh` installs the Nerd Fonts used by the configs. My Hyprlock setup also uses Apple's SF Pro, which can be installed separately:

```bash
./install_apple-font.sh
```

This downloads SF Pro from Apple and installs it to `~/.local/share/fonts`. It requires `7z` (`sudo pacman -S p7zip`).

---

## 🗂️ Optional Extras

The `etc/` directory contains files that are **not** deployed by `setup.sh`:

- `etc/environment` — Qt theme environment variable (`QT_QPA_PLATFORMTHEME=qt6ct`); copy it to `/etc/environment`
- `etc/GIMP/` — GIMP 3.0/3.2 profiles; copy them into `~/.config/GIMP/`
- `etc/Audio Presets/` — EasyEffects presets
- `etc/sweather.py` — weather CLI used by the Waybar weather module; place it in your `PATH` (for example `~/.local/bin`)
- `etc/lyricsync.py` — terminal lyrics synchronization tool
- `etc/.peaclock/config` — peaclock configuration; copy it to `~/.peaclock/config`
- `etc/Github_setup.txt` — my personal SSH/Git setup notes

> The Waybar weather module uses a hardcoded location in `Config/waybar/weather.sh`. Change it to your own city.

---

## 📸 Showcase

Here are some parts of my setup.

### Waybar

<img width="1366" height="35" alt="Waybar" src="https://github.com/user-attachments/assets/9302afbe-ef15-491e-9fef-8b9db7899f3c" />

<img width="1366" height="37" alt="Waybar" src="https://github.com/user-attachments/assets/d29143b4-d543-4800-b85f-80090eeba7cb" />

<img width="1366" height="38" alt="Waybar" src="https://github.com/user-attachments/assets/78c0b252-d23e-489b-8f77-adcc378d0581" />

### 🎵 Media Player

A custom media player integrated directly into Waybar:

<img width="1280" height="269" alt="Media Player" src="https://github.com/user-attachments/assets/1b0dc46c-9c5a-4616-b715-a79003a9931c" />

> *The GIF preview may appear a little slow on GitHub.*

### 🚀 Fastfetch

My customized Fastfetch setup:

<img width="754" height="394" alt="Fastfetch" src="https://github.com/user-attachments/assets/0018d127-0cf4-42e8-a388-41b69302ec68" />

### 🔎 Rofi

My customized Rofi launcher:

<img width="605" height="369" alt="Rofi" src="https://github.com/user-attachments/assets/accb27d3-08af-434d-8334-cdc41c4347ed" />

### Powermenu (Rofi)

<img width="978" height="334" alt="Powermenu" src="https://github.com/user-attachments/assets/39d9b660-76d1-46dc-924e-d5ea36e70dc1" />

### Hyprlock

My customized Hyprlock:

<img width="598" height="400" alt="Hyprlock" src="https://github.com/user-attachments/assets/f0103005-1dd1-4aa0-83b7-d81582483f00" />

### Theme Selector

<img width="612" height="369" alt="Theme Selector" src="https://github.com/user-attachments/assets/d5cc78e6-a8fc-4824-b8ee-546a182d09c5" />

> ⚠️ Check the script before using it:
>
> ```bash
> ./Config/hypr/scripts/theme-selector.sh
> ```

---

## ⌨️ Keybindings

Here are some of the main keyboard shortcuts in my Hyprland setup:

| Shortcut | Action |
| --- | --- |
| `SUPER + Q` | Open terminal (Kitty) |
| `SUPER + D` | Open file manager (Dolphin) |
| `SUPER + E` | Open Yazi in Kitty |
| `SUPER + X` | Open Neovim in Kitty |
| `SUPER + B` | Open browser (Firefox) |
| `SUPER + R` | Open application launcher (Rofi) |
| `SUPER + C` | Open calculator (Rofi) |
| `SUPER + V` | Open clipboard history |
| `SUPER + W` | Close active window |
| `SUPER + F` | Toggle floating and center the window |
| `SUPER + P` | Pin a floating window |
| `Fullscreen` key | Toggle fullscreen |
| `SUPER + M` | Open Spotify |
| `SUPER + Space` | Play / pause Spotify |
| `SUPER + L` | Lock the screen |
| `SUPER + SHIFT + M` | Exit Hyprland |
| `SUPER + 1–9 / 0` | Switch workspace |
| `SUPER + SHIFT + 1–9 / 0` | Move window to workspace |
| `SUPER + Arrow Keys` | Move focus |
| `SUPER + SHIFT + Arrow Keys` | Move window |
| `SUPER + Mouse Drag` | Move window |
| `SUPER + Right Mouse Drag` | Resize window |
| `SUPER + S` | Toggle scratchpad |
| `SUPER + SHIFT + S` | Move window to scratchpad |
| `SUPER + T` | Open theme selector |
| `SUPER + SHIFT + T` | Open wallpaper selector |
| `SUPER + SHIFT + R` | Reload Waybar, Hyprpaper, and Hypridle |
| `SUPER + J` | Toggle split (dwindle layout) |
| `SUPER + SHIFT + J` | Rotate split (dwindle layout) |

> **Note:** Shortcuts may change as the configuration evolves. Check [`Config/hypr/mods/binds.lua`](https://github.com/Hamza-069/Arch_hyprland/blob/main/Config/hypr/mods/binds.lua) for the latest keybindings.

---

## 🛠️ Customization

Feel free to take inspiration from anything in this repository. You don't need to use the entire setup — copy individual configurations and adapt them to your own workflow.

```text
Config/
├── clipvault/
├── fastfetch/
├── fish/
├── hypr/
├── kitty/
├── mpv/
├── nvim/
├── rofi/
├── swaync/
├── waybar/
├── yazi/
└── zsh/
```

Take what you like, change what you don't, and make it your own.

---

## 💬 Feedback

Suggestions, improvements, and ideas are welcome!

If you find something that could be improved, feel free to [open an issue](https://github.com/Hamza-069/Arch_hyprland/issues).

---

## 🙏 Credits

- **Rofi configuration:** [Aditya Shakya (adi1090x)](https://github.com/adi1090x/rofi) — thank you for the inspiration and work!

<p align="center">
  Made with ❤️ and way too much time spent tweaking configs.
</p>
