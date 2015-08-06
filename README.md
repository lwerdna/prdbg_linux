# prdbg_arm
This is a tool to muck with a live arm linux/Android kernel. You can read/write memory, view disassembly and symbol information conveniently, and even set rudimentary breakpoints.

![screenshot](misc/screenshot.png?raw=true "screenshot")

The interface is a command environment is python. The heavy lifting is done by a kernel module which resides on the device.

     DEVELOPMENT MACHINE | DEVICE UNDER TEST           +----------+
                         |                             |kernel    |
                         |                             |          |
    +------+     +---+   |   +-----+     +------+      +------+   |
    |python| <-> |adb| <---> |gofer| <-> |char  | <--> |driver|   |
    +------+     +---+   |   +-----+     |device|      +------+   |
                         |               +------+      |          |
                         |                             +----------+
                         |

The driver implements a minimal set of services: read/write mem, write executable mem, alloc/free mem, and call mem. The code that implements higher order functionality (like breakpoints) uses these services, and is located in the python component, where coding is easier.

If you've gotten LKM's to run on your device, you can use this almost immediately. Else, you may wish to guage the effort required by reading driver/README.md.

