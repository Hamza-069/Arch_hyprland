function yun --wraps=yay\ -Qqm\ \|\ \\\n\ \ \ \ fzf\ --multi\ --ansi\ --border\ \\\n\ \ \ \ \ \ \ \ --prompt=\"\ Remove\ \>\ \"\ \\\n\ \ \ \ \ \ \ \ --preview-window=\"down,60\%,wrap\"\ \\\n\ \ \ \ \ \ \ \ --preview\ \'bash\ -lc\ \"yay\ -Qi\ --\ \\\"\\\$1\\\"\"\ _\ \{\}\'\ \\\n\ \ \ \ \ \ \ \ --bind\ \'enter:execute\(yay\ -Rns\ --\ \$\(printf\ \"\%s\\n\"\ \{+\}\)\)+abort\' --description alias\ yun=yay\ -Qqm\ \|\ \\\n\ \ \ \ fzf\ --multi\ --ansi\ --border\ \\\n\ \ \ \ \ \ \ \ --prompt=\"\ Remove\ \>\ \"\ \\\n\ \ \ \ \ \ \ \ --preview-window=\"down,60\%,wrap\"\ \\\n\ \ \ \ \ \ \ \ --preview\ \'bash\ -lc\ \"yay\ -Qi\ --\ \\\"\\\$1\\\"\"\ _\ \{\}\'\ \\\n\ \ \ \ \ \ \ \ --bind\ \'enter:execute\(yay\ -Rns\ --\ \$\(printf\ \"\%s\\n\"\ \{+\}\)\)+abort\'
    yay -Qqm | fzf --multi --ansi --border \
        --prompt=" Remove > " \
        --preview-window="down,60%,wrap" \
        --preview 'bash -lc "yay -Qi -- \"\$1\"" _ {}' \
        --bind 'enter:execute(yay -Rns -- $(printf "%s\n" {+}))+abort' $argv
end
