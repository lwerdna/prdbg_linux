#!/usr/bin/python

# rename __versions to AAAAAAAAAA to hopefully make insmod and Android skip
# over symol version checking

import os
import sys

fo = open(sys.argv[1], 'r+b')
stuff = fo.read()
from struct import pack, unpack

# read Elf32_Ehdr
e_ident = stuff[0:16]
(e_type, e_machine, e_version, e_entry, 
    e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, 
    e_phnum, e_shentsize, e_shnum, e_shstrndx) = \
    unpack('HHIIIIIHHHHHH', stuff[16:52])

# seek the section containing the section string table
temp = e_shoff + e_shstrndx * 40
(sh_name, sh_type, sh_flags, sh_addr, sh_offset, 
    sh_size, sh_link, sh_info, sh_addralign, sh_entsize) = \
    unpack('IIIIIIIIII', stuff[temp:(temp + 40)])

# replace only within section string table, insert into file
strtab = stuff[sh_offset:(sh_offset + sh_size)]
print "before: (len:%d)\n%s" % (len(strtab), repr(strtab))
strtab = strtab.replace('__versions', 'AAAAAAAAAA')
print "after: (len:%d)\n%s" % (len(strtab), repr(strtab))
print repr(strtab)

# write back
fo.seek(sh_offset)
fo.write(strtab)
fo.close()

