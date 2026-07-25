## 🟥 <ins>Don't</ins> Run `install.sh`

> ⚠️ **Do not run `install.sh` unless you have reviewed the script and understand what it does.**

These are my personal dotfiles, and the installation script is **not intended to be a universal Arch Linux installer**.

You can copy the configurations you want and adapt them to your own system.

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Hamza-069/Arch_hyprland.git
cd Arch_hyprland
```

### 2. ⚠️ Review the configuration

Before copying anything, inspect the configuration files and adjust:

* Personal paths
* Usernames
* Hardware-specific settings
* Package dependencies
* Applications used by the configuration

### 3. 💾 Back up your existing configuration

Before replacing your current configuration, make a backup of the directories you plan to modify.

The main configurations included in this repository are:

```text
~/.config/
├── clipvault/
├── fastfetch/
├── fish/
├── hypr/
├── kitty/
├── nvim/
├── rofi/
├── swaync/
├── waybar/
├── yazi/
└── zsh/
```

For example:

```bash
cp -r ~/.config/hypr ~/.config/hypr.backup
```

Do the same for any other configuration you plan to replace.

### 4. 📂 Apply the configuration

You can copy the configurations you want individually.

For example:

```bash
cp -r Config/hypr ~/.config/
cp -r Config/waybar ~/.config/
cp -r Config/kitty ~/.config/
```

Or, if you know that the entire configuration is compatible with your system:

```bash
cp -r Config/* ~/.config/
```

> **⚠️ Do not blindly copy everything.** Some configurations may depend on packages, hardware, or paths specific to my system.

---

## 🐚 Shell Setup

This repository includes separate setup scripts for **Zsh** and **Fish**.

### Zsh

```bash
./install_zsh.sh
```

### Fish

```bash
./install_fish.sh
```

> **⚠️ Review the scripts before running them** and make sure you understand what changes they make to your system.

---

## ⚠️ Important

This repository is **not a universal Arch Linux installer**.

These dotfiles are tailored to my personal system and may contain:

* Hardware-specific settings
* Personal paths
* Package dependencies
* Wayland-specific configuration
* Hyprland-specific settings
* Scripts that expect specific applications to be installed

**Always review the configuration before applying it to your system.**

---

# 📸 Showcase

I'm still working on the README, but here are some parts of my setup.

## Waybar

<img width="1366" height="35" alt="Waybar" src="https://github.com/user-attachments/assets/9302afbe-ef15-491e-9fef-8b9db7899f3c" />

<img width="1366" height="37" alt="Waybar" src="https://github.com/user-attachments/assets/d29143b4-d543-4800-b85f-80090eeba7cb" />

<img width="1366" height="38" alt="Waybar" src="https://github.com/user-attachments/assets/78c0b252-d23e-489b-8f77-adcc378d0581" />

## 🎵 Media Player

A custom media player integrated directly into Waybar:

<img width="1280" height="269" alt="Media Player" src="https://github.com/user-attachments/assets/1b0dc46c-9c5a-4616-b715-a79003a9931c" />

> *The GIF preview may appear a little slow on GitHub.*

---

## 🚀 Fastfetch

My customized Fastfetch setup:

<img width="754" height="394" alt="Fastfetch" src="https://github.com/user-attachments/assets/0018d127-0cf4-42e8-a388-41b69302ec68" />

---

## 🔎 Rofi

My customized Rofi launcher:

<img width="605" height="369" alt="Rofi" src="https://github.com/user-attachments/assets/accb27d3-08af-434d-8334-cdc41c4347ed" />

---

## 🛠️ Customization

Feel free to take inspiration from anything in this repository.

You don't need to use the entire setup. You can copy individual configurations and adapt them to your own workflow.

For example:

```text
Config/
├── hypr/
├── waybar/
├── kitty/
├── yazi/
└── ...
```

Take what you like, change what you don't, and make it your own.

---

## 💬 Feedback

Suggestions, improvements, and ideas are welcome!

If you find something that could be improved, feel free to [open an issue](https://github.com/Hamza-069/Arch_hyprland/issues).

---

## 🙏 Credits

* **Rofi configuration:** [Aditya Shakya (adi1090x)](https://github.com/adi1090x/rofi) — thank you for the inspiration and work!


<p align="center">
  Made with ❤️ and way too much time spent tweaking configs.
</p>
