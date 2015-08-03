# inlinehook is a utility for hooking ARM code
#
# terms
# =====
# src    - the address where instruction interception occurs
# dst    - the address that should execute when execution reaches src
# detour - the code at <dst> which executes instead of the code at <src>
# tramp  - a 16-byte code block that can be called to execute the original,
#          non-hooked code located at src
# jmp    - a "jump" implemented with an 8-byte "ldr pc, =<addr>"
# 
# key characteristics
# ===================
# - interception by overwriting with 8-byte "ldr pc, =<addr>"
# - creation of a "tramp" which can be used to call the original, non-hooked
#   version of the target function
#
# typical workflow
# ================
# 1) allocate or find a code cavity for your detour code, call this <dst>
# 2) construct your "detour", the code you want to execute when execution 
#    reaches <src>
# 3) call add_step1(<src>); this allocates and constructs the tramp, tracks it
#    internally, and returns its address so that you may use it in your detour
# 4) call add_step2(<src>, <dst>); this actually overwrites the code at <src>
#    with the jmp to <dst>
#
# picture
# =======
# ...
# ???:   instr
# ???:   instr
# src:   jmp dst ---------------------------> dst: detour instr0
# src+4:                                           detour instr1
# src+8: instr <----+                              ...
# ???:   instr      |    tramp:   src[0] <-------- call   tramp (optional)
# ???:   instr      |    tramp+4: src[1]           ...  
# ???:   instr      +--- tramp+8: jmp src+8
# ???:   instr
# ...                     

# python
import struct

# us
import mem
from output import *

# global list of all inlinehooks (for reference/removal)
inlinehooks = {}

# step 1 just builds the tramp, given <addrHook>
#
# (4) <src>[0..3] (stolen instr0)
# (4) <src>[4..7] (stolen instr1)
# (4) ldr pc, [pc, #0]
# (4) addr = <src> + 8
#   
#
def add_step1(src):
    global inlinehooks

    if src in inlinehooks:
        raise Exception("ERROR: inlinehook address 0x%X already exists!" % src)

    stolen = mem.read(src, 8)

    # build tramp
    trampBytes = ''
    trampBytes += stolen
    trampBytes += '\x04\xf0\x1f\xe5'
    trampBytes += struct.pack('<I', src+8)

    # allocate, store tramp
    trampAddr = mem.vmalloc(16)
    mem.write(trampAddr, trampBytes)
    
    # save this info
    inlinehooks[src] = { 'src':src, 'stolen':stolen, \
        'trampAddr':trampAddr, 'trampBytes':trampBytes }

    # return the tramp
    return trampAddr

# hook from src -> dst
#
# params:
#   src: the location that is hooked
#   dst: the location of the detour (destination of hook)
#
def add_step2(src, dst):
    global inlinehooks

    if not src in inlinehooks:
        raise Exception("ERROR: inlinehook address 0x%X doesn't exists!" % src)

    # write the hook
    hookBytes = ''
    hookBytes += '\x04\xf0\x1f\xe5'
    hookBytes += struct.pack('<I', dst)
    mem.writeCode(src, hookBytes)

    #
    inlinehooks[src]['dst'] = dst

def remove(src):
    global inlinehooks

    if not src in inlinehooks:
        raise Exception("ERROR: removing inlinehook at 0x%X, " + \
            "but I have no record of it!" % src)

    info = inlinehooks[src]

    # restore the stolen bytes over the hook src
    mem.writeCode(src, info['stolen'])

    # free the tramp
    mem.vfree(src, info['trampAddr'])

    # delete the entry in our list
    del(inlinehooks[src])

def remove_all():
    global inlinehooks

    for addr in inlinehooks.keys():
        remove(addr)

