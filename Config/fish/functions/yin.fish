function yin --wraps=yay --description 'install AUR packages'
    yay -Slq | \
    fzf -i --multi --ansi --border \
        --prompt=" Install > " \
        --preview-window="down,60%,wrap" \
        --preview 'bash -lc "pkg=\${1##*/}; yay -Si -- \"\$pkg\"" _ {}' \
        --bind 'enter:execute(yay -S -- $(printf "%s\n" {+} | sed "s|.*/||"))+abort' $argv
end
