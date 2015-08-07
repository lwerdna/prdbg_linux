This is a tool to muck with live Linux and Android kernels on x86-64 and ARM. You can read/write memory, view disassembly and symbol information conveniently, and set probe locations that report on the processor state after execution reaches them.

![screenshot](misc/screenshot.png?raw=true "screenshot")

The interface is a command environment is python. The heavy lifting is done by a kernel module which resides on the device under test.

Here's what you have to do to set it up:
1. prdbg relies on my alib repo, so clone it and set an environment variable to point at its path, eg: `export PATH_ALIB_PY=$HOME/Downloads/alib/py`
2. compile the driver and gofer for the OS/arch on your target
3. copy the gofer and driver to the target, insert the driver
4. select the config that describes your setup (see below) and symlink config.py to that config
5. if the target machine is a different architecture than your controller machine, set an environment variable to a cross compiler, eg: `export CCOMPILER=$HOME/arm-eabi-4.4.3/bin/arm-eabi-`
5. ./prdbg.py

In Linux, the setup is local, meaning that device under test is also the controlling machine. A networked version over something simple like telnet is planned.

                                           +----------+
                                           |kernel    |
                                           |          |
    +------+     +-----+     +------+      +------+   |
    |python| <-> |gofer| <-> |char  | <--> |driver|   |
    +------+     +-----+     |device|      +------+   |
                             +------+      |          |
                                           +----------+

With an Android device connected with a ADB (over USB or networked), the setup looks like this:

     DEVELOPMENT MACHINE | DEVICE UNDER TEST           +----------+
                         |                             |kernel    |
                         |                             |          |
    +------+     +---+   |   +-----+     +------+      +------+   |
    |python| <-> |adb| <---> |gofer| <-> |char  | <--> |driver|   |
    +------+     +---+   |   +-----+     |device|      +------+   |
                         |               +------+      |          |
                         |                             +----------+
                         |

The driver implements a minimal set of services: read/write mem, write executable mem, alloc/free mem, and call mem. The code that implements higher order functionality (like breakpoints) uses these services, and is located in the python component, where coding is easier. It must be compiled for the machine you're targetting.

The gofer (definition: a person who runs errands) is a simple command line utility that interacts with the driver and produces output on stdout, making it easy for python to communicate with it both locally and remotely. It must be compiled for the machine you're targetting.

If you've gotten LKM's to run on your device, you can use this almost immediately. Else, you may wish to guage the effort required by reading driver/README.md.

