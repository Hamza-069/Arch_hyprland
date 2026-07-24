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



# Prompt
setopt prompt_subst

precmd() {
    if [[ $? -eq 0 ]]; then
        PROMPT='%B%F{blue}%~%f%b %F{green}>%f '
    else
        PROMPT='%B%F{blue}%~%f%b %B%F{red}>%f%b '
    fi
}
