This readme will detail how to compile the prdbg driver for your OS.

# for Ubuntu 14.04
Let's get the easy case over with first. There's a lot of support online that I don't want to repeat here. You should only have to run `uname -r` and make sure your kernel headers are in /usr/src/. From the driver directory, compile in one step with:

```
KERNEL_DIR=/usr/src/linux-headers-3.16.0-30-generic/ make
```

# for Android
Here are my recommended steps. Adjustments are often required.
1. find and download the kernel source for the Android OS you're targetting
  - cat /proc/version should yield useful
  - if you can't find the EXACT version, get one that matches as close as possible.
  - for handsets, manufacturers have open source sites, like http://opensource.samsung.com or http://sourceforge.net/motorola/
2. acquire the proper cross compiler
  - if present, look to the build instructions or readme in the kernel source release
  - most commonly it's Android prebuilt releases: arm-eabi-4.4.3, arm-eabi-4.6, and arm-eabi-4.7
  - note that some compilers have settings enabled by default, for example arm-eabi-4.7 introduces -mno-unaligned-access which will vary the Tag_CPU_unaligned_access in the resulting .ARM.attributes ELF section
3. configure your kernel source
  - hopefully the build instructions or readme from the kernel source release will include a default config in the build, something like `make VARIANT_DEFCONFIG=msm8960_m2_att_defconfig msm8960_m2_defconfig SELINUX_DEFCONFIG=selinux_defconfig`
4. make the kernel
  - sometimes the entire build isn't required, sometimes you can get away with compiling just the first bit, up until version.o and stuff gets made
5. compile the prdbg driver against the built kernel
  - with prdbg outside of kernel, the command will look something like `ARCH=arm CROSS_COMPILE=~/arm-eabi-4.7/bin/arm-eabi- KERNEL_DIR=~/Phones/s3/SGH-I747_NA_KK_Opensource/Kernel make`
  - remember to match your compiler with the one used when building the kernel
  - more details from at <kernel>/Documentation/kbuild/modules.txt

# Inserting
On the device, `insmod prdbg.ko` while monitoring /proc/kmsg. The usermode side does its best to provide an explanation from the kernel after requesting module insertion, so you might get something like "exec format error" or "invalid module format" but it's often wrong or not really helpful. Instead, look at the matching message from the running kernel log.
## ERROR "no symbol version for module_layout" or "disagrees about version of symbol module_layout"
The modpost script should be producing a prdbg.mod.c which has declares a section with the CRC's of all symbols that prdbg uses. It should look something like this:
```
static const struct modversion_info ____versions[]
__used
__attribute__((section("__versions"))) = {
	{ 0x6921dbc2, "module_layout" },
	{ 0x6bc3fbc0, "__unregister_chrdev" },
	{ 0x7dd5b7f7, "__register_chrdev" },
	{ 0x2e5810c6, "__aeabi_unwind_cpp_pr1" },
	{ 0x1db7dc40, "pgprot_kernel" },
	{ 0x67c2fa54, "__copy_to_user" },
	{ 0x999e8297, "vfree" },
	{ 0x28d6861d, "__vmalloc" },
	{ 0x41a8ea0a, "mem_text_write_kernel_word" },
	{ 0x9d669763, "memcpy" },
	{ 0x12da5bb2, "__kmalloc" },
	{ 0x27e1a049, "printk" },
	{ 0x37a0cba, "kfree" },
	{ 0xefd6cf06, "__aeabi_unwind_cpp_pr0" },
};
```
You have several options, sorted easiest to hardest:

1. if you're on a system with modprobe, try the --force-modversion or -f flags
2. try to rename the __versions section, this will usually make the module loader give up, see misc/rename_versions.py
3. build a substitute Module.symvers reflecting the symbols and CRC's of your running kernel, use misc/symvers_from_dkmem.c if /dev/kmem is accessible, else copy off the default modules and reap their version information with misc/symvers_from_lkms.py; replace the Module.symvers in your kernel source root directory and rebuild the module; prdbg.mod.c and the __versions section in prdbg.ko should reflect the new changes

## ERROR: "version magic '3.3.0 SMP preempt mod_unload ARMv7 ' should be '3.3.0-1514807 SMP preempt mod_unload ARMv7 '
There are several ways to go about this.
1. edit <kernel root>/scripts/setlocalversion to simply print out the required string by adding something like this to the end:
```
res="-1514807"
echo "$res"
```
2. edit the <kernel root>/include/generated/utsrelease.h
3. edit the VERMAGIC_STRING right in prdbg.mod.c between the modpost step and the file link

## ERROR: "TIMA: lkmauth--verification failed -1"
This is a Samsung KNOX component. If you have /dev/kmem available, you can use prdbg to read/write memory thru it. Look at /proc/kallsyms and see if lkmauth() is there. If it is, patching is relatively easy: just compare the disassembly to the source in <kernel root>/kernel/module.c and make it return success. If it's not available, then it's declared inline, and the task will be a bit harder, starting around sys_init_module() and examining the chain of (possibly inline) calls to load_module(), copy_and_check(), elf_header_check(), and lkmauth().

Some example patches are misc/lkmauth_bypass0.c and misc/lkmauth_bypass1.c.


