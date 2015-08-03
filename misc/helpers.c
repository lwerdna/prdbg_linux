#include <stdio.h>

/******************************************************************************
 KMEM READ/WRITE
******************************************************************************/
int 
kmem_generic(int b_read, unsigned long offset, void *buf, unsigned int count)
{
	int rc = -1;
    FILE *fp = NULL;

    /*
    if(b_read)
        printf("reading %d bytes from 0x%X\n", count, offset);
    else
        printf("writing %d bytes to 0x%X\n", count, offset);
    */    

    fp = fopen("/dev/kmem", "rb+");
    if(!fp) {
        printf("ERROR: fopen()\n");
        goto cleanup;
    }

	/* Seek to offset */
	if(fseek(fp, offset, SEEK_SET)) {
		printf("ERROR: fseek()\n");
        goto cleanup;
    }

	/* read/write */
    if(b_read) {
    	if(fread(buf, 1, count, fp) != count) {
    		printf("ERROR: fread()\n");
            goto cleanup;
        }
    }
    else {
    	if(fwrite(buf, 1, count, fp) != count) {
    		printf("ERROR: fwrite()\n");
            goto cleanup;
        }
    }

    rc = 0;

    cleanup:
    if(fp) {
        fclose(fp);
    }

    return rc;
}

/* read one byte at a time until null found, limited by max */
int
kmem_read_str(unsigned long offset, char *buf, unsigned int max)
{
    int rc=-1;

    int i;

    for(i=0; i<max; ++i) {
        if(kmem_generic(1, offset+i, buf+i, 1)) 
            goto cleanup;

        if(buf[i] == '\0') {
            rc = 0;
            break;
        }
    }

    cleanup:
    return rc;
}

int 
kmem_read(unsigned long offset, void *buf, unsigned int count)
{
    return kmem_generic(1, offset, buf, count);
}

int 
kmem_write(unsigned long offset, void *buf, unsigned int count)
{
    return kmem_generic(0, offset, buf, count);
}

/******************************************************************************
 UTILS
******************************************************************************/
unsigned long get_kernel_sym(char *name)
{
	FILE *f;
	unsigned long addr;
	char dummy;
	char sname[512];
	int ret;

	f = fopen("/proc/kallsyms", "r");
	if (f == NULL)
		return 0;

	ret = 0;
	while(ret != EOF) {
		ret = fscanf(f, "%p %c %s\n", (void **)&addr, &dummy, sname);
		if (ret == 0) {
			fscanf(f, "%s\n", sname);
			continue;
		}
		if (!strcmp(name, sname)) {
			fclose(f);
			return addr;
		}
	}

	fclose(f);
	return 0;
}

