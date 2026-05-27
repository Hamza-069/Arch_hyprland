function in --wraps=pacman\ -Slq\ \|\ \\\n\ \ \ \ fzf\ --multi\ --ansi\ --border\ \\\n\ \ \ \ \ \ \ \ --prompt=\"󰮯\ Install\ \>\ \"\ \\\n\ \ \ \ \ \ \ \ --preview-window=\"down,60\%,wrap\"\ \\\n\ \ \ \ \ \ \ \ --preview\ \'bash\ -lc\ \"pkg=\\\$\{1#\#\*/\}\;\ pacman\ -Si\ --\ \\\"\\\$pkg\\\"\"\ _\ \{\}\'\ \\\n\ \ \ \ \ \ \ \ --bind\ \'enter:execute\(sudo\ pacman\ -S\ --\ \$\(printf\ \"\%s\\n\"\ \{+\}\ \|\ sed\ \"s\|.\*/\|\|\"\)\)+abort\' --description alias\ in=pacman\ -Slq\ \|\ \\\n\ \ \ \ fzf\ --multi\ --ansi\ --border\ \\\n\ \ \ \ \ \ \ \ --prompt=\"󰮯\ Install\ \>\ \"\ \\\n\ \ \ \ \ \ \ \ --preview-window=\"down,60\%,wrap\"\ \\\n\ \ \ \ \ \ \ \ --preview\ \'bash\ -lc\ \"pkg=\\\$\{1#\#\*/\}\;\ pacman\ -Si\ --\ \\\"\\\$pkg\\\"\"\ _\ \{\}\'\ \\\n\ \ \ \ \ \ \ \ --bind\ \'enter:execute\(sudo\ pacman\ -S\ --\ \$\(printf\ \"\%s\\n\"\ \{+\}\ \|\ sed\ \"s\|.\*/\|\|\"\)\)+abort\'
    pacman -Slq | \
    fzf --multi --ansi --border \
        --prompt="󰮯 Install > " \
        --preview-window="down,60%,wrap" \
        --preview 'bash -lc "pkg=\${1##*/}; pacman -Si -- \"\$pkg\"" _ {}' \
        --bind 'enter:execute(sudo pacman -S -- $(printf "%s\n" {+} | sed "s|.*/||"))+abort' $argv
end
