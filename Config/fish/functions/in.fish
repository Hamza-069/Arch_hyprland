function in --wraps=pacman --description 'install pacman packages'
    pacman -Slq | fzf --multi --ansi --border -i \
        --prompt="󰮯 Install > " \
        --preview-window="down,60%,wrap" \
        --preview 'bash -lc "pkg=\${1##*/}; pacman -Si -- \"\$pkg\"" _ {}' \
        --bind 'enter:execute(sudo pacman -S -- $(printf "%s\n" {+} | sed "s|.*/||"))+abort' $argv
end
