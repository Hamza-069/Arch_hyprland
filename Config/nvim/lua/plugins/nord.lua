return {
  {
    "gbprod/nord.nvim",
    lazy = true, -- Load immediately during startup
    priority = 1000, -- Make sure it loads before everything else
    config = function()
      require("nord").setup({
        transparent = false, -- Set to true if your terminal handles transparency
        terminal_colors = true, -- Extends the theme to active :terminal windows
        styles = {
          comments = { italic = true },
        },
      })
      vim.cmd.colorscheme("nord")
    end,
  },
}
