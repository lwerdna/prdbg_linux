#!/usr/bin/python

# from python
import os
import re
import sys
import struct
import string
import readline

# alib
sys.path.append(os.environ['PATH_CODE'] + '/alib/py')
import utils
import bytes
import parsing
import toolchain
import output

# ours
import mem
import ksyms
import probe

# globals
g_probes = []

#------------------------------------------------------------------------------
# MISC
#------------------------------------------------------------------------------
completer_last_text = ''
completer_text_options = []
def completer(text, state):
    global completer_last_text
    global completer_text_options
    result = None
    #print "called completer(%s, %d)" % (text, state)
    if text != completer_last_text:
        completer_last_text = text
        syms = ksyms.search(text + '.*')
        completer_text_options = []
        for sym in syms:
            completer_text_options.append(sym.name)

    if state < len(completer_text_options):
        result = completer_text_options[state]

    #print "returning ", result
    return result

def resolveToVal(text):
    # replace any symbol names with their numerical counterparts
    text = ksyms.symsToVals(text) 
    # calculate numerical expressions and python
    ret = eval(text)
    # done!
    return ret

#------------------------------------------------------------------------------
# MAIN
#------------------------------------------------------------------------------
# readline settings
readline.set_completer(completer)
readline.parse_and_bind('tab: complete') # default python binding for tab is to insert \t
delims = readline.get_completer_delims()
# remove '!' from deliminators so can tab complete eg: kernel!sys
readline.set_completer_delims(string.replace(readline.get_completer_delims(), '!', ''))

# toolchain lib disasm settings
CROSS_COMPILE = os.environ['HOME'] + '/arm-eabi-4.4.3/bin/arm-eabi-'
toolchainOpts = { \
               'as' : CROSS_COMPILE + 'as',
         'as_flags' : '',
               'ld' : CROSS_COMPILE + 'ld',
         'ld_flags' : '',
          'objdump' : CROSS_COMPILE + 'objdump',
    'objdump_flags' : ''
}

ksyms = ksyms.Symbols()

nextEffectiveCmd = ''
nextEffectiveAddr = 0

# user i/o loop
while 1:
    try:
        show_context = 0
    
        line = raw_input('prdbg> ')
   
        if not line:
            line = nextEffectiveCmd
        else:
            nextEffectiveCmd = line

        line = ksyms.symsToVals(line)

        firstTok = line.split()[0]

        # start/stop junk
        if(line == "q"):
            print "quiting..."
            break

        if line=='install' or line=='uninstall':
            # rmmod the driver in both cases 
            tmp = utils.runGetOutput(['adb shell lsmod'], 1)
            output.Info(tmp)
            if re.search('prdbg', tmp):
                tmp = utils.runGetOutput(['adb shell su -c "rmmod prdbg"'], 1)
                output.Info(tmp)
                 
            if line=='install':
                # unhide addresses when reading /proc/kallsyms
                tmp = utils.runGetOutput(['adb shell su -c "echo 0 > /proc/sys/kernel/kptr_restrict"'], 1)
                output.Info(tmp)

                # copy the gofer
                tmp = utils.runGetOutput(['adb push ./gofer/gofer /data/local/tmp'], 1)
                output.Info(tmp)

                # copy the driver
                tmp = utils.runGetOutput(['adb push ./driver/prdbg.ko /data/local/tmp'], 1)
                output.Info(tmp)

                # insmod the driver
                tmp = utils.runGetOutput(['adb shell su -c "insmod /data/local/tmp/prdbg.ko"'], 1)
                output.Info(tmp)

                # create the character device if it doesn't exist
                tmp = utils.runGetOutput(['adb shell ls /dev/prdbg'], 1)
                output.Info(tmp)
                if re.search('No such file or directory', tmp):
                    tmp = utils.runGetOutput(['adb shell su -c "/data/local/tmp/busybox mknod /dev/prdbg c 500 1"'], 1)
                    output.Info(tmp)
        
                    tmp = utils.runGetOutput(['adb shell su -c "chmod 666 /dev/prdbg"'], 1)
                    output.Info(tmp)

            continue

        # evaluate
        match = re.match(r'^\? (.*)$', line)
        if match:
            val = resolveToVal(match.group(1)) 
            print '0x%X' % val

            continue

        #----------------------------------------------------------------------
        # mem dumping 
        #----------------------------------------------------------------------
        if firstTok in ['db','dw','dd','dq','db ','dw ','dd ','dq ']:
            # save grouping (byte, word, dword, qword)
            grouping = {'b':1, 'w':2, 'd':4, 'q':8}[line[1]]

            # get rid of the command
            line = parsing.consumeTokens(line, ' ', 1)

            # get address, length
            if line:
                [addr, length] = parsing.parseAddressRange(line, 128)
            else:
                length = 128
                addr = nextEffectiveAddr

            # read, print bytes
            data = mem.read(addr, length)
            print repr(data)
            temp = bytes.getHexDump(data, addr, grouping); 
            output.ColorData()
            print temp
            output.ColorPop()
            
            nextEffectiveAddr = addr + length
            
            continue

        if firstTok in ['dbida', 'dbgdb', 'dbc', 'dbpython']:
            # get rid of the command
            line = parsing.consumeTokens(line, ' ', 1)

            # get address, length
            if line:
                [addr, length] = parsing.parseAddressRange(line, 128)
            else:
                length = 128
                addr = nextEffectiveAddr

            # read, print bytes
            data = mem.read(addr, length)

            if firstTok == 'dbida':
                print bytes.getIdaPatchIdc(addr, data)
            elif firstTok == 'dbgdb':
                print bytes.getGdbWrites(addr, data)
            elif firstTok == 'dbc':
                print bytes.getCString(data)
            elif firstTok == 'dbpython':
                print bytes.getPythonString(data)
            
            nextEffectiveAddr = addr + length
            
            continue

        #----------------------------------------------------------------------
        # mem writing 
        #----------------------------------------------------------------------
        if firstTok == 'eb':
            addr = 0

            # get rid of the command
            line = parsing.consumeToken(line)
            # get the address
            addr = parsing.parseHexValue(line)
            line = parsing.consumeToken(line)
            # get the bytes
            data = parsing.parseBytes(line)

            # read, print bytes
            mem.writeCode(addr, data)
            print "writing 0x%X bytes to 0x%X: %s" % (len(data), addr, repr(data))
            
            continue

        # disassemble
        if line[0:2] in ['u','u ']:
            line = parsing.consumeTokens(line, ' ', 1)
            length = 128

            if line:
                # try to make an address out of the given arguments
                line = ksyms.symsToVals(line)
                addr = eval(line)
            else:
                addr = nextEffectiveAddr

            data = mem.read(addr, length)

            disasm = toolchain.disasmToString(addr, data, toolchainOpts) 
            disasm = ksyms.valsToSyms(disasm)
            output.ColorData()
            print disasm
            output.ColorPop()

            nextEffectiveAddr = addr + length 

            continue

        #----------------------------------------------------------------------
        # symbol handling stuff
        #----------------------------------------------------------------------
        if(line == 'kallsyms' or line == 'kas'):
            temp = utils.runGetOutput(['adb shell su -c "echo 0 > /proc/sys/kernel/kptr_restrict"'], 1)
            output.Info(temp)

            temp = utils.runGetOutput(['adb shell su -c "cat /proc/kallsyms"'], 1)
            ksyms.parseKallsymsOutput(temp)
            continue

        if(line[0:2] == 'x '):
            line = parsing.consumeTokens(line, ' ', 1)
            print "Searching symbols for regex: %s" % line
            syms = ksyms.search(line) 
            for sym in syms:
                print sym
            continue

        if(line[0:3] == 'ln '):
            line = parsing.consumeTokens(line, ' ', 1)
            print "Searching symbols near: %s" % line
            symname = ksyms.getNearSymbol(int(line, 16)) 
            if symname:
                print symname
            else:
                print "No nearby symbols!"

            continue

        #----------------------------------------------------------------------
        # probing
        #----------------------------------------------------------------------
        if(line[0:5] == 'padd '):
            line = parsing.consumeTokens(line, ' ', 1)
            p = probe.Probe(int(line, 16))
            p.install()
            g_probes.append(p)

        if(line[0:5] == 'pdel '):
            line = parsing.consumeTokens(line, ' ', 1)
            for (i,p) in enumerate(g_probes):
                if p.addrHook == int(line, 16):
                    del(g_probes[i])
                    break
                   
        if(line == 'pdelall'):
            for (i,p) in enumerate(g_probes):
                p.uninstall()
                
            g_probes = []

        if(line == 'plist'):
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

