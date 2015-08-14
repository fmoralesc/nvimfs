# nvimfs

A FUSE filesystem that exposes the Neovim API.

## Dependencies

* FUSE
* Neovim
* Python 3 (tested using 3.4)
* `python-neovim` for Python 3 (`pip3 install neovim`)

## Setup

First, install in your 'runtimepath'. Using a plugin manager like [vim-plug][],
you need to add this to your vimrc:

~~~ vim
Plug 'fmoralesc/nvimfs'
~~~

and then execute

~~~ vim
:PlugInstall
~~~

to download and install the plugin. Afterwards, register the [remote
plugin][remote-plugin] with

~~~ vim
:UpdateRemotePlugins
~~~

and finally, restart Nevim.

[vim-plug]: https://github.com/junegunn/vim-plug

[remote-plugin]: http://neovim.io/doc/user/remote_plugin.html#remote-plugin

## Usage

The nvim filesystem will be mounted by default on `&rtp[0]` (typically,
`~/.nvim/`), under the `neovimfs` folder.

The typical tree will look like this:

~~~
neovimfs/
└── clients
    ├── 0
    │   ├── buffers
    │   │   ├── 1
    │   │   │   ├── name
    │   │   │   └── tags
    │   │   ├── 2
    │   │   │   ├── name
    │   │   │   └── tags
    │   │   └── new
    │   ├── cmd
    │   ├── eval
    │   ├── name
    │   └── windows
    │       └── new
    └── new

~~~

As you can see, at the toplevel there is the `clients/` directory. In it there
is a file called `new`, and a series of numbered directories, each representing
a neovim client. To register a new client, you can write the path to the client
socket to the `new` file, which will initialize the corresponding subdirectory
(the plugin does this automatically for every new client).

The filesystem won't be unmounted when any particular neovim instance exists,
and the plugin will try to manage it so its contents are in sync with the
running neovim instances. This means it can be used to manage several neovim
instances at once: for example, to query if any instance is editing a file
matching `buffer.py`, you can use the typical unix tools:

~~~ sh
    $ cd clients/
    $ grep -r "buffer.py" . --exclude new
    ./2/buffers/10/name:/home/felipe/devel/project/dir/buffer.py
    ./3/buffers/2/name:/home/felipe/devel/toy/newbuffer.py
~~~

You can send commands to the running nvim instances by writing to the `cmd`
file:

~~~ sh
    $ echo "e /tmp" > clients/0/cmd
~~~

You can also evaluate expressions:

~~~ sh
    $ echo "has('nvim')" > clients/0/eval
    $ cat clients/0/eval
    1
~~~

**Note**: multiple lines can be written to the `eval` file, so you can use it
as a scratch buffer from within Neovim. You can also append new expressions to
the file:


~~~ sh
    $ echo "1+1" >> clients/0/eval
    $ cat clients/0/eval
    1
    2
~~~
