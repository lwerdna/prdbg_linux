# prdbg config
#-------------
#   TARGET OS: Linux 
# TARGET ARCH: whatever your host is
#       COMMS: local (python invokes /tmp/gofer which reads/writes /tmp/prdbg char device)

# python libs
import os

# prdbg libs
import mem_local as mem
import probe_x86_64 as probe
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
    tmp = utils.runGetOutput(['lsmod'], 1)
    output.Info(tmp)
    if re.search('prdbg', tmp):
        tmp = utils.runGetOutput(['su -c "rmmod prdbg"'], 1)
        output.Info(tmp)
         
    # unhide addresses when reading /proc/kallsyms
    # gotta do fancy shit here that I don't understand yet, like:
    # sudo sh -c " echo 0 > /proc/sys/kernel/kptr_restrict"
    # echo 0 | sudo tee /proc/sys/kernel/kptr_restrict 
    #tmp = utils.runGetOutput(['su -c "echo 0 > /proc/sys/kernel/kptr_restrict"'], 1)
    #output.Info(tmp)

    # copy the gofer
    tmp = utils.runGetOutput(['./gofer/gofer /data/local/tmp'], 1)
    output.Info(tmp)

    # insmod the driver
    tmp = utils.runGetOutput(['insmod ./driver/prdbg.ko'], 1)
    output.Info(tmp)

    # create the character device if it doesn't exist
    tmp = utils.runGetOutput(['ls /dev/prdbg'], 1)
    output.Info(tmp)
    if re.search('No such file or directory', tmp):
        tmp = utils.runGetOutput(['mknod /dev/prdbg c 500 1'], 1)
        output.Info(tmp)

        tmp = utils.runGetOutput(['chmod 666 /dev/prdbg'], 1)
        output.Info(tmp)

def uninstall():
    tmp = utils.runGetOutput(['lsmod'], 1)
    output.Info(tmp)
    if re.search('prdbg', tmp):
        tmp = utils.runGetOutput(['rmmod prdbg'], 1)
        output.Info(tmp)

