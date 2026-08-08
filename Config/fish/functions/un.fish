function un --wraps=pacman --description 'uninstall pacman packages'
    pacman -Qq | fzf -i --multi --ansi --border \
        --prompt="󰮯 Remove > " \
        --preview-window="down,60%,wrap" \
        --preview 'bash -lc "pacman -Qi -- \"\$1\"" _ {}' \
        --bind 'enter:execute(sudo pacman -Rns -- $(printf "%s\n" {+}))+abort' $argv
end
