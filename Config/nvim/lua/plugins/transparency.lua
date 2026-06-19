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
}
