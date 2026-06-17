---------------
---- INPUT ----
---------------

hl.config({
	input = {
		kb_layout = "se",
		kb_variant = "",
		kb_model = "",
		kb_options = "",
		kb_rules = "",
		repeat_rate = 35,
		repeat_delay = 450,

		follow_mouse = 1,
		sensitivity = 0.1, -- -1.0 - 1.0, 0 means no modification.

		touchpad = {
			natural_scroll = false,
			disable_while_typing = false,
			clickfinger_behavior = true,
			scroll_factor = 0.8,
		},
	},
	gestures = {
		workspace_swipe_invert = false,
	},
})

hl.gesture({
	fingers = 3,
	direction = "horizontal",
	action = "workspace",
	workspace_swipe_invert = false,
})

hl.gesture({
	fingers = 3,
	direction = "down",
	action = "special",
	workspace_name = "magic",
	disable_inhibit = true,
})

hl.gesture({
	fingers = 3,
	direction = "up",
	action = function()
		hl.exec_cmd("swaync-client -t -sw")
	end,
})

hl.gesture({
	fingers = 2,
	direction = "pinchin",
	mods = "SUPER",
	action = "cursorZoom",
	zoom_level = 2.0,
	mode = "mult",
})
hl.gesture({
	fingers = 2,
	direction = "pinchout",
	mods = "SUPER",
	action = "cursorZoom",
	zoom_level = -2.0,
	mode = "mult",
})
-- Example per-device config
-- See https://wiki.hypr.land/Configuring/Advanced-and-Cool/Devices/ for more

hl.device({
	name = "--hid-gaming-mouse",
	sensitivity = -0.5,
	scroll_factor = 0.5,
})

hl.device({
	name = "2.4g-wireless-mouse",
	sensitivity = -0.5,
	scroll_factor = 0.5,
})
