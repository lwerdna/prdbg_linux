int kmem_generic(int b_read, unsigned long offset, void *buf, unsigned int count);
int kmem_read(unsigned long offset, void *buf, unsigned int count);
int kmem_write(unsigned long offset, void *buf, unsigned int count);
unsigned long get_kernel_sym(char *name);
int kmem_read_str(unsigned long offset, char *buf, unsigned int max);

