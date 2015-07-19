from os.path import join

class NeovimFSDict(dict):
    def __init__(self, vim):
        self.vim = vim
        self.vim.vars['neovimfs'] = {}

    def __getitem__(self, key):
        return self.vim.eval('g:neovimfs["'+key+'"]')

    def __setitem__(self, key, val):
        if isinstance(val, int):
            val = str(val)
        elif isinstance(val, str):
            val = '"'+val+'"'
        self.vim.command('let g:neovimfs["'+key+'"] = ' + val)
