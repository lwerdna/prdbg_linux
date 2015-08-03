#!/usr/bin/python

from struct import pack, unpack

import os
import sys

# alib
sys.path.append(os.environ['PATH_CODE'] + '/alib/py')
import utils
import bytes
import parsing
import toolchain
import termcolors

# us
import mem
import inlinehook
from output import *

#------------------------------------------------------------------------------
# PROBE MANAGEMENT
#------------------------------------------------------------------------------

# a probe has three states:
# - uninstalled
# - installed
# - tripped

class Probe(object):
    # constructor:
    # 1) builds the probe
    # 2) allocates, copies itself to memory on target
    def __init__(self, addr):
        # the address of the probe is the address at which we want to sample
        # the context, or equivalently the address of the hook
        self.addrHook = addr

        self.detourBytes = ''
        self.detourSyms = ''

        CROSS_COMPILE = os.environ['HOME'] + '/arm-eabi-4.4.3/bin/arm-eabi-'
        self.toolchainOpts = { \
                   'as' : CROSS_COMPILE + 'as',
             'as_flags' : '',
                   'ld' : CROSS_COMPILE + 'ld',
             'ld_flags' : '',
              'objdump' : CROSS_COMPILE + 'objdump',
        'objdump_flags' : ''
        }

    def build(self):
        # currently, the detour is a simple JMP to the thunk

        # form the detour (body of probe)
        src = ''
        #src += '.syntax unified\n'
        #src += '.thumb\n'
        src += '.global detour_len\n'
        src += '.global context_len\n'
        src += '\n'
        src += 'detour:\n'
        # saving registers onto stack
        src += '    push    {r0-r12}\n'
        # check hit marker, skip
        src += '    adr     r0, ctx_hit\n'
        src += '    ldr     r1, [r0, #0]\n'
        src += '    cbnz    r1, detour_done\n'
        # not hit? mark hit
        src += '    mov     r1, #1\n'
        src += '    str     r1, [r0, #0]\n'
        # 
        src += 'detour_done:\n'
        src += '    ldr     pc, =0x%08X\n' % self.addrThunk

        src += 'context:\n'
        src += 'ctx_hit:\n'
        src += '    .word 0:\n'
        src += 'ctx_CPSR:\n'
        src += '    .word 0:\n'
        src += 'ctx_GPRs:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'
        src += '    .word 0:\n'


        src += 'context_end:\n'
        src += 'literal_pool:\n'
        src += '.ltorg\n'
        src += 'detour_end:\n'
        src += '.equ context_len, (context_end - context)\n'
        src += '.equ detour_len, (detour_end - detour)\n'
        src += '.end\n'
   
        # assemble this thing
        (detourBytes, detourSyms) = toolchain.assemble(src, self.toolchainOpts)

        self.detourBytes = detourBytes

        self.detourLen = detourSyms['detour_len']

        Info('detour assembled to 0x%X bytes' % len(self.detourBytes))
        Info('detour measures itself to be 0x%X bytes' % \
            self.detourLen)

        # allocate memory to hold the detour
        self.addrDetour = mem.vmalloc(len(self.detourBytes))
        Info('allocated 0x%X bytes at 0x%X for detour' % \
            (self.detourLen, self.addrDetour))

        # write the detour to allocated mem
        mem.write(self.addrDetour, self.detourBytes)

    #
    def install(self):
        state = self.getState()

        if state == 'installed':
            print 'ERROR: install() called on already-installed probe'
            return

        #  inlinehook step 1/2
        self.addrThunk = inlinehook.add_step1(self.addrHook)

        # - thunk is used when assembling, alloc'ing, and clopying the probe 
        # - this also sets .addrDetour)
        self.build()

        # inlinehook step 2/2
        inlinehook.add_step2(self.addrHook, self.addrDetour)

    # uninstall:
    # - restores the bytes before the hook was placed
    # - allocates memory for detour (couldn't do this early, size might change 
    #    depending on probe options)
    # - writes the hook 
    def uninstall(self):
        state = self.getState()

        if state in ['installed', 'tripped']:
            write_fw(self.addrHook, self.bytesOrig)

    #
    # three states:
    # - uninstalled
    # - installed
    # - tripped
    def getState(self, outCtx=None):
        if not self.detourBytes or not self.detourSyms or not self.addrDetour:
            Info('detourBytes or detourSyms or addrDetour is not initialized -> uninstalled')
            return 'uninstalled'
        
        lenCode = self.detourSyms['context']
        lenCtx = len(self.detourBytes) - lenCode
        
        data = mem.read(self.addrDetour, len(self.detourBytes))

        if data[0:lenCode] != self.detourBytes[0:lenCode]:
            Error('detour in memory doesn\'t match detour we assembled -> uninstalled')
            return 'uninstalled'

        # ok, now it's at least installed ... let's see if it's set
        if data[lenCode:] == '0x41'*lenCtx:
            Info('all those 0x41\s at end of probe -> installed')
            return 'installed'

        outCtx = data[lenCode:]
        return 'tripped'
 
    def __str__(self):
        # refresh state
        context = ''

        result = 'probe @%08X -> %08X -> %08X [%s]...' % \
            (self.addrHook, self.addrDetour, self.addrThunk, state)
         
        if self.getState == 'tripped':
            (CPSR, r13, r14, r00, r01, r02, r03, r04, r05, r06, r07, r08, r09, r10, r11, r12) = \
                unpack((ctxLength/4)*'I', context)
        
            # print "CPSR: 0x%X" % CPSR
            # CPSR - {application, interrupt, execution} program status register
            # application
            APSR_N = ((CPSR>>31) & 1) 
            APSR_Z = ((CPSR>>30) & 1)
            APSR_C = ((CPSR>>29) & 1) 
            APSR_V = ((CPSR>>28) & 1) 
            APSR_Q = ((CPSR>>27) & 1) 
       
            result += "\n(N,Z,C,V,Q)=(%d,%d,%d,%d,%d)" % (APSR_N,APSR_Z,APSR_C,APSR_V,APSR_Q)
            result += '\nr00=0x%08X r01=0x%08X r02=0x%08X r03=0x%08X' % (r00, r01, r02, r03)
            result += '\nr04=0x%08X r05=0x%08X r06=0x%08X r07=0x%08X' % (r04, r05, r06, r07)
            result += '\nr08=0x%08X r09=0x%08X r10=0x%08X r11=0x%08X' % (r08, r09, r10, r11)
            result += '\nr12=0x%08X  sp=0x%08X  lr=0x%08X  pc=0x%08X' % (r12, r13, r14, self.addrHook)
        
        return result

# remove inactive and tripped probes
def cmdProbeClean():
    global g_probes
    temp = []
    for p in g_probes:
        if p.getState() == 'set':
            temp.append(p)
    g_probes = temp

# list all probes
def cmdProbeList():
    global g_probes
    for p in g_probes:
        print p

#
def cmdProbeUnset():
    global g_probes
    for p in g_probes:
        p.unset()
    g_probes = []

def cmdProbeAdd(addr, dumpSource):
    global g_probes

    # clean out inactive/tripped probes
    cmdProbeClean()

    # calculate room
    probeLen = getSym(probe_file, "probe_len")
    totalMem = cfg['ADDR_PROBE_BODIES_END'] - cfg['ADDR_PROBE_BODIES']
    maxProbes = totalMem / probeLen
    print "totalMem: %Xh" % totalMem
    print "probeLen: %Xh (%d) bytes" % (probeLen, probeLen)
    print "maxProbes: %Xh" % maxProbes
    if len(g_probes) >= maxProbes:
        print "ERROR: max probes reached"
        return

    # sort the existing probes based on their body address
    g_probes = sorted(g_probes, key = lambda probe: probe.addrBody)

    spot = cfg['ADDR_PROBE_BODIES']
    for p in g_probes:
        if p.addrBody == spot:
            spot += probeLen
        else:
            break

    if spot >= cfg['ADDR_PROBE_BODIES_END']:
        print "ERROR: no free spots for probe body"
        return

    probe = Probe(addr, spot, dumpSource)
    probe.set()
    g_probes.append(probe)

    return probe

