function n --wraps=fd\ .\ --hidden\ --exclude\ .git\ \|\ \\\nfzf\ --ansi\ --border\ --height=100\%\ --layout=reverse\ \\\n\ \ \ \ --prompt=\"\ Open\ \>\ \"\ \\\n\ \ \ \ --preview=\"if\ test\ -d\ \{\}\;\ eza\ --tree\ --level=2\ \{\}\;\ else\ bat\ --style=numbers\ --color=always\ --line-range\ :300\ \{\}\;\ end\"\ \\\n\ \ \ \ --bind\ \"enter:become\(nvim\ \{\}\)\" --description alias\ n=fd\ .\ --hidden\ --exclude\ .git\ \|\ \\\nfzf\ --ansi\ --border\ --height=100\%\ --layout=reverse\ \\\n\ \ \ \ --prompt=\"\ Open\ \>\ \"\ \\\n\ \ \ \ --preview=\"if\ test\ -d\ \{\}\;\ eza\ --tree\ --level=2\ \{\}\;\ else\ bat\ --style=numbers\ --color=always\ --line-range\ :300\ \{\}\;\ end\"\ \\\n\ \ \ \ --bind\ \"enter:become\(nvim\ \{\}\)\"
    fd . --hidden --exclude .git | \
fzf --ansi --border --height=100% --layout=reverse \
    --prompt=" Open > " \
    --preview="if test -d {}; eza --tree --level=2 {}; else bat --style=numbers --color=always --line-range :300 {}; end" \
    --bind "enter:become(nvim {})" $argv
end
