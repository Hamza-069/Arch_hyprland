local function set_transparency()
  vim.cmd([[
    highlight Normal guibg=NONE
    highlight NormalFloat guibg=NONE
    highlight NonText guibg=NONE
    highlight SignColumn guibg=NONE
  ]])
end

return {
  {
    "LazyVim/LazyVim",
    init = function()
      vim.api.nvim_create_autocmd("ColorScheme", {
        callback = set_transparency,
      })
      vim.api.nvim_create_autocmd("User", {
        pattern = "VeryLazy",
        callback = set_transparency,
      })
    end,
  },
  -- Theme  = tokyonight STORM
  {
    "folke/tokyonight.nvim",
    lazy = true,
    opts = { style = "storm" },
  },
  -- highlight-colors
  {
    "brenoprata10/nvim-highlight-colors",
    config = function()
      require("nvim-highlight-colors").setup({})
    end,
  },
  -- For the .MD files
  {
    "MeanderingProgrammer/render-markdown.nvim",
    dependencies = { "nvim-treesitter/nvim-treesitter", "nvim-mini/mini.nvim" }, -- if you use the mini.nvim suite
    -- dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-mini/mini.icons' },        -- if you use standalone mini plugins
    -- dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-tree/nvim-web-devicons' }, -- if you prefer nvim-web-devicons
    ---@module 'render-markdown'
    ---@type render.md.UserConfig
    opts = {},
  },
}
