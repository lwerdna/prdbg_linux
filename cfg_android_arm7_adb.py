# prdbg config
#-------------
#   TARGET OS: android 
# TARGET ARCH: ARMv7
#       COMMS: android debug bridge (adb) to /data/local/tmp/gofer

# python libs
import os
import re
import sys

# alib libs
sys.path.append(os.environ['PATH_ALIB_PY'])
import utils
import output

# prdbg libs
import mem_adb as mem
import probe_ARMv7 as probe
import ksyms

# toolchain lib disasm settings
if not 'CCOMPILER' in os.environ:
    raise Exception('no cross compiler found, please export CCOMPILER\n' + \
        'eg: $ export CCOMPILER=$HOME/arm-eabi-4.4.3/bin/arm-eabi')

tmp = os.environ['HOME'] + '/arm-eabi-4.4.3/bin/arm-eabi-'
toolchainOpts = { \
               'as' : tmp + 'as',
         'as_flags' : '',
               'ld' : tmp + 'ld',
         'ld_flags' : '',
          'objdump' : tmp + 'objdump',
    'objdump_flags' : ''
}

def install():
    tmp = utils.runGetOutput(['adb shell lsmod'], 1)
    output.Info(tmp)
    if re.search('prdbg', tmp):
        tmp = utils.runGetOutput(['adb shell su -c "rmmod prdbg"'], 1)
        output.Info(tmp)
         
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

def uninstall():
    tmp = utils.runGetOutput(['adb shell lsmod'], 1)
    output.Info(tmp)
    if re.search('prdbg', tmp):
        tmp = utils.runGetOutput(['adb shell su -c "rmmod prdbg"'], 1)
        output.Info(tmp)

def getKAllSyms():
    temp = utils.runGetOutput(['adb shell su -c "echo 0 > /proc/sys/kernel/kptr_restrict"'], 1)
    output.Info(temp)

    temp = utils.runGetOutput(['adb shell su -c "cat /proc/kallsyms"'], 1)
    return temp

