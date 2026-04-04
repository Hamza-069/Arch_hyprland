if status is-interactive
# Commands to run in interactive sessions can go here

# Disable Fish welcome message
set -U fish_greeting ""
end
starship init fish | source
zoxide init fish | source
