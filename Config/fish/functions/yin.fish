function yin --wraps=yay\ -Slq\ \|\ \\\n\ \ \ \ fzf\ --multi\ --ansi\ --border\ \\\n\ \ \ \ \ \ \ \ --prompt=\"\ Install\ \>\ \"\ \\\n\ \ \ \ \ \ \ \ --preview-window=\"down,60\%,wrap\"\ \\\n\ \ \ \ \ \ \ \ --preview\ \'bash\ -lc\ \"pkg=\\\$\{1#\#\*/\}\;\ yay\ -Si\ --\ \\\"\\\$pkg\\\"\"\ _\ \{\}\'\ \\\n\ \ \ \ \ \ \ \ --bind\ \'enter:execute\(yay\ -S\ --\ \$\(printf\ \"\%s\\n\"\ \{+\}\ \|\ sed\ \"s\|.\*/\|\|\"\)\)+abort\' --description alias\ yin=yay\ -Slq\ \|\ \\\n\ \ \ \ fzf\ --multi\ --ansi\ --border\ \\\n\ \ \ \ \ \ \ \ --prompt=\"\ Install\ \>\ \"\ \\\n\ \ \ \ \ \ \ \ --preview-window=\"down,60\%,wrap\"\ \\\n\ \ \ \ \ \ \ \ --preview\ \'bash\ -lc\ \"pkg=\\\$\{1#\#\*/\}\;\ yay\ -Si\ --\ \\\"\\\$pkg\\\"\"\ _\ \{\}\'\ \\\n\ \ \ \ \ \ \ \ --bind\ \'enter:execute\(yay\ -S\ --\ \$\(printf\ \"\%s\\n\"\ \{+\}\ \|\ sed\ \"s\|.\*/\|\|\"\)\)+abort\'
    yay -Slq | \
    fzf --multi --ansi --border \
        --prompt=" Install > " \
        --preview-window="down,60%,wrap" \
        --preview 'bash -lc "pkg=\${1##*/}; yay -Si -- \"\$pkg\"" _ {}' \
        --bind 'enter:execute(yay -S -- $(printf "%s\n" {+} | sed "s|.*/||"))+abort' $argv
end
