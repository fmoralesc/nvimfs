#!/usr/bin/env python3
import neovim
import re
from collections import defaultdict, namedtuple
from os import environ
from os.path import basename, dirname, join, isfile, exists
from errno import ENOENT
from stat import *
from time import time
try:
    from nvimfs.fuse import FUSE, FuseOSError, Operations
except:
    from fuse import FUSE, FuseOSError, Operations

OBuffer = namedtuple('OBuffer', 'name')

class OxberryFS(Operations):
    def __init__(self, start_client=None, mountpoint=None):
        self.mtpoint = mountpoint
        self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0 # file number
        self.cd = 0 # client number
        self.wd = 0 # window number
        now = time()
        self.files['/'] = dict(st_mode=(S_IFDIR | 0o0755), st_ctime=now,
                st_mtime=now, st_atime=now, st_nlink=2)
        self.mkdir('/clients') # contains seen clients
        self.create('/clients/new') # write to it to register a new client
        if start_client:
            self.write('/clients/new', start_client.encode())

    def init_client(self, address):
        """
        initializes a client.
        """
        path = '/clients/' + str(self.cd)
        self.mkdir(path)
        self.create(join(path,'name')) # keeps the socket address
        self.write(join(path, 'name'), address.encode())
        self.chmod(join(path, 'name'), 0o0444) # the name is read-only
        self.create(join(path, 'cmd')) # write to it to execute commands
        self.create(join(path, 'eval')) # write to set a expression, read to eval it
        self.mkdir(join(path, 'buffers')) # a directory of buffers
        self.create(join(path, 'buffers', 'new')) # write to it to create a new buffer
        self.populate_buffers(path)
        self.mkdir(join(path, 'windows')) # a directory of windows
        self.create(join(path, 'windows', 'new')) # write to it to create a new buffer
        #self.populate_windows(path)
        self.cd += 1

    def populate_buffers(self, client_path):
        cname = self.get_client_name(client_path + "/")
        nvim = neovim.attach("socket", path=cname)
        for buf in nvim.buffers:
            if isfile(buf.name):
                buf_path = join(client_path, "buffers", str(buf.number))
                self.init_buffer(buf, buf_path)

    def init_buffer(self, buf_data, address):
        self.mkdir(address)
        self.create(join(address, "name"))
        self.write(join(address, "name"), buf_data.name)
        #self.create(join(address, "options"))
        #self.create(join(address, "vars"))
        self.create(join(address, "tags"))

    def populate_windows(self, client_path):
        cname = self.get_client_name(client_path + "/")
        nvim = neovim.attach("socket", path=cname)
        for win in nvim.windows:
            self.wd += 1
            win_path = join(client_path, "windows", str(self.wd))
            self.init_window(win_path, win)

    def init_window(self, address, win_data):
        self.mkdir(address)
        #self.create(join(address, "options"))
        #self.create(join(address, "vars"))

    def get_client_name(self, address):
        m = re.match('/clients/\d*/', address)
        if m:
            name = self.data[join(m.group(), 'name')]
            if name != b'':
                return name.decode()

    def reap_clients_if_needed(self, address):
        for f in self.files:
            m = re.match('/clients/\d+/name', f)
            if m:
                name = self.data[m.group()]
                if name != b'':
                    if not exists(name):
                        self.rmdir(dirname(m.group()))
                        break

    def chmod(self, path, mode):
        self.files[path]['st_mode'] &= 0o0770000
        self.files[path]['st_mode'] |= mode
        return 0

    def chown(self, path, uid, gid):
        self.files[path]['st_uid'] = uid
        self.files[path]['st_gid'] = gid

    def create(self, path, mode=0o0644):
        self.files[path] = dict(st_mode=(S_IFREG | mode), st_nlink=1,
                                st_size=0, st_ctime=time(), st_mtime=time(),
                                st_atime=time())

        self.fd += 1
        return self.fd

    def getattr(self, path, fh):
        if path not in self.files:
            raise FuseOSError(ENOENT)

        return self.files[path]

    def getxattr(self, path, name, position=0):
        attrs = self.files[path].get('attrs', {})

        try:
            return attrs[name]
        except KeyError:
            return ''       # Should return ENOATTR

    def listxattr(self, path):
        attrs = self.files[path].get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode=0o0755):
        if not path in self.files:
            self.files[path] = dict(st_mode=(S_IFDIR | mode), st_nlink=1,
                                    st_size=0, st_ctime=time(), st_mtime=time(),
                                    st_atime=time())

            self.files['/']['st_nlink'] += 1
            return 0
        else:
            return -1

    def open(self, path, flags):
        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        return self.data[path][offset:offset + size]

    def readdir(self, path, fh):
        self.reap_clients_if_needed(path)
        files = [basename(x[1:]) for x in self.files \
                                        if x != '/' \
                                        and dirname(x) == path \
                                        and x != path]
        return ['.', '..'] + files

    def readlink(self, path):
        return self.data[path]

    def removexattr(self, path, name):
        attrs = self.files[path].get('attrs', {})

        try:
            del attrs[name]
        except KeyError:
            pass        # Should return ENOATTR

    def rename(self, old, new):
        self.files[new] = self.files.pop(old)

    def rmdir(self, path):
        # FIXME: handle files within the directories, and remove data too
        try:
            self.files.pop(path)
            self.files['/']['st_nlink'] -= 1
        except KeyError:
            pass

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        attrs = self.files[path].setdefault('attrs', {})
        attrs[name] = value

    #def statfs(self, path):
        #return dict(f_bsize=512, f_blocks=2000000, f_bavail=1000000)

    def symlink(self, target, source):
        self.files[target] = dict(st_mode=(S_IFLNK | 0o0777), st_nlink=1,
                                  st_size=len(source))

        self.data[target] = source

    def truncate(self, path, length, fh=None):
        self.data[path] = self.data[path][:length]
        self.files[path]['st_size'] = length

    def unlink(self, path):
        self.files.pop(path)

    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)
        self.files[path]['st_atime'] = atime
        self.files[path]['st_mtime'] = mtime

    def nvim_eval(self, nvim, exprs):
        vals = []
        for expr in exprs:
            try:
                evaled = nvim.eval(expr)
                if isinstance(evaled, bytes):
                    vals.append(evaled.decode())
                else:
                    vals.append(str(evaled))
            except neovim.api.nvim.NvimError:
                vals.append("'" + expr + "' couldn't be evaluated")
        vals.append('')
        read_data = "\n".join(vals).encode(errors="ignore")
        return read_data

    def write(self, path, data, offset=0, fh=None):
        r_len = len(data)
        cname = self.get_client_name(path)
        if cname:
            nvim = neovim.attach("socket", path=cname)
            lines = data.decode(errors="ignore").splitlines()
            if re.match('/clients/\d+/cmd', path):
                for c in lines:
                    nvim.command(c)
            elif re.match('/clients/\d+/eval', path):
                data = self.nvim_eval(nvim, lines)
            elif re.match('/clients/\d+/buffers/new', path):
                for f in lines:
                    nvim.command('drop ' + f)
                    # initialize the buffer tree
                    bufnr = str(nvim.eval('bufnr("%")'))
                    buf_path = join(re.match('/clients/\d+/buffers/', path).group(), bufnr)
                    self.init_buffer(OBuffer(f.encode()), buf_path)
            elif re.match('/clients/\d+/windows/new', path):
                for w in lines:
                    if re.match('((vertical|leftabove|aboveleft|rightbelow|belowright|topleft|botright)\s)*'\
                            'v?(split|new)', w):
                        nvim.command(w)
        else:
            if re.match('/clients/new', path):
                self.init_client(data.decode())
        # save the data
        # TODO: respect file permissions
        self.data[path] = self.data[path][:offset] + data
        self.files[path]['st_size'] = len(self.data[path])
        return r_len

if __name__ == '__main__':
    from sys import argv
    if 'NVIM_LISTEN_ADDRESS' in environ:
        fuse = FUSE(OxberryFS(environ['NVIM_LISTEN_ADDRESS'], argv[1]), argv[1], foreground=True)
