#!/usr/bin/python

# from python
import os
import re
import sys
import struct
import string
import readline

# alib
sys.path.append(os.environ['PATH_ALIB_PY'])
import utils
import bytes
import parsing
import toolchain
import output

# ours
import ksyms
import config
mem = config.mem
probe = config.probe
toolchainOpts = config.toolchainOpts

# globals
g_probes = []
g_symbols = ksyms.Symbols()

#------------------------------------------------------------------------------
# MISC
#------------------------------------------------------------------------------
completer_last_text = ''
completer_text_options = []
def completer(text, state):
    global completer_last_text
    global completer_text_options
    global g_symbols
    result = None
    #print "called completer(%s, %d)" % (text, state)
    if text != completer_last_text:
        completer_last_text = text
        syms = g_symbols.search(text + '.*')
        completer_text_options = []
        for sym in syms:
            completer_text_options.append(sym.name)

    if state < len(completer_text_options):
        result = completer_text_options[state]

    #print "returning ", result
    return result

def resolveToVal(text):
    global g_symbols
    # replace any symbol names with their numerical counterparts
    text = g_symbols.symsToVals(text) 
    # calculate numerical expressions and python
    ret = eval(text)
    # done!
    return ret

def evalReMatchGroup1(match):
    return '%X' % eval(match.group(0))

#------------------------------------------------------------------------------
# MAIN
#------------------------------------------------------------------------------
# readline settings
readline.set_completer(completer)
readline.parse_and_bind('tab: complete') # default python binding for tab is to insert \t
delims = readline.get_completer_delims()
# remove '!' from deliminators so can tab complete eg: kernel!sys
readline.set_completer_delims(string.replace(readline.get_completer_delims(), '!', ''))

nextEffectiveCmd = ''
nextEffectiveAddr = 0

# user i/o loop
while 1:
    try:
        # default values for memory params
        (addr, length) = (nextEffectiveAddr, 128)
    
        line = raw_input('prdbg> ')
   
        if not line:
            line = nextEffectiveCmd
        else:
            nextEffectiveCmd = line

        # pre parsing
        (cmd, delim, params) = line.partition(' ')
        print "params raw: %s" % params
        params = g_symbols.symsToVals(params) 
        print "params after symsToVals: %s" % params
        params = re.sub(r'[xa-fA-F0-9\+\-\*\/\s]+', evalReMatchGroup1, params)
        print "params after eval: %s" % params
        # start/stop junk
        if(cmd == "q"):
            break

        if cmd == 'install':
            config.install()

        if cmd == 'uninstall':
            config.uninstall()

        # evaluate
        if cmd == '?':
            print '0x%X' % resolveToVal(params)

        #----------------------------------------------------------------------
        # mem dumping 
        #----------------------------------------------------------------------
        if cmd in ['db','dw','dd','dq']:
            # save grouping (byte, word, dword, qword)
            grouping = {'b':1, 'w':2, 'd':4, 'q':8}[cmd[1]]

            # get address, length
            if params:
                [addr, length] = parsing.parseAddressRange(params, 128)

            # read, print bytes
            data = mem.read(addr, length)
            print repr(data)
            temp = bytes.getHexDump(data, addr, grouping); 
            temp = g_symbols.valsToSyms(temp)
            output.ColorData()
            print temp
            output.ColorPop()
            
            nextEffectiveAddr = addr + length

        if cmd in ['dbida', 'dbgdb', 'dbc', 'dbpython']:
            # get address, length
            if params:
                [addr, length] = parsing.parseAddressRange(params, 128)

            # read, print bytes
            data = mem.read(addr, length)

            if cmd == 'dbida':
                print bytes.getIdaPatchIdc(addr, data)
            elif cmd == 'dbgdb':
                print bytes.getGdbWrites(addr, data)
            elif cmd == 'dbc':
                print bytes.getCString(data)
            elif cmd == 'dbpython':
                print bytes.getPythonString(data)
            
            nextEffectiveAddr = addr + length

        #----------------------------------------------------------------------
        # mem writing 
        #----------------------------------------------------------------------
        if cmd == 'eb':
            addr = 0

            # get the address
            addr = parsing.parseHexValue(params)
            params = parsing.consumeToken(params)
            # get the bytes
            data = parsing.parseBytes(params)

            # read, print bytes
            mem.writeCode(addr, data)
            print "writing 0x%X bytes to 0x%X: %s" % (len(data), addr, repr(data))
            
        #----------------------------------------------------------------------
        # disassembling
        #----------------------------------------------------------------------
        if cmd == 'u':
            length = 128

            addr = int(params, 16)
            data = mem.read(addr, length)

            disasm = toolchain.disasmToString(addr, data, toolchainOpts) 
            disasm = g_symbols.valsToSyms(disasm)
            output.ColorData()
            print disasm
            output.ColorPop()

            nextEffectiveAddr = addr + length 

        #----------------------------------------------------------------------
        # symbol handling stuff
        #----------------------------------------------------------------------
        if cmd == 'kallsyms' or cmd == 'kas':
            temp = config.getKAllSyms()            
            g_symbols.parseKallsymsOutput(temp)

        if cmd == 'x':
            print "Searching symbols for regex: %s" % params
            syms = g_symbols.search(params) 
            for sym in syms:
                print sym

        if cmd == 'ln':
            print "Searching symbols near: %s" % params
            symname = g_symbols.getNearSymbol(int(params, 16)) 
            if symname:
                print symname
            else:
                print "No nearby symbols!"

        if cmd in ['dds', 'ddq']:
            if params:
                [addr, length] = parsing.parseAddressRange(params, 128)

            data = mem.read(addr, length)
            print repr(data)

            while data:
                value = None
                if cmd == 'dds':
                    if len(data) < 4: break;
                    value = struct.unpack('<I', data[0:4])[0]
                    data = data[4:]
                    addr += 4    
                if cmd == 'ddq':
                    if len(data) < 8: break;
                    value = struct.unpack('<Q', data[0:8])[0]
                    data = data[8:]
                    addr += 8    
 
                print "%x: %s" % (addr, g_symbols.valsToSyms('%X' % value))

        #----------------------------------------------------------------------
        # probing
        #----------------------------------------------------------------------
        if cmd == 'padd':
            p = probe.Probe(int(params, 16))
            p.install()
            g_probes.append(p)

        if cmd == 'pdel':
            for (i,p) in enumerate(g_probes):
                if p.addrHook == int(params, 16):
                    del(g_probes[i])
                    break
                   
        if cmd == 'pdelall':
            for (i,p) in enumerate(g_probes):
                p.uninstall()
                
            g_probes = []

        if cmd == 'plist':
            for p in g_probes:
                print p

    #----------------------------------------------------------------------
    # done
    #----------------------------------------------------------------------
    except KeyboardInterrupt:
        #print "ctrl+c detected"
        print ''
        continue

    except EOFError:
        print 'You needed sleep anyways!'
        break

    #except Exception:
    #    print 'exception occurred...'
    #    continue

