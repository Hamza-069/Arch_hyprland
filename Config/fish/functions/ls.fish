function ls --wraps='exa --tree --level=2 --icons --group-directories-first' --description 'list files'
    exa --tree --level=2 --icons --group-directories-first $argv
end
