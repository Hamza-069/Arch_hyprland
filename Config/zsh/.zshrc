# History
HISTFILE=~/.histfile
HISTSIZE=10000
SAVEHIST=10000

setopt autocd
setopt appendhistory
setopt hist_ignore_dups
setopt hist_save_no_dups
setopt hist_ignore_all_dups
setopt hist_find_no_dups
setopt share_history
unsetopt beep

# Completion
autoload -Uz compinit
compinit

zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'
zstyle ':completion:*' group-name ''

# Plugins
source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
source /usr/share/zsh/plugins/zsh-history-substring-search/zsh-history-substring-search.zsh
source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down

# FZF
source <(fzf --zsh)
export _FZF_PREVIEW_CMD='bat --color=always --style=plain,numbers --line-range=:500 {}'
export FZF_CTRL_T_OPTS="--preview '$_FZF_PREVIEW_CMD'"


# Zoxide
eval "$(zoxide init zsh)"

# Aliases
alias ls='eza --tree --level=2 --icons --group-directories-first'
alias as='fastfetch'
alias cd='z'
alias gits='/home/ham/.config/hypr/scripts/gitsync.sh'
alias q='exit'
alias x='cmatrix -u 6'
n() {
    local file

    file=$(fd . \
        --hidden \
        --exclude .git |
        fzf \
            --ansi \
            --border \
            --height=100% \
            --layout=reverse \
            --prompt=' Open > ' \
            --preview='if [[ -d {} ]]; then eza --tree --level=2 --icons --group-directories-first {}; else bat --style=numbers --color=always --line-range=:300 {}; fi'
    )

    [[ -n "$file" ]] && nvim "$file"
}

in() {
    local packages

    packages=$(pacman -Slq | fzf \
        --multi \
        --ansi \
        --border \
        --prompt='󰮯 Install > ' \
        --preview-window='down,60%,wrap' \
        --preview='pkg=${1#*/}; pacman -Si "$pkg"'
    )

    [[ -z "$packages" ]] && return

    printf '%s\n' "$packages" |
        sed 's|.*/||' |
        xargs -r sudo pacman -S
}


# ─────────────────────────────────────────────
# Remove official Arch packages
# ─────────────────────────────────────────────

un() {
    local packages

    packages=$(pacman -Qqe | fzf \
        --multi \
        --ansi \
        --border \
        --prompt='󰮯 Remove > ' \
        --preview-window='down,60%,wrap' \
        --preview='pacman -Qi {}'
    )

    [[ -z "$packages" ]] && return

    printf '%s\n' "$packages" |
        xargs -r sudo pacman -Rns
}


# ─────────────────────────────────────────────
# Install AUR packages
# ─────────────────────────────────────────────

yin() {
    local packages

    packages=$(yay -Slq | fzf \
        --multi \
        --ansi \
        --border \
        --prompt=' Install > ' \
        --preview-window='down,60%,wrap' \
        --preview='pkg=${1#*/}; yay -Si "$pkg"'
    )

    [[ -z "$packages" ]] && return

    printf '%s\n' "$packages" |
        sed 's|.*/||' |
        xargs -r yay -S
}


# ─────────────────────────────────────────────
# Remove AUR packages
# ─────────────────────────────────────────────

yun() {
    local packages

    packages=$(yay -Qqm | fzf \
        --multi \
        --ansi \
        --border \
        --prompt=' Remove > ' \
        --preview-window='down,60%,wrap' \
        --preview='yay -Qi {}'
    )

    [[ -z "$packages" ]] && return

    printf '%s\n' "$packages" |
        xargs -r yay -Rns
}

# Load Zsh datetime module
zmodload zsh/datetime

# Store command start time
preexec() {
    cmd_start=$EPOCHREALTIME
}

# Build prompt
precmd() {
    local exit_code=$?

    # Calculate elapsed time
    local elapsed="0.00"

    if [[ -n "$cmd_start" ]]; then
        elapsed=$(awk -v start="$cmd_start" -v end="$EPOCHREALTIME" \
            'BEGIN { printf "%.2f", end - start }')
    fi

    # Shortened path
    local path="${PWD/#$HOME/~}"
    local -a parts
    local short_path=""

    if [[ "$path" == "~" ]]; then
        short_path="~"
    else
        parts=("${(@s:/:)path}")

        for part in "${parts[@]}"; do
            [[ -z "$part" ]] && continue

            if [[ "$part" == "~" ]]; then
                short_path="~"
            else
                short_path+="/${part[1]}"
            fi
        done

        short_path="${short_path%/${parts[-1][1]}}/${parts[-1]}"
    fi

    # Left side
    if (( exit_code == 0 )); then
        PROMPT="%B%F{blue}${short_path}%f%b %F{green}>%f "
    else
        PROMPT="%B%F{blue}${short_path}%f%b %B%F{red}>%f%b "
    fi

    # Right side
    RPROMPT="%B%F{blue}${elapsed}s%f%b  %B%F{red}%D{%I:%M}%f%b"
    # Reset
    cmd_start=""
}
