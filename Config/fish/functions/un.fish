function un --wraps=pacman\ -Qq\ \|\ \\\nfzf\ --multi\ --ansi\ --border\ \\\n\ \ \ \ --preview-window=\"down,60\%,wrap\"\ \\\n\ \ \ \ --preview\ \'bash\ -lc\ \"pacman\ -Qi\ --\ \\\"\\\$1\\\"\"\ _\ \{\}\'\ \\\n\ \ \ \ --bind\ \'enter:execute\(sudo\ pacman\ -Rns\ --\ \$\(printf\ \"\%s\\n\"\ \{+\}\)\)+abort\' --wraps=pacman\ -Qq\ \|\ \\\n\ \ \ \ fzf\ --multi\ --ansi\ --border\ \\\n\ \ \ \ \ \ \ \ --prompt=\"󰮯\ Remove\ \>\ \"\ \\\n\ \ \ \ \ \ \ \ --preview-window=\"down,60\%,wrap\"\ \\\n\ \ \ \ \ \ \ \ --preview\ \'bash\ -lc\ \"pacman\ -Qi\ --\ \\\"\\\$1\\\"\"\ _\ \{\}\'\ \\\n\ \ \ \ \ \ \ \ --bind\ \'enter:execute\(sudo\ pacman\ -Rns\ --\ \$\(printf\ \"\%s\\n\"\ \{+\}\)\)+abort\' --description alias\ un=pacman\ -Qqe\ \|\ \\\n\ \ \ \ fzf\ --multi\ --ansi\ --border\ \\\n\ \ \ \ \ \ \ \ --prompt=\"󰮯\ Remove\ \>\ \"\ \\\n\ \ \ \ \ \ \ \ --preview-window=\"down,60\%,wrap\"\ \\\n\ \ \ \ \ \ \ \ --preview\ \'bash\ -lc\ \"pacman\ -Qi\ --\ \\\"\\\$1\\\"\"\ _\ \{\}\'\ \\\n\ \ \ \ \ \ \ \ --bind\ \'enter:execute\(sudo\ pacman\ -Rns\ --\ \$\(printf\ \"\%s\\n\"\ \{+\}\)\)+abort\'
    pacman -Qqe | fzf --multi --ansi --border \
        --prompt="󰮯 Remove > " \
        --preview-window="down,60%,wrap" \
        --preview 'bash -lc "pacman -Qi -- \"\$1\"" _ {}' \
        --bind 'enter:execute(sudo pacman -Rns -- $(printf "%s\n" {+}))+abort' $argv
end
