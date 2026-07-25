if status is-interactive
    # Commands to run in interactive sessions can go here

    # Disable Fish welcome message
    set -U fish_greeting ""

    zoxide init fish | source

    set -g fish_cursor_default block
    set -g fish_cursor_insert block
    set -g fish_cursor_replace_one block
    # fish_vi_key_bindings 

    # Custom prompt
    function fish_prompt
        set -l last_status $status
        set_color --bold blue
        echo -n (prompt_pwd) ""

        if test $last_status -ne 0
            set_color --bold red
            echo -n "> "
        else
            set_color --bold green
            echo -n "> "
        end

        set_color normal
    end
    function fish_right_prompt
        set_color --bold blue
        if test $CMD_DURATION -gt 0
            set -l ms $CMD_DURATION
            set -l mins (math --scale=0 "$ms / 60000")
            set -l secs (math --scale=0 "$ms % 60000 / 1000")
            set -l msec (math --scale=0 "$ms / 10 % 100")
            if test $mins -gt 0
                printf "%d:%02d.%02d  " $mins $secs $msec
            else
                printf "%d.%02d  " $secs $msec
            end
        end

        set_color --bold red
        echo -n (date "+%I:%M ")

        set_color normal
    end
end
export PATH="$HOME/.local/bin:$PATH"
