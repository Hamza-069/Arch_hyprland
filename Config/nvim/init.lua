-- Leader
vim.g.mapleader = " "

-- Basic settings
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.tabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true
vim.opt.termguicolors = true

-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
vim.opt.rtp:prepend(lazypath)

-- Plugins
require("lazy").setup({
  -- Theme
  { "folke/tokyonight.nvim" },
  { "projekt0n/github-nvim-theme" },

  -- File explorer
  { "nvim-tree/nvim-tree.lua" },

  -- Status line
  { "nvim-lualine/lualine.nvim" },

  -- Fuzzy finder
  { "nvim-telescope/telescope.nvim", dependencies = { "nvim-lua/plenary.nvim" } },

  -- Treesitter (better syntax)
  { "nvim-treesitter/nvim-treesitter", build = ":TSUpdate" },

  -- LSP
  { "neovim/nvim-lspconfig" },
  -- Autocomplete
{ "hrsh7th/nvim-cmp" },
{ "hrsh7th/cmp-nvim-lsp" },
{ "hrsh7th/cmp-buffer" },
{ "hrsh7th/cmp-path" },

-- AI 
{ "Exafunction/codeium.nvim" },
-- Undo 
{
  "jiaoshijie/undotree",
  opts = {
    -- your options
  },
  keys = { -- load the plugin only when using it's keybinding:
    { "<leader>u", "<cmd>lua require('undotree').toggle()<cr>" },
  },
},

-- Snippets (optional but useful)
{ "L3MON4D3/LuaSnip" },
})

-- Theme setup
vim.cmd.colorscheme("github_dark")
vim.api.nvim_set_hl(0, "Normal", { bg = "#0d1117" }) -- GitHub dark base

-- Keymaps
vim.keymap.set("n", "<leader>e", ":NvimTreeToggle<CR>")
vim.keymap.set("n", "<leader>ff", ":Telescope find_files<CR>")
vim.keymap.set("n", "<leader>fg", ":Telescope live_grep<CR>")

vim.lsp.config("pyright", {})
vim.lsp.enable("pyright")

vim.lsp.config("lua_ls", {})
vim.lsp.enable("lua_ls")

require("codeium").setup({})
local cmp = require("cmp")

cmp.setup({
  snippet = {
    expand = function(args)
      require("luasnip").lsp_expand(args.body)
    end,
  },

  mapping = cmp.mapping.preset.insert({
    ["<C-b>"] = cmp.mapping.scroll_docs(-4),
    ["<C-f>"] = cmp.mapping.scroll_docs(4),
    ["<C-Space>"] = cmp.mapping.complete(),
    ["<CR>"] = cmp.mapping.confirm({ select = true }),
    ["<Tab>"] = cmp.mapping.select_next_item(),
    ["<S-Tab>"] = cmp.mapping.select_prev_item(),
  }),

  sources = cmp.config.sources({
    { name = "nvim_lsp" },
    { name = "buffer" },
    { name = "path" },
  }),
})
