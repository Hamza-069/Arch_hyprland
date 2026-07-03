--------------------------------
---- WINDOWS AND WORKSPACES ----
--------------------------------

-- See https://wiki.hypr.land/Configuring/Basics/Window-Rules/
-- and https://wiki.hypr.land/Configuring/Basics/Workspace-Rules/

-- Example window rules that are useful

local suppressMaximizeRule = hl.window_rule({
	-- Ignore maximize requests from all apps. You'll probably like this.
	name = "suppress-maximize-events",
	match = { class = ".*" },

	suppress_event = "maximize",
})
-- suppressMaximizeRule:set_enabled(false)

hl.window_rule({
	-- Fix some dragging issues with XWayland
	name = "fix-xwayland-drags",
	match = {
		class = "^$",
		title = "^$",
		xwayland = true,
		float = true,
		fullscreen = false,
		pin = false,
	},

	no_focus = true,
})

-- Layer rules also return a handle.
-- local overlayLayerRule = hl.layer_rule({
--     name  = "no-anim-overlay",
--     match = { namespace = "^my-overlay$" },
--     no_anim = true,
-- })
-- overlayLayerRule:set_enabled(false)

-- Hyprland-run windowrule
hl.window_rule({
	name = "move-hyprland-run",
	match = { class = "hyprland-run" },

	move = "20 monitor_h-120",
	float = true,
})

--Make some app FLOAST
hl.window_rule({ name = "float-sxiv", match = { class = "^Sxiv$" }, float = true, center = true })
hl.window_rule({ name = "float-Savefile", match = { title = "^Save File$" }, float = true, center = true })
hl.window_rule({ name = "float-blueman-manager", match = { class = "^blueman-manager$" }, float = true, center = true })
hl.window_rule({ name = "float-pavucontrol", match = { class = "^org\\.pulseaudio\\.pavucontrol$" }, float = true })
hl.window_rule({
	name = "float-spotify",
	match = { class = "^Spotify$" },
	float = true,
	size = "1115 615",
	center = true,
})

--This is for Picture-in-Picture
hl.window_rule({
	name = "Picture-in-Picture",
	match = { class = "^firefox$", title = "Picture-in-Picture" },
	float = true,
	size = "340 192", -- screensize/4
	pin = true,
	opacity = "1.0 override",
	move = "4 35",
})

hl.window_rule({
	name = "fix-xwayland-drags",
	match = {
		class = "^$",
		title = "^$",
		xwayland = true,
		float = true,
		fullscreen = false,
		pin = false,
	},
	no_focus = true,
})

hl.window_rule({
	name = "move-hyprland-run",
	match = {
		class = "hyprland-run",
	},
	move = "20 monitor_h-120",
	float = true,
})
