-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  local lazyrepo = "https://github.com/folke/lazy.nvim.git"
  local out = vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "--branch=stable",
    lazyrepo,
    lazypath,
  })
  if vim.v.shell_error ~= 0 then
    vim.api.nvim_echo({
      { "Failed to clone lazy.nvim:\n", "ErrorMsg" },
      { out,                            "WarningMsg" },
      { "\nPress any key to exit..." },
    }, true, {})
    vim.fn.getchar()
    os.exit(1)
  end
end
vim.opt.rtp:prepend(lazypath)

-- Setup plugins
require("lazy").setup({
  spec = {
    -- Load LazyVim core
    { "LazyVim/LazyVim", import = "lazyvim.plugins" },

    -- Your custom plugins
    { import = "plugins" },

    -- Catppuccin theme
    {
      "catppuccin/nvim",
      name = "catppuccin",
      priority = 1000,
      opts = {
        flavour = "mocha", -- latte, frappe, macchiato, mocha
        transparent_background = false,
      },
      config = function(_, opts)
        require("catppuccin").setup(opts)
      end,
    },

    -- GitHub theme
    { 'projekt0n/github-nvim-theme', name = 'github-theme' },

    -- Example extra plugin
    {
      "VPavliashvili/json-nvim",
      ft = "jsonc",
    },
  },

  defaults = {
    lazy = false,
    version = false,
  },

  install = {
    colorscheme = { "tokyonight", "habamax", "catppuccin" },
  },

  checker = {
    enabled = true,
    notify = false,
  },

  performance = {
    rtp = {
      disabled_plugins = {
        "gzip",
        "tarPlugin",
        "tohtml",
        "tutor",
        "zipPlugin",
      },
    },
  },
})
