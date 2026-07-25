PROMPT_EOL_CHAR=""

# ── Prompt (load first for instant display) ──
zmodload zsh/datetime
autoload -Uz add-zsh-hook

cmd_start=""
PROMPT="%B%F{blue}%~%f%b %F{green}>%f "
RPROMPT="%B%F{red}%D{%I:%M}%f%b"

preexec() {
    cmd_start=$EPOCHREALTIME
    RPROMPT="%B%F{cyan}%D{%I:%M}%f%b"
}

precmd() {
    local exit_code=$?
    local elapsed=""

    if [[ -n "$cmd_start" ]]; then
        elapsed=$(awk -v start="$cmd_start" -v end="$EPOCHREALTIME" 'BEGIN {
            ms = int((end - start) * 1000)
            mins = int(ms / 60000)
            secs = int((ms % 60000) / 1000)
            msec = int(ms / 10) % 100
            if (mins > 0) printf "%d:%02d.%02d", mins, secs, msec
            else printf "%d.%02d", secs, msec
        }')
    fi

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

    if (( exit_code == 0 )); then
        PROMPT="%B%F{blue}${short_path}%f%b %F{green}>%f "
    else
        PROMPT="%B%F{blue}${short_path}%f%b %B%F{red}>%f%b "
    fi

    if [[ -n "$elapsed" ]]; then
        RPROMPT="%B%F{blue}${elapsed}%f%b  %B%F{red}%D{%I:%M}%f%b"
    else
        RPROMPT="%B%F{red}%D{%I:%M}%f%b"
    fi

    cmd_start=""
}

# ── Deferred init (heavy stuff loads once, after first prompt) ──
_deferred_init() {
    add-zsh-hook -d precmd _deferred_init

    # History
    HISTFILE=~/.histfile
    HISTSIZE=10000
    SAVEHIST=10000
    setopt autocd appendhistory share_history
    setopt hist_ignore_dups hist_save_no_dups hist_ignore_all_dups hist_find_no_dups
    unsetopt beep

    # Completion
    autoload -Uz compinit && compinit

    zstyle ':completion:*' menu yes select
    zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'
    zstyle ':completion:*' group-name ''
    zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
    zstyle ':omz: autosuggestions' strategy 'history' 'completion'
    zstyle ':completion:*' preview 'ls --color=always %1 2>/dev/null || ls %1'

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
        file=$(fd . --hidden --exclude .git |
            fzf --ansi --border --height=100% --layout=reverse \
                --prompt=' Open > ' \
                --preview='if [[ -d {} ]]; then eza --tree --level=2 --icons --group-directories-first {}; else bat --style=numbers --color=always --line-range=:300 {}; fi'
        )
        [[ -n "$file" ]] && nvim "$file"
    }

    in() {
        local packages
        packages=$(pacman -Slq | fzf \
            --multi --ansi --border \
            --prompt='󰮯 Install > ' \
            --preview-window='down,60%,wrap' \
            --preview='pacman -Si {}'
        )
        [[ -z "$packages" ]] && return
        sudo pacman -S ${(f)packages} < /dev/tty
    }

    un() {
        local packages
        packages=$(pacman -Qqe | fzf \
            --multi --ansi --border \
            --prompt='󰮯 Remove > ' \
            --preview-window='down,60%,wrap' \
            --preview='pacman -Qi {}'
        )
        [[ -z "$packages" ]] && return
        local names=(${(f)packages})
        names=(${names:#})
        sudo pacman -Rns $names
    }

    yin() {
        local packages
        packages=$(yay -Slq | fzf \
            --multi --ansi --border \
            --prompt=' Install > ' \
            --preview-window='down,60%,wrap' \
            --preview='yay -Si {}'
        )
        [[ -z "$packages" ]] && return
        yay -S ${(f)packages} < /dev/tty
    }

    yun() {
        local packages
        packages=$(yay -Qqm | fzf \
            --multi --ansi --border \
            --prompt=' Remove > ' \
            --preview-window='down,60%,wrap' \
            --preview='yay -Qi {}'
        )
        [[ -z "$packages" ]] && return
        local names=(${(f)packages})
        names=(${names:#})
        yay -Rns $names
    }
}

add-zsh-hook precmd _deferred_init
