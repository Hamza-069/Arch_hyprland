#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/arch_hyprland_setup.log"

DRY_RUN=false
BACKUP_DIR="$HOME/.config-backup/$(date +%Y%m%d-%H%M%S)"

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

Deploy Hyprland dotfiles configs to ~/.config/

Options:
  --dry-run         Show what would be done without executing
  -h, --help        Show this help

Examples:
  $0                # Deploy all configs
  $0 --dry-run      # Preview what would be deployed
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case $1 in
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

run_cmd() {
  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] Would run: $*"
  else
    eval "$@"
  fi
}

backup_config() {
  local target="$1"
  local name="$(basename "$target")"
  local backup_target="$BACKUP_DIR/$name"

  mkdir -p "$BACKUP_DIR"
  info "Backing up $target -> $backup_target"
  run_cmd "cp -r \"$target\" \"$backup_target\""
}

deploy_configs() {
  info "Deploying configs from Config/..."

  if [[ "$DRY_RUN" == true ]]; then
    info "[DRY-RUN] Would deploy: ${CONFIG_DIRS[*]}"
    return
  fi

  info "Deploying all configs: ${CONFIG_DIRS[*]}"

  for name in "${CONFIG_DIRS[@]}"; do
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
  info "Starting config deployment (dry-run: $DRY_RUN)"

  deploy_configs

  if [[ " ${CONFIG_DIRS[*]} " =~ " hypr " ]]; then
    reload_hyprland
  fi

  info "Setup complete! Log: $LOG_FILE"
}

main "$@"