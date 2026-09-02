#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/arch_hyprland_setup.log"

RUN_PACKAGES=true
RUN_CONFIGS=true
RUN_SHELL=true
DRY_RUN=false

CONFIG_DIRS=(
  clipvault
  fastfetch
  fish
  hypr
  kitty
  mpv
  nvim
  rofi
  swaync
  waybar
  yazi
  zsh
)

log() {
  local level="$1"
  shift
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

info() { log "INFO" "$@"; }
warn() { log "WARN" "$@"; }
error() { log "ERROR" "$@"; }

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Unified setup script for Arch Hyprland dotfiles.

Options:
  --full            Run everything (packages, configs, shell) [default]
  --packages-only   Only run package installation (./install.sh)
  --configs-only    Only deploy configs from Config/
  --shell-only      Only run shell setup (zsh/fish)
  --dry-run         Show what would be done without executing
  -h, --help        Show this help

Examples:
  $0                    # Interactive full setup
  $0 --packages-only    # Install packages only
  $0 --configs-only     # Deploy configs only
  $0 --dry-run          # Preview all actions
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case $1 in
      --full)
        RUN_PACKAGES=true
        RUN_CONFIGS=true
        RUN_SHELL=true
        ;;
      --packages-only)
        RUN_PACKAGES=true
        RUN_CONFIGS=false
        RUN_SHELL=false
        ;;
      --configs-only)
        RUN_PACKAGES=false
        RUN_CONFIGS=true
        RUN_SHELL=false
        ;;
      --shell-only)
        RUN_PACKAGES=false
        RUN_CONFIGS=false
        RUN_SHELL=true
        ;;
      --dry-run)
        DRY_RUN=true
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        error "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
    shift
  done
}

confirm() {
  local prompt="$1"
  local default="${2:-N}"
  local reply

  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] Would prompt: $prompt"
    return 0
  fi

  read -rp "$prompt [y/N] " reply
  reply=${reply:-$default}
  [[ "$reply" =~ ^[Yy]$ ]]
}

run_cmd() {
  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] Would run: $*"
  else
    eval "$@"
  fi
}

run_install_sh() {
  info "Running package installation (./install.sh)..."
  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] Would execute: ./install.sh"
    return
  fi

  if [[ ! -f "$SCRIPT_DIR/install.sh" ]]; then
    error "install.sh not found in $SCRIPT_DIR"
    return 1
  fi

  cd "$SCRIPT_DIR"
  bash ./install.sh 2>&1 | tee -a "$LOG_FILE"
  info "Package installation complete"
}

backup_config() {
  local target="$1"
  local backup="${target}.backup.$(date +%s)"
  info "Backing up $target -> $backup"
  run_cmd "cp -r \"$target\" \"$backup\""
}

deploy_configs() {
  info "Deploying configs from Config/..."

  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] Available configs: ${CONFIG_DIRS[*]}"
    return
  fi

  echo
  echo "Select configs to deploy (space-separated numbers, 'all', or 'none'):"
  for i in "${!CONFIG_DIRS[@]}"; do
    printf "  [%d] %s\n" "$i" "${CONFIG_DIRS[$i]}"
  done
  echo

  read -rp "Selection: " selection
  selection=${selection:-none}

  local selected=()
  if [[ "$selection" == "all" ]]; then
    selected=("${CONFIG_DIRS[@]}")
  elif [[ "$selection" != "none" ]]; then
    for num in $selection; do
      if [[ "$num" =~ ^[0-9]+$ ]] && [[ $num -ge 0 ]] && [[ $num -lt ${#CONFIG_DIRS[@]} ]]; then
        selected+=("${CONFIG_DIRS[$num]}")
      else
        warn "Invalid selection: $num"
      fi
    done
  fi

  if [[ ${#selected[@]} -eq 0 ]]; then
    info "No configs selected, skipping deployment"
    return
  fi

  info "Deploying: ${selected[*]}"

  for name in "${selected[@]}"; do
    local src="$SCRIPT_DIR/Config/$name"
    local target="$HOME/.config/$name"

    if [[ ! -d "$src" ]]; then
      warn "Source not found: $src"
      continue
    fi

    if [[ -e "$target" ]]; then
      backup_config "$target"
    fi

    info "Copying $name -> $target"
    run_cmd "cp -r \"$src\"/. \"$target\""
  done

  info "Config deployment complete"
}

setup_shell() {
  info "Shell setup"

  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] Would prompt for shell selection (zsh/fish/both/none)"
    return
  fi

  echo
  echo "Select shell to configure:"
  echo "  1) zsh"
  echo "  2) fish"
  echo "  3) both"
  echo "  4) none"
  echo

  read -rp "Choice [1-4]: " choice
  choice=${choice:-4}

  case $choice in
    1)
      info "Setting up zsh..."
      run_cmd "bash \"$SCRIPT_DIR/install_zsh.sh\""
      ;;
    2)
      info "Setting up fish..."
      run_cmd "bash \"$SCRIPT_DIR/install_fish.sh\""
      ;;
    3)
      info "Setting up zsh..."
      run_cmd "bash \"$SCRIPT_DIR/install_zsh.sh\""
      info "Setting up fish..."
      run_cmd "bash \"$SCRIPT_DIR/install_fish.sh\""
      ;;
    4)
      info "Skipping shell setup"
      ;;
    *)
      warn "Invalid choice: $choice"
      ;;
  esac
}

reload_hyprland() {
  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] Would reload hyprland"
    return
  fi

  if command -v hyprctl &>/dev/null; then
    info "Reloading Hyprland..."
    run_cmd "hyprctl reload"
  else
    warn "hyprctl not found, skipping reload"
  fi
}

main() {
  echo "=== Arch Hyprland Setup - $(date) ===" | tee "$LOG_FILE"
  info "Starting setup (dry-run: $DRY_RUN)"

  parse_args "$@"

  if [[ "$RUN_PACKAGES" == true ]]; then
    run_install_sh
  fi

  if [[ "$RUN_CONFIGS" == true ]]; then
    deploy_configs
  fi

  if [[ "$RUN_SHELL" == true ]]; then
    setup_shell
  fi

  if [[ "$RUN_CONFIGS" == true ]] && [[ " ${CONFIG_DIRS[*]} " =~ " hypr " ]]; then
    reload_hyprland
  fi

  info "Setup complete! Log: $LOG_FILE"
}

main "$@"