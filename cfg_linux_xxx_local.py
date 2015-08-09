# prdbg config
#-------------
#   TARGET OS: Linux 
# TARGET ARCH: whatever your host is
#       COMMS: local (python invokes /tmp/gofer which reads/writes /tmp/prdbg char device)

# python libs
import re
import os
import sys

# prdbg libs
import mem_local as mem
import probe_x86_64 as probe
import ksyms

# alib
sys.path.append(os.environ['PATH_ALIB_PY'])
import utils
import output

# toolchain lib disasm settings
toolchainOpts = { \
               'as' : 'as',
         'as_flags' : '',
               'ld' : 'ld',
         'ld_flags' : '',
          'objdump' : 'objdump',
    'objdump_flags' : ''
}

def install():
    tmp = utils.runGetOutput(['lsmod'], 1)
    output.Info(tmp)
    if re.search('prdbg', tmp):
        tmp = utils.runGetOutput(['sudo rmmod prdbg'], 1)
        output.Info(tmp)
         
    # unhide addresses when reading /proc/kallsyms
    # gotta do fancy shit here that I don't understand yet, like:
    # sudo sh -c " echo 0 > /proc/sys/kernel/kptr_restrict"
    # echo 0 | sudo tee /proc/sys/kernel/kptr_restrict 
    #tmp = utils.runGetOutput(['su -c "echo 0 > /proc/sys/kernel/kptr_restrict"'], 1)
    #output.Info(tmp)

    # copy the gofer
    tmp = utils.runGetOutput(['cp ./gofer/gofer /tmp'], 1)
    output.Info(tmp)

    # insmod the driver
    tmp = utils.runGetOutput(['sudo insmod ./driver/prdbg.ko'], 1)
    output.Info(tmp)

    # create the character device if it doesn't exist
    tmp = utils.runGetOutput(['ls /dev/prdbg 2>&1'], 1)
    output.Info(tmp)
    if re.search('No such file or directory', tmp):
        tmp = utils.runGetOutput(['sudo mknod /dev/prdbg c 500 1'], 1)
        output.Info(tmp)

        tmp = utils.runGetOutput(['sudo chmod 666 /dev/prdbg'], 1)
        output.Info(tmp)

def uninstall():
    tmp = utils.runGetOutput(['lsmod'], 1)
    output.Info(tmp)
    if re.search('prdbg', tmp):
        tmp = utils.runGetOutput(['sudo rmmod prdbg'], 1)
        output.Info(tmp)

def getKAllSyms():
    temp = utils.runGetOutput(['echo 0 > /proc/sys/kernel/kptr_restrict'], 1)
    output.Info(temp)

    temp = utils.runGetOutput(['cat /proc/kallsyms'], 1)
    return temp

