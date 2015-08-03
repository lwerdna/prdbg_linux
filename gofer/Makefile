CC = $(CCOMPILER)gcc

LIB_SWITCHES = -L$(PATH_ALIB_C)

all: gofer

gofer: gofer.c
	$(CC) --sysroot=$(NDK_SYSROOT) gofer.c output.c parsing.c $(LIB_SWITCHES) -o gofer -lalib

clean:
	rm gofer *.o
