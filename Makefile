ALL: probe.o

probe.o: probe.s
	$(CCOMPILER)as -mcpu=cortex-m3 -mthumb $< -o $@

clean:
	rm *.o *.pyc
