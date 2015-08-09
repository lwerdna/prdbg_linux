CC = $(CCOMPILER)gcc

COMP_SWITCHES = -I$(PATH_ALIB_C)
LIB_SWITCHES = -L$(PATH_ALIB_C)

all: gofer

gofer: gofer.c
	$(CC) gofer.c $(COMP_SWITCHES) $(LIB_SWITCHES) -o gofer -lalib

clean:
	rm gofer *.o
