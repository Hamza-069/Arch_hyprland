---------------------
---- MY PROGRAMS ----
---------------------

-- Set programs that you use
local terminal = "kitty"
local fileManager = "kitty -e yazi"
local menu = "~/.config/rofi/launchers/type-1/launcher.sh"
local editor = "kitty -e nvim"
local browser = "zen-browser"
local music = "LD_PRELOAD=/usr/local/lib/spotify-adblock.so spotify-launcher"

---------------------
---- KEYBINDINGS ----
---------------------

local mainMod = "SUPER" -- Sets "Windows" key as main modifier

-- Example binds, see https://wiki.hypr.land/Configuring/Basics/Binds/ for more
hl.bind(mainMod .. " + Escape", hl.dsp.exec_cmd("hyprctl kill"))
hl.bind(mainMod .. " + w", hl.dsp.window.close())
hl.bind(mainMod .. " + Q", hl.dsp.exec_cmd(terminal))
hl.bind(
	mainMod .. " + SHIFT + M",
	hl.dsp.exec_cmd("command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'")
)
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd(fileManager))
hl.bind(mainMod .. " + F", function()
	hl.dispatch(hl.dsp.window.float({ action = "toggle" }))
	hl.dispatch(hl.dsp.window.center({ window = "activewindow" }))
	hl.dispatch(hl.dsp.window.set_prop({ prop = "opacity_inactive_override", value = "1" }))
end)

hl.bind(mainMod .. " + R", hl.dsp.exec_cmd("sh -c 'pkill rofi || exec " .. menu .. "'"))
hl.bind(mainMod .. " + P", function()
	hl.dispatch(hl.dsp.window.float({ action = "toggle" }))
	hl.dispatch(hl.dsp.window.pin())
	hl.dispatch(hl.dsp.window.resize({ x = "830", y = "480" }))
	hl.dispatch(hl.dsp.window.center({ window = "activewindow" }))
	hl.dispatch(hl.dsp.window.set_prop({ prop = "opacity_inactive_override", value = "1" }))
end)
hl.bind(mainMod .. " + J", hl.dsp.layout("togglesplit")) -- dwindle only
hl.bind(mainMod .. " + SHIFT + J", hl.dsp.layout("rotatesplit"))

-- Move focus with mainMod + arrow keys
hl.bind(mainMod .. " + left", hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + up", hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + down", hl.dsp.focus({ direction = "down" }))

-- Move active window around current workspace
hl.bind(mainMod .. " + SHIFT + Right", hl.dsp.window.move({ direction = "r" }))
hl.bind(mainMod .. " + SHIFT + Left", hl.dsp.window.move({ direction = "l" }))
hl.bind(mainMod .. " + SHIFT + Up", hl.dsp.window.move({ direction = "u" }))
hl.bind(mainMod .. " + SHIFT + Down", hl.dsp.window.move({ direction = "d" }))
hl.bind(mainMod .. " + CONTROL + SHIFT + Right", hl.dsp.window.move({ workspace = "r+1" }))
hl.bind(mainMod .. " + CONTROL + SHIFT + Left", hl.dsp.window.move({ workspace = "r-1" }))

-- Switch workspaces with mainMod + [0-9]
-- Move active window to a workspace with mainMod + SHIFT + [0-9]
for i = 1, 10 do
	local key = i % 10 -- 10 maps to key 0
	hl.bind(mainMod .. " + " .. key, hl.dsp.focus({ workspace = i }))
	hl.bind(mainMod .. " + SHIFT + " .. key, hl.dsp.window.move({ workspace = i }))
end

--Custom
hl.bind(mainMod .. " + B", hl.dsp.exec_cmd(browser))
hl.bind(mainMod .. " + X", hl.dsp.exec_cmd(editor))
hl.bind(mainMod .. " + M", hl.dsp.exec_cmd(music))
hl.bind(mainMod .. " + SPACE", hl.dsp.exec_cmd("playerctl play-pause -p spotify"))
hl.bind("CONTROL + XF86FullScreen", hl.dsp.exec_cmd("~/.config/hypr/scripts/text-extractor.sh"))

--Clipboard
hl.bind(
	mainMod .. " + V",
	hl.dsp.exec_cmd(
		"clipvault list | rofi -dmenu -theme ~/.config/rofi/launchers/type-1/style-5.rasi | cut -f1 | clipvault get | wl-copy"
	)
)

hl.bind(mainMod .. " + T", hl.dsp.exec_cmd("~/.config/hypr/scripts/theme-selector.sh"))
hl.bind(mainMod .. " + SHIFT + R", hl.dsp.exec_cmd("~/.config/hypr/scripts/reload.sh | hyprctl reload"))
hl.bind(mainMod .. " + L", hl.dsp.exec_cmd("hyprlock"))
hl.bind("XF86FullScreen", hl.dsp.window.fullscreen({ action = "toggle" }))
hl.bind("XF86Poweroff", hl.dsp.exec_cmd("~/.config/rofi/powermenu/type-2/powermenu.sh"))

--Hyprshot
hl.bind("XF86LaunchA", hl.dsp.exec_cmd("hyprshot -m output --output-folder  ~/Screenshots/"))
hl.bind(mainMod .. " + XF86LaunchA", hl.dsp.exec_cmd("hyprshot -m region --output-folder  ~/Screenshots/"))
hl.bind("CTRL + XF86LaunchA", hl.dsp.exec_cmd("hyprshot -m window --output-folder  ~/Screenshots/"))

--hyprpicker
hl.bind(mainMod .. " + XF86FullScreen", hl.dsp.exec_cmd("hyprpicker -u 65 -s 9 -a -b -l -n"))

-- Example special workspace (scratchpad)
hl.bind(mainMod .. " + S", hl.dsp.workspace.toggle_special("magic"))
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.window.move({ workspace = "special:magic" }))

-- Scroll through existing workspaces with mainMod + scroll
hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e-1" }))
hl.bind(mainMod .. " + mouse_up", hl.dsp.focus({ workspace = "e+1" }))

-- Move/resize windows with mainMod + LMB/RMB and dragging
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(), { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

-- Laptop multimedia keys for volume and LCD brightness
hl.bind(
	"XF86AudioRaiseVolume",
	hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"),
	{ locked = true, repeating = true }
)
hl.bind(
	"XF86AudioLowerVolume",
	hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),
	{ locked = true, repeating = true }
)

hl.bind(
	mainMod .. " + XF86AudioRaiseVolume",
	hl.dsp.exec_cmd("playerctl -p spotify next"),
	{ locked = true, repeating = false }
)
hl.bind(
	mainMod .. " + XF86AudioLowerVolume",
	hl.dsp.exec_cmd("playerctl -p spotify previous"),
	{ locked = true, repeating = false }
)

hl.bind(
	"XF86AudioMute",
	hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),
	{ locked = true, repeating = false }
)
hl.bind(
	"XF86AudioMicMute",
	hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"),
	{ locked = true, repeating = false }
)
hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl set 5%+"), { locked = true, repeating = true })
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl set 5%-"), { locked = true, repeating = true })
hl.bind(
	mainMod .. " + XF86MonBrightnessUp",
	hl.dsp.exec_cmd("brightnessctl set 1%+"),
	{ locked = true, repeating = true }
)
hl.bind(
	mainMod .. " + XF86MonBrightnessDown",
	hl.dsp.exec_cmd("brightnessctl set 1%-"),
	{ locked = true, repeating = true }
)

-- Requires playerctl
hl.bind("XF86AudioNext", hl.dsp.exec_cmd("playerctl next"), { locked = true })
hl.bind("XF86AudioPause", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPlay", hl.dsp.exec_cmd("playerctl play-pause"), { locked = true })
hl.bind("XF86AudioPrev", hl.dsp.exec_cmd("playerctl previous"), { locked = true })
