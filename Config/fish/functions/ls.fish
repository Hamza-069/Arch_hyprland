function ls --wraps='exa -tree --level=2 --icons-s' --wraps='exa -tree --level=2 --icons' --wraps='exa --tree --level=2 --icons' --wraps='exa --icons' --wraps='exa --tree --level=1 --icons' --wraps='exa --tree --level=1 --icons --group-directories-first' --wraps='exa --tree --level=2 --icons --group-directories-first' --description 'alias ls=exa --tree --level=2 --icons --group-directories-first'
    exa --tree --level=2 --icons --group-directories-first $argv
end
