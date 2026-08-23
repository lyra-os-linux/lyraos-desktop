" Lyra OS default colorscheme, shared by vim and neovim.
"
" Lives under /usr/share/vim/site/colors, the version-independent "site"
" runtime dir both editors already carry in their default runtimepath (see
" /etc/nvim/sysinit.vim's `set runtimepath+=/usr/share/vim/site`) - one file
" themes both. It only sets the ~20 generic highlight groups (Statement,
" Type, Constant, ...); every language-specific group already links to one
" of these via the syntax files shipped in vim-data / neovim's runtime, so
" this stays a handful of lines instead of a per-language table.
"
" Adapts to 'background' so both the dark and light Lyra palettes ship in
" one file, matching the "both variants installed, only the default
" differs" approach used by the Lyra GTK theme. Colors match the official
" palette from PROMPT-LYRA-OS.md (dark-slate "enterprise" set).

hi clear
if exists('syntax_on')
  syntax reset
endif
let g:colors_name = 'lyra'

function! s:hi(group, fg, bg, attr) abort
  let l:cmd = 'hi ' . a:group
  if a:fg[0] !=# ''
    let l:cmd .= ' guifg=' . a:fg[0] . ' ctermfg=' . a:fg[1]
  endif
  if a:bg[0] !=# ''
    let l:cmd .= ' guibg=' . a:bg[0] . ' ctermbg=' . a:bg[1]
  endif
  let l:cmd .= ' gui=' . a:attr . ' cterm=' . a:attr
  execute l:cmd
endfunction

let s:none = ['', '']

if &background ==# 'dark'
  " PROMPT-LYRA-OS.md dark base/tones: #16191d, #1c2025, #262b3d, #1e2b39
  let s:bg0 = ['#16191d', '234'] | let s:bg1 = ['#1c2025', '235']
  let s:bg2 = ['#262b3d', '237']
  let s:fg  = ['#d7dae0', '253'] | let s:fgd = ['#565f73', '240']
  let s:acc = ['#ced3f3', '189'] | let s:blu = ['#7c93f0', '104']
  let s:cya = ['#7dcfff', '117'] | let s:tea = ['#7fb4ca', '109']
  let s:grn = ['#9fca8c', '108'] | let s:amb = ['#d8a657', '179']
  let s:mau = ['#b48ead', '139'] | let s:org = ['#e0af68', '215']
  let s:red = ['#e06c75', '167']
else
  " PROMPT-LYRA-OS.md light base + lavender accent: #fcfcfd, #f4f5f7, #ced3f3
  let s:bg0 = ['#fcfcfd', '231'] | let s:bg1 = ['#f4f5f7', '254']
  let s:bg2 = ['#e4e7f5', '189']
  let s:fg  = ['#262b3d', '237'] | let s:fgd = ['#8890a3', '245']
  let s:acc = ['#4a56b0', '62']  | let s:blu = ['#3a56d4', '63']
  let s:cya = ['#1b7c9e', '31']  | let s:tea = ['#2f7d8c', '30']
  let s:grn = ['#3f7d40', '28']  | let s:amb = ['#a1670c', '136']
  let s:mau = ['#7d4f8c', '96']  | let s:org = ['#b5590c', '130']
  let s:red = ['#c53030', '124']
endif

" UI chrome
call s:hi('Normal',       s:fg,  s:bg0, 'NONE')
call s:hi('NormalFloat',  s:fg,  s:bg1, 'NONE')
call s:hi('LineNr',       s:fgd, s:none, 'NONE')
call s:hi('CursorLineNr', s:acc, s:bg1, 'bold')
call s:hi('CursorLine',   s:none, s:bg1, 'NONE')
call s:hi('Visual',       s:none, s:bg2, 'NONE')
call s:hi('Search',       s:bg0, s:acc, 'NONE')
call s:hi('IncSearch',    s:bg0, s:org, 'NONE')
call s:hi('MatchParen',   s:none, s:bg2, 'bold')
call s:hi('StatusLine',   s:acc, s:bg1, 'bold')
call s:hi('StatusLineNC', s:fgd, s:bg1, 'NONE')
call s:hi('VertSplit',    s:bg2, s:bg0, 'NONE')
call s:hi('Pmenu',        s:fg,  s:bg1, 'NONE')
call s:hi('PmenuSel',     s:acc, s:bg2, 'bold')
call s:hi('SignColumn',   s:fgd, s:none, 'NONE')
call s:hi('Folded',       s:fgd, s:bg1, 'italic')
call s:hi('NonText',      s:fgd, s:none, 'NONE')
call s:hi('Whitespace',   s:fgd, s:none, 'NONE')

" Syntax (generic groups; specific ones link here from vim-data/neovim's
" own syntax files)
call s:hi('Comment',    s:fgd, s:none, 'italic')
call s:hi('Constant',   s:amb, s:none, 'NONE')
call s:hi('String',     s:grn, s:none, 'NONE')
call s:hi('Identifier', s:cya, s:none, 'NONE')
call s:hi('Function',   s:cya, s:none, 'bold')
call s:hi('Statement',  s:blu, s:none, 'bold')
call s:hi('PreProc',    s:mau, s:none, 'NONE')
call s:hi('Type',       s:tea, s:none, 'NONE')
call s:hi('Special',    s:org, s:none, 'NONE')
call s:hi('Underlined', s:blu, s:none, 'underline')
call s:hi('Todo',       s:org, s:bg2, 'bold')
call s:hi('Error',      s:red, s:none, 'bold')
call s:hi('DiffAdd',    s:grn, s:bg1, 'NONE')
call s:hi('DiffChange', s:amb, s:bg1, 'NONE')
call s:hi('DiffDelete', s:red, s:bg1, 'NONE')
call s:hi('DiffText',   s:org, s:bg2, 'bold')
call s:hi('SpellBad',   s:red, s:none, 'undercurl')

delfunction s:hi
