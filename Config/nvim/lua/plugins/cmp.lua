return {
  {
    "hrsh7th/nvim-cmp",
    opts = function(_, opts)
      local cmp = require("cmp")

      opts.mapping = cmp.mapping.preset.insert({
        -- Navigate with arrow keys
        ["<Down>"] = cmp.mapping.select_next_item(),
        ["<Up>"] = cmp.mapping.select_prev_item(),

        -- Tab to confirm
        ["<Tab>"] = cmp.mapping.confirm({ select = true }),

        -- Optional: disable default Enter behavior
        ["<CR>"] = cmp.config.disable,
      })
    end,
  },
}
