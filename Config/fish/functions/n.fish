function n --wraps=nvim --description 'open files with nvim'
    fd . --hidden --exclude .git | \
fzf -i --ansi --border --height=100% --layout=reverse \
    --prompt=" Open > " \
    --preview="if test -d {}; exa --tree --level=2 {}; else bat --style=numbers --color=always --line-range :300 {}; end" \
    --bind "enter:become(nvim {})" $argv
end
