CC = $(CCOMPILER)gcc

COMP_SWITCHES =
LIB_SWITCHES =

all: gofer

gofer: gofer.c
	$(CC) gofer.c $(COMP_SWITCHES) $(LIB_SWITCHES) -o gofer -lautils

clean:
	rm gofer *.o
