#!/usr/bin/python

# python
import re

# us
import utils
from output import *

# alib
import termcolors

# A for absolute.
# B or b for uninitialized data section (called BSS).
# D or d for initialized data section.
# G or g for initialized data section for small objects (global).
# i for sections specific to DLLs.
# N for debugging symbol.
# p for stack unwind section.
# R or r for read only data section.
# S or s for uninitialzed data section for small objects.
# T or t for text (code) section.
# U for undefined.
# V or v for weak object.
# W or w for weak objects which have not been tagged so.
# - for stabs symbol in an a.out object file.
# ? for 'symbol type unknown.'

class Symbol():
    def __init__(self, name, addr, type):
        self.name = name
        self.addr = addr
        self.type = type

    def __str__(self):
        return "%X %s %s" % (self.addr, self.type, self.name)

class Symbols():
    def __init__(self):
        self.addrToSyms = {}
        self.nameToSym = {}
        self.syms = []

        # this tracks that latest rename we used for the given name
        self.nameToLatestName = {}

    def incrSymName(self, name):
        answer = None

        # the current name we're incrementing could possibly start where we
        # left off on the previous name
        curr = name
        if name in self.nameToLatestName:
            curr = name

        match = re.match(r'^.*_(\d+)$', curr)
        if match:
            suffix = '_%d' % (int(match.group(1)))
            suffix_new = '_%d' % (int(match.group(1)) + 1)
            answer = re.sub(suffix, suffix_new, curr)
        else:
            answer = curr + '_0'

        self.nameToLatestName[name] = answer

        return answer
            
    def addSymbol(self, name, addr, type, renameDuplicates=0):
        quit = 0

        if name in self.nameToSym:
            if renameDuplicates:
                while name in self.nameToSym:
                    name_old = name
                    name = self.incrSymName(name_old)
                Warn("renamed duplicate %s to %s" % (name_old, name))
            else:                
                Error("duplicate symbol name: %s" % str(self.nameToSym[name]))
                return

        #Info("added symbol %s with address 0x%X" % (name, addr))
        sym = Symbol(name, addr, type)
        # addresses map to array of syms (address collision allowed)
        if addr in self.addrToSyms: self.addrToSyms[addr].append(sym)
        else: self.addrToSyms[addr] = [sym]
        # names map to single sym (name collision disallowed)
        self.nameToSym[name] = sym
        #
        self.syms.append(sym)

        #print "Adding new symbols: %s" % str(sym)
       
    def parseKallsymsOutput(self, lines):
        count = 0
       
        for l in lines.split("\n"):
            if not l:
                break
 
            match = re.match(r'^([a-fA-F0-9]+)\s+(.)\s+(.*?)\s*$', l)
            if not match:
                print "malformed symbol line: %s" % l
                break

            (addr, type, name) = (match.group(1), match.group(2), match.group(3))

            # filter out mapping symbols from lkm's like '$a' and '$d' 
            if name[0] == '$':
                #print 'it was line -%s- that caused it' % l
                continue

            addr = int(addr, 16)

            self.addSymbol(name, addr, type, 1)
            count += 1

        print "Loaded %d symbols" % count

    # replaces any 32-bit hex-encoded address with symbol name
    def valsToSyms(self, text):
        offset = 0

        while 1:
            match = re.search(r'(?:0x)?[a-fA-F0-9]{8,16}', text[offset:])

            if not match:
                break;
    
            textaddr = match.group(0)
            #print "searching for ", textaddr
            symname = self.getNearSymbol(int(textaddr, 16))
            if symname:
                # update offset of search
                offset = text.find(textaddr, offset) + len(textaddr)
                # replace the address with symbol name
                #print "replacing -%s- with -%s-" % (textaddr, symname)
                oldcolor = termcolors.color_stack[-1]
                text = text.replace(textaddr, '%s%s%s' % \
                    (termcolors.FOREGROUND_GREEN, symname, oldcolor))
                #print "after replace: ", text
            else:
                # update offset of search
                #print "old offset: ", offset
                offset = text.find(textaddr, offset) + len(textaddr)
                #print "new offset: ", offset

        return text

    # replace symbol names and symbol+XX to hex encoded addresses
    def symsToVals(self, text):
        for s in re.findall(r'\w+', text):
            if s in self.nameToSym:
                text = text.replace(s, '0x%X' % self.nameToSym[s].addr)

        return text

    def getNearSymbol(self, addr, threshold=1024):
        if addr in self.addrToSyms:
            return self.addrToSyms[addr][0].name

        # scan backwards for symbol (see if addr is symbol+offset)
        for a in range(addr-1, addr-threshold-1, -1):
            if a in self.addrToSyms:
                return self.addrToSyms[a][0].name + '+0x%02X' % (addr-a)

        # scan forwards for symbol (see if addr is symbol-offset
        for a in range(addr+1, addr + threshold + 1):
            if a in self.addrToSyms:
                return self.addrToSyms[a][0].name + '-0x%02X' % (a - addr)


        return None

    def search(self, pattern):
        syms = []
        for key in sorted(self.nameToSym.keys()):
            if re.match(pattern, key):
                syms.append(self.nameToSym[key])
        return syms

    def getAll(self):
        return self.syms

    def __getitem__(self, name):
        if name in self.nameToSym:
            return self.nameToSym[name].addr
        return None
            

if __name__ == "__main__":
    symtab = Symbols()

    symtab.loadKallsymsFile('/proc/kallsyms')

    
