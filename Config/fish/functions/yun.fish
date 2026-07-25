function yun --wraps=yay --description 'uninstall AUR packages'
    yay -Qqm | fzf -i --multi --ansi --border \
        --prompt=" Remove > " \
        --preview-window="down,60%,wrap" \
        --preview 'bash -lc "yay -Qi -- \"\$1\"" _ {}' \
        --bind 'enter:execute(yay -Rns -- $(printf "%s\n" {+}))+abort' $argv
end
