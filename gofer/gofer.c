#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h> /* open */
#include <stdint.h> /* uint32_t, etc. */
#include <inttypes.h> /* PRIxPTR, etc. */

#include <unistd.h>
#include <sys/stat.h>
#include <linux/fs.h>

#include "../driver/prdbg.h"

/* from alib */
#include "parsing.h"
#include "output.h"

int 
talk_driver(struct cmd_header *hdr)
{
    int rc = -1;
    struct stat mystat;
    int fd;

    /* try to connect to driver */
    rc = stat(DEVICE_FILE_PATH, &mystat);
    if(rc) {
        printf("stat() returned %d, trying mknod()\n", rc);

        if(mknod(DEVICE_FILE_PATH, S_IFCHR, 
          makedev(DEVICE_NUM_MAJOR, DEVICE_NUM_MINOR))) {
            printf("couldn't mknod(), quitting\n");
            goto cleanup;
        }
    }

	fd = open(DEVICE_FILE_PATH, O_RDWR, 0);
	if (fd < 0) {
		printf("open() returned %d\n", fd);
		goto cleanup;
	}

    /* send it */
    write(fd, hdr, hdr->len);
    read(fd, hdr, hdr->len);
	close(fd);

    rc = 0;
    cleanup:
    return rc;
}

void 
mem_read(uintptr_t addr, unsigned long bytes_n)
{
    struct cmd_mem_generic cmd;

    /* header part */
    cmd.hdr.cmd_id = CMD_MEM_READ;
    cmd.hdr.len = sizeof(cmd);

    /* command specific part */
    cmd.addr = (void *) addr;
    cmd.bytes_n = bytes_n;

    /* talk to driver */
    if(talk_driver((struct cmd_header *) &cmd) >= 0) {
        /* print the result */
        dump_bytes(cmd.bytes, bytes_n, addr);
    }
}

void 
mem_write(uintptr_t addr, unsigned char *buff, unsigned long bytes_n)
{
    struct cmd_mem_generic cmd = {
        .hdr.cmd_id = CMD_MEM_WRITE,
        .hdr.len = sizeof(struct cmd_mem_generic)
    };

    cmd.addr = (void *)addr;
    cmd.bytes_n = bytes_n;
    memcpy(&(cmd.bytes), buff, bytes_n);

    talk_driver((struct cmd_header *) &cmd);
}

void 
mem_write_code(uintptr_t addr, unsigned char *buff, unsigned long bytes_n)
{
    struct cmd_mem_generic cmd = {
        .hdr.cmd_id = CMD_MEM_WRITE_CODE,
        .hdr.len = sizeof(struct cmd_mem_generic)
    };

    cmd.addr = (void *)addr;
    cmd.bytes_n = bytes_n;
    memcpy(&(cmd.bytes), buff, bytes_n);

    talk_driver((struct cmd_header *) &cmd);
}

void 
vmalloc(uint32_t bytes_n)
{
    struct cmd_mem_generic cmd = {
        .hdr.cmd_id = CMD_VMALLOC,
        .hdr.len = sizeof(struct cmd_mem_generic)
    };

    cmd.bytes_n = bytes_n;

    talk_driver((struct cmd_header *) &cmd);

    printf("%p\n", cmd.addr);
}

void 
vfree(uintptr_t addr)
{
    struct cmd_mem_generic cmd = {
        .hdr.cmd_id = CMD_VFREE,
        .hdr.len = sizeof(struct cmd_mem_generic)
    };

    cmd.addr = (void *)addr;

    talk_driver((struct cmd_header *) &cmd);
}

void 
call(uintptr_t addr, unsigned long arg)
{
    struct cmd_execute_mem cmd = {
        .hdr.cmd_id = CMD_CALL,
        .hdr.len = sizeof(struct cmd_execute_mem)
    };

    cmd.addr = (void *)addr;
    cmd.arg = (void *)arg;

    talk_driver((struct cmd_header *) &cmd);
}

int 
kmem_generic(int b_read, uintptr_t addr, void *buf, unsigned int count)
{
	int rc = -1;
    FILE *fp = NULL;

    if(b_read)
        printf("reading %d bytes from %" PRIxPTR "\n", count, addr);
    else
        printf("writing %d bytes to %" PRIxPTR "\n", count, addr);
    
    fp = fopen("/dev/kmem", "rb+");
    if(!fp) {
        printf("ERROR: fopen()\n");
        goto cleanup;
    }

	/* seek to addr */
	if(fseek(fp, addr, SEEK_SET)) {
		printf("ERROR: fseek()\n");
        goto cleanup;
    }

	/* read/write */
    if(b_read) {
    	if(fread(buf, 1, count, fp) != count) {
    		printf("ERROR: fread()\n");
            goto cleanup;
        }

        printf("buf[0] is: 0x%02X\n", (*(unsigned char *)buf) & 0xFF);
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

void
generic_empty_command(int cmd_id)
{
    struct cmd_header hdr;
    hdr.cmd_id = cmd_id;
    hdr.len = sizeof(hdr);
    talk_driver(&hdr);
}

/******************************************************************************
 MAIN
******************************************************************************/
int 
main(int ac, char **av)
{
    int i, rc=-1;
    int cmd_arg0 = -1;
    int cmd_arg1 = -1;

    uintptr_t addr;
    unsigned int length;
    unsigned int tmp_uint32;

    unsigned char buff[256];

    if(ac <= 1) {
        return -1;
    }

    if(ac >= 3) {
        cmd_arg0 = atoi(av[2]);
    }

    if(ac >= 4) {
        cmd_arg1 = atoi(av[3]);
    }

    /*************************************************************************/
    /* memory reading/writing */ 
    /*************************************************************************/
    if(!strcmp(av[1], "MEMREAD")) {
        if(!parse_addr_range(ac, av, &addr, &length)) {
            mem_read(addr, length);
        }
    }
    else if(!strcmp(av[1], "MEMWRITE")) {
        if(!parse_addr_bytelist(ac, av, &addr, buff)) {
            mem_write(addr, buff, ac-3);
        }
    }
    else if(!strcmp(av[1], "MEMWRITECODE")) {
        if(!parse_addr_bytelist(ac, av, &addr, buff)) {
            mem_write_code(addr, buff, ac-3);
        }
    }

    /*************************************************************************/
    /* memory reading/writing using /dev/kmem */
    /*************************************************************************/
    else if(!strcmp(av[1], "RMDK") || !strcmp(av[1], "rmdk")) {
        printf("[R]ead [M]emory using /[D]ev/[K]mem\n");
        if(parse_addr_range(ac, av, &addr, &length)) {
            printf("ERROR: parse_addr_range()\n");
            goto cleanup;
        }

        memset(buff, '\xFA', sizeof(buff));
        printf("addr: %" PRIxPTR "\n", addr);
        printf("length: %08X\n", length);
        rc = kmem_read(addr, buff, length);

        if(rc) {
            printf("ERROR: kmem_read()\n");
            goto cleanup;
        }

        dump_bytes(buff, length, addr);
    }
    else if(!strcmp(av[1], "WMDK") || !strcmp(av[1], "wmdk")) {
        printf("[W]rite [M]emory using /[D]ev/[K]mem\n");
        if(!parse_addr_bytelist(ac, av, &addr, buff)) {
            rc = kmem_write(addr, buff, ac - 3); 

            if(rc) {
                printf("ERROR: kmem_write()\n");
                goto cleanup;
            }
        }
    }

    /*************************************************************************/
    /* memory allocation */
    /*************************************************************************/
    else if(!strcmp(av[1], "VMALLOC")) {
        if(!parse_uint32_hex(av[2], &tmp_uint32)) {
            vmalloc(tmp_uint32);
        }
    }
    else if(!strcmp(av[1], "VFREE")) {
        if(!parse_uintptr_hex(av[2], &addr)) {
            printf("vfree(%" PRIxPTR ")\n", addr);
            vfree(addr);
        }
    }
    /*************************************************************************/
    /* memory execution */ 
    /*************************************************************************/
    else if(!strcmp(av[1], "CALL")) {
        if(!parse_uintptr_hex(av[2], &addr)) {
            unsigned long arg;
            if(!parse_uintptr_hex(av[3], &arg)) {
                call(addr, arg);
            }
        }
    }

    /*************************************************************************/
    /* else */
    /*************************************************************************/

    else if(!strcmp(av[1], "CALLTEST") || !strcmp(av[1], "TEST")) {
        generic_empty_command(CMD_CALL_TEST);
    }
    
    else {
        printf("PRDBG gofer\n");
        printf("Last compiled: %s (%s)\n", __DATE__, __TIME__);
        printf("(unrecognized command line argument)\n");
    }

    /* done done done */ 
    cleanup:
    return 0;
}
