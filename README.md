
##  🟥 <ins> Don't</ins> run the _.install.sh_

You can copy my config
## 🚀 Installation

### 1. Clone the repository

```
git clone https://github.com/Hamza-069/Arch_hyprland.git
cd Arch_hyprland
```

### 2. ⚠️ Review the configuration

Before copying anything, inspect the files and adjust paths, usernames, hardware-specific settings, and applications to match your system.

### 3. Apply the configuration

Copy the configuration files you need from the `Config` directory into your `~/.config` directory.

```
cp -r Config/* ~/.config/
```

**Do not blindly copy everything.** Some files may depend on packages or hardware that are specific to my setup.

----------

## 🐚 Shell Setup

This repository includes separate setup scripts for different shells:

```
./install_zsh.sh
```

or:

```
./install_fish.sh
```

Review the scripts before running them and make sure you understand what they change.

----------

## ⚠️ Important

This repository is **not a universal Arch Linux installer**.

These dotfiles are tailored to my personal system and may contain:

-   Hardware-specific settings
-   Personal paths
-   Package dependencies
-   Wayland-specific configuration
-   Hyprland-specific settings
-   Scripts that expect certain applications to be installed

**Always review the configuration before applying it to your system.**

.

Working on ReadME

Waybar:
<img width="1366" height="35" alt="2026-07-12-141936_hyprshot" src="https://github.com/user-attachments/assets/9302afbe-ef15-491e-9fef-8b9db7899f3c" />
.
<img width="1366" height="37" alt="image" src="https://github.com/user-attachments/assets/d29143b4-d543-4800-b85f-80090eeba7cb" />
 .
<img width="1366" height="38" alt="image" src="https://github.com/user-attachments/assets/78c0b252-d23e-489b-8f77-adcc378d0581" />
.


Media player (for waybar):
<img width="1280" height="269" alt="mediaplayer" src="https://github.com/user-attachments/assets/1b0dc46c-9c5a-4616-b715-a79003a9931c" />
*(It is a bit **slow** for the GIF)*	

	 
## 🛠️ Customization

Feel free to take inspiration from anything here.

You can copy individual configurations instead of using the entire setup:

```
Config/
├── hypr/
├── waybar/
├── kitty/
├── yazi/
└── ...
```

Your setup doesn't need to look exactly like mine — take what you like and make it your own.

Made with AI
## Feedback

Suggestions/improvements 
[welcome](https://github.com/Hamza-069/Arch_hyprland/issues)!
