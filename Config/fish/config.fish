if status is-interactive
    # Commands to run in interactive sessions can go here

    # Disable Fish welcome message
    set -U fish_greeting ""

    zoxide init fish | source

    # Custom prompt
    function fish_prompt
        set_color --bold blue
        echo -n (prompt_pwd) ""

        if test $status -ne 0
            set_color --bold red
            echo -n "x> "
        else
            set_color green
            echo -n "> "
        end

        set_color normal
    end

end
export PATH="$HOME/.local/bin:$PATH"
