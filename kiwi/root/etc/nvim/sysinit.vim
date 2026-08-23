" Lyra OS system nvim config. This is the neovim package's own system
" config path (/etc/nvim/sysinit.vim, confirmed via `rpm -ql neovim` and
" `nvim --headless -c 'set rtp?'`), loaded automatically before any user
" init.vim/init.lua unless nvim is started with -u.
"
" Loaded before any user init.vim/init.lua, on both the Desktop and Server
" profile - vim/neovim are shared-base packages (kiwi/config.xml). Every
" setting here is a default a user's own ~/.config/nvim/init.vim or
" init.lua can freely override; nothing here is enforced. Neovim already
" ships sane defaults for a lot of this (:help nvim-defaults) - hlsearch,
" incsearch, wildmenu and mouse are on already, so this only adds what
" nvim leaves off.

" In order for neovim to use installed plugins/colorschemes shared with
" vim (e.g. this package's own colors/lyra.vim, under
" /usr/share/vim/site/colors).
set runtimepath+=/usr/share/vim/site

augroup LyraSpecTemplate
  autocmd!
  " RPM spec file skeleton - OBS-based packaging is how Lyra OS itself
  " ships software (docs/obs-release.md), so this is a real dev workflow
  " here, not upstream boilerplate.
  autocmd BufNewFile *.spec silent! 0read /usr/share/nvim/template.spec
augroup END

colorscheme lyra

set number
set cursorline
set scrolloff=4
set sidescrolloff=8
set list
set listchars=tab:»\ ,trail:·,nbsp:+
set ignorecase
set smartcase
set splitright
set splitbelow
set signcolumn=yes
set updatetime=300

set tabstop=4
set shiftwidth=4
set softtabstop=4
set expandtab
set autoindent

" Persistent undo across sessions. Root's HOME can be read-only under
" onlyRequired's minimal live/install environment, hence the isdirectory
" guard instead of assuming stdpath('state') is writable.
let s:lyra_undodir = stdpath('state') . '/undo'
if !isdirectory(s:lyra_undodir)
  silent! call mkdir(s:lyra_undodir, 'p', 0700)
endif
if isdirectory(s:lyra_undodir)
  let &undodir = s:lyra_undodir
  set undofile
endif
unlet s:lyra_undodir

" vim: et ts=2 sw=2
