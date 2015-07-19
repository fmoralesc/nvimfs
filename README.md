# nvimfs

A FUSE filesystem that exposes the Neovim API.

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
    /clients
	new
	0/
	   name
	   cmd
	   eval
	   buffers/
		new
		1/
		    name
~~~

This filesystem won't be unmounted when any particular neovim instance exists,
and the plugin will try to manage it so its contents are in sync with the
running neovim instances. This means it can be used to manage several neovim
instances at once: for example, to query if any instance is editing a file
matching 'buffer.py', you can use the typical unix tools:

~~~ sh
    $ cd clients/
    $ grep -r "test4" . --exclude new
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
