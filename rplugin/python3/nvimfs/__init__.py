from os import mkdir, environ
from os.path import join, exists, ismount, isfile, dirname
from shutil import rmtree
from glob import glob
from subprocess import Popen
import neovim
from nvimfs.config import NeovimFSDict
from nvimfs.fs import __file__ as fs_script

@neovim.plugin
class NvimFSHandler(object):
    def __init__(self, vim):
        self.vim = vim
        self.config = None

    def __lshift__(self, args):
        """
        Syntactic sugar for executing commands:

            self << 'vsplit'

        """
        self.vim.command(args)

    @neovim.autocmd('VimEnter', sync=True)
    def init(self):
        """
        Setup the plugin on start.
        """
        self.__current_client = None
        self.config = NeovimFSDict(self.vim)
        self.config['id'] = self.vim.channel_id
        self.config['mountpoint'] = join(self.vim.eval('&rtp').split(',')[0], 'neovimfs')
        self.spawn_neovimfs()

    def spawn_neovimfs(self):
        """
        Mount the NeovimFS filesystem if not already mounted.
        Otherwise, register the current client using the filesystem interface (`/clients/new`).
        """
        if not exists(self.config['mountpoint']):
            mkdir(self.config['mountpoint'])
        if not ismount(self.config['mountpoint']):
            # NVIM_LISTEN_ADDRESS is used from the environment
            p = Popen([fs_script, self.config['mountpoint']])
        else:
            start_addr = environ['NVIM_LISTEN_ADDRESS']
            # start_addr -> /clients/new
            p = join(self.config['mountpoint'], 'clients', 'new')
            with open(p, 'w') as newf:
                newf.write(start_addr)

    @property
    def current_client(self):
        if not self.__current_client:
            client_names = glob(join(self.config['mountpoint'], 'clients', '*', 'name'))
            for n in client_names:
                with open(n, 'r') as cn:
                    name = cn.read()
                    if name == environ['NVIM_LISTEN_ADDRESS']:
                        self.__current_client = dirname(n)
                        break
        return self.__current_client

    @neovim.autocmd('VimLeavePre', pattern='*')
    @neovim.shutdown_hook
    def remove_client(self):
        """
        Remove the current client tree from the Oxberry filesystem when vim exits.
        """
        if self.current_client:
            rmtree(self.current_client)

    @neovim.autocmd('BufAdd', eval='fnamemodify(expand("<afile>"), ":p")')
    def add_buffer(self, filename):
        if self.current_client and isfile(filename):
            buffer_nr = str(self.vim.eval('bufnr("$")'))
            path = join(self.current_client, "buffers", buffer_nr)
            mkdir(path)
            with open(join(path, 'name'), 'w') as name:
                name.write(filename)
            open(join(path, 'tags'), 'a').close()

    @neovim.autocmd('BufDelete', eval='fnamemodify(expand("<afile>"), ":p")')
    def remove_buffer(self, filename):
        buf_tree_to_delete = None
        if self.current_client:
            buffer_names = glob(join(self.current_client, 'buffers', '*', 'name'))
            for bn in buffer_names:
                with open(bn, 'r') as bufname:
                    name = bufname.read()
                    if name == filename:
                        buf_tree_to_delete = dirname(bn)
                        break
            if buf_tree_to_delete:
                rmtree(buf_tree_to_delete)

    @neovim.autocmd('BufEnter', pattern='*/clients/*/eval,*/clients/*/cmd')
    def handle_eval_files(self):
        """
        These files in the Oxberry filesystem serve to evaluate viml, so we highlight them as such.
        """
        self << 'setfiletype vim'
