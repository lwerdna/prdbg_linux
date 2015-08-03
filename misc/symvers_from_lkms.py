#!/usr/bin/python
#
# constructs Module.symvers by parsing thru __version .ko's from Android device
# run it in a directory of copied .ko's (like from /system/lib/modules)
# overwrite the Module.symvers produced when compiling your kernel source directory
# compile your module against your kernel source directory
# use KBUILD_VERBOSE=1 to ensure scripts/mod/modpost is being called
# examine your <module>.mod.c to see if your module's imports selected from Module.symvers correctly
# output should look something like:
#
# $ reading file: radio-iris-transport.ko
# module_layout: 0x6921DBC2
# smd_close: 0xA31A8580
# radio_hci_register_dev: 0x3DC08C69
# smd_disable_read_intr: 0x426E2EE2
# smd_named_open_on_edge: 0x774408A6
# ...
# kmalloc_caches: 0xE2BED9CD
# kmem_cache_alloc_trace: 0x5C7DB6E9
# capable: 0xC6CBBC89
# kfree: 0x37A0CBA
# __aeabi_unwind_cpp_pr0: 0xEFD6CF06
# free_contiguous_memory: 0x7C3BCCA8
# extracted 474 unique symbols and their check codes
# $ ls Module.symvers
# -rw-rw-r-- 1 a a 17969 Aug  2 15:31 Module.symvers
#
# 2015 andrewl

import re
import os
import sys
import struct

#------------------------------------------------------------------------------
# HELPERS
#------------------------------------------------------------------------------
# assumes 32-bit ARM ELF
def getVersionsSection(fname):
    fp = open(fname, 'rb')
    data = fp.read()
    fp.close()

    # read Elf32_Ehdr
    e_ident = data[0:16]
    (e_type, e_machine, e_version, e_entry, 
        e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, 
        e_phnum, e_shentsize, e_shnum, e_shstrndx) = \
        struct.unpack('HHIIIIIHHHHHH', data[16:52])

    # seek the section containing the section string table
    temp = e_shoff + e_shstrndx * 40
    (sh_name, sh_type, sh_flags, sh_addr, sh_offset, 
        sh_size, sh_link, sh_info, sh_addralign, sh_entsize) = \
        struct.unpack('IIIIIIIIII', data[temp:(temp + 40)])
    strTable = data[sh_offset:(sh_offset + sh_size)]

    # iterate over sections, finding the one named __versions
    for i in range(e_shnum):
        (sh_name, sh_type, sh_flags, sh_addr, sh_offset, 
            sh_size, sh_link, sh_info, sh_addralign, sh_entsize) = \
            struct.unpack('IIIIIIIIII', data[e_shoff+40*i: e_shoff+40*i+40])

        if strTable[sh_name:sh_name+10] == '__versions':
            return data[sh_offset:sh_offset+sh_size]

    # oh shit, not found
    raise Exception('coudln\'t locate __versions in %s' % fname)

#------------------------------------------------------------------------------
# MAIN
#------------------------------------------------------------------------------
fnames = []
for (dirpath, dirnames, filenames) in os.walk('.'):
    for filename in filenames:
        if re.match(r'^.*\.ko$', filename):
            fnames.append(filename)

symToCode = {}

for fname in fnames:
    print "reading file: %s" % fname

    data = getVersionsSection(fname)

    if len(data) % 64: raise Exception('bad size')

    while data:
        # parse the struct modversion_info
        code = struct.unpack('<I', data[0:4])[0]
        sym = data[4:64]

        # strip off trailing nulls
        while sym[-1] == '\x00':
            sym = sym[:-1]

        if sym in symToCode and symToCode[sym] != code:
            raise Exception('modules disagree about code for %s' % sym)

        symToCode[sym] = code
        print "%s: 0x%X" % (sym, code)

        data = data[64:]

print "extracted %d unique symbols and their check codes" % len(symToCode.keys())

fp = open('Module.symvers', 'w')
for sym in symToCode.keys():
    fp.write('0x%x\t%s\tdummy/path\n' % (symToCode[sym], sym))
fp.close()
