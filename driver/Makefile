ifneq ($(KERNELRELEASE),)
# kbuild part of makefile
obj-m  := prdbg.o
#prdbg-y := prdbg.o 
else
 # Normal Makefile

all: module

module:
	KBUILD_VERBOSE=1 $(MAKE) -C $(KERNEL_DIR) M=`pwd`

clean:
	$(MAKE) -C $(KERNEL_DIR) M=`pwd` clean
endif

