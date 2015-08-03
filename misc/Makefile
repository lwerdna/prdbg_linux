# uses Android NDK to compile these utils
#
# in your environment, make sure $CCOMPILER and $NDK_SYSROOT are set
#
# example:
# $ echo $CCOMPILER
# /home/a/android-ndk-r10e/toolchains/arm-linux-androideabi-4.9/prebuilt/linux-x86_64/bin/arm-linux-androideabi-
# $ echo $NDK_SYSROOT
# /home/a/android-ndk-r10e/platforms/android-19/arch-arm

COMPILE_FLAGS = --sysroot=$(NDK_SYSROOT)

CC = $(CCOMPILER)gcc

all: lkmauth_bypass0 symvers_from_dkmem

helpers.o: helpers.c
	$(CC) $(COMPILE_FLAGS) -c helpers.c

lkmauth_bypass0: lkmauth_bypass0.c helpers.o
	$(CC) $(COMPILE_FLAGS) lkmauth_bypass0.c helpers.o -o lkmauth_bypass0

symvers_from_dkmem: symvers_from_dkmem.c helpers.o
	$(CC) $(COMPILE_FLAGS) symvers_from_dkmem.c helpers.o -o symvers_from_dkmem

clean:
	rm lkmauth_bypass0 symvers_from_dkmem *.o
