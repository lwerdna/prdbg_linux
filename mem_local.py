import os
import sys
import struct

# alib
sys.path.append(os.environ['PATH_ALIB_PY'])
import utils
import bytes
import parsing
from output import Info()

# if true: use /dev/kmem, else: thru the driver
prefer_kmem = False

#------------------------------------------------------------------------------
# CORE FUNCTIONS: read/write alloc/free call
#------------------------------------------------------------------------------
def read(addr, amt):
    if prefer_kmem:
        cmd = ['/tmp/gofer RMDK %X L%X"' % (addr, amt)]
    else:
        cmd = ['/tmp/gofer MEMREAD %X L%X"' % (addr, amt)]
    text = utils.runGetOutput(cmd, 1)
    Info(text)
    return parsing.parseBytesFromHexDump(text)

def write(addr, data):
    if prefer_kmem:
        cmd = ['/tmp/gofer WMDK %X"' % addr]
    else:
        cmd = ['/tmp/gofer MEMWRITE %X"' % addr]
    while data:
        cmd[0] += ' %02X' % struct.unpack('B', data[0])
        data = data[1:]
    text = utils.runGetOutput(cmd, 1)
    Info(text)
    return

def writeCode(addr, data):
    cmd = ['/tmp/gofer MEMWRITECODE %X"' % addr]
    while data:
        cmd[0] += ' %02X' % struct.unpack('B', data[0])
        data = data[1:]
    text = utils.runGetOutput(cmd, 1)
    Info(text)
    return

def vmalloc(amt):
    cmd = ['/tmp/gofer VMALLOC %X"' % amt]
    text = utils.runGetOutput(cmd, 1);
    Info(text)
    return parsing.parseHexValue(text)

def vfree(addr): 
    cmd = ['/tmp/gofer VFREE %X"' % addr]
    text = utils.runGetOutput(cmd, 1);
    Info(text)

def call(addr, arg):
    cmd = ['/tmp/gofer CALL %X"' % addr]
    text = utils.runGetOutput(cmd, 1);
    Info(text)

