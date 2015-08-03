/*  - insmod this into the kernel
    - this LKM publishes an character device identified by "major number"
      identifier (see DEVICE_NUM_MAJOR)
    - use mknod <DEVICE_FILE_PATH> c <DEVICE_NUM_MAJOR> <DEVICE_NUM_MINOR> 
      eg: "mknod /dev/prdbg c 500 1"
    - use chmod 666 <DEVICE_FILE_PATH> to get usermode progs to read/write it
      eg: "chmod 666 /dev/prdbg"
    - writing to the device saves the command struct to allocated memory
    - reading from the device processes the saved command, and the output is
      read straight forward
*/

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/vmalloc.h>

#include <asm/uaccess.h>
#include <asm/pgtable.h>
#include <asm/cacheflush.h>
//#include <asm/mmu_writeable.h> // for mem_text_write_kernel_word()

#include "prdbg.h"

//-----------------------------------------------------------------------------
// GLOBALS
//-----------------------------------------------------------------------------

/* this is the last command send from the usermode program */
struct cmd_header *cmd_hdr = 0;

//-----------------------------------------------------------------------------
// TEST STUFF
//-----------------------------------------------------------------------------
void
prdbg_test(void)
{
    printk("%s()\n", __func__);
}

//-----------------------------------------------------------------------------
// CHAR DEVICE STUFF (how usermode interacts with us)
//-----------------------------------------------------------------------------

/* callback - process open file */
static int 
chrdev_open(struct inode *inode, struct file *file)
{
    //printk("%s()\n", __func__);
    return 0;
}

/* callback - process closes file */
static int 
chrdev_release(struct inode *inode, struct file *file)
{
    //printk("%s()\n", __func__);
    return 0;
}

/* callback - process reads file */
static ssize_t 
chrdev_read(struct file *file, char __user *buffer,
    size_t length, loff_t *offset)
{
    ssize_t rc = -EINVAL;

    //printk("%s()\n", __func__);

    if(!cmd_hdr) {
        printk("missing command\n");
        goto cleanup;
    }

    printk("acting on command id 0x%X\n", cmd_hdr->cmd_id);

    switch(cmd_hdr->cmd_id) {
        case CMD_MEM_READ:
        case CMD_MEM_WRITE:
        {   
            struct cmd_mem_generic *cmd_mem = 
                (struct cmd_mem_generic *)cmd_hdr;

            if(cmd_hdr->cmd_id == CMD_MEM_READ) {
                printk("Reading 0x%X bytes from virtual address %p\n", 
                    cmd_mem->bytes_n, cmd_mem->addr); 

                /* copy from kernel memory into result of command */
                memcpy(&(cmd_mem->bytes), (void *)cmd_mem->addr, cmd_mem->bytes_n);
            }
            else {
                printk("Writing 0x%X bytes to virtual address %p\n", 
                    cmd_mem->bytes_n, cmd_mem->addr); 

                /* copy command buffer into memory */
                memcpy((void *)cmd_mem->addr, cmd_mem->bytes, cmd_mem->bytes_n);
            }
           
        }
        break;

        case CMD_MEM_WRITE_CODE:
        {
            struct cmd_mem_generic *cmd_mem = 
                (struct cmd_mem_generic *)cmd_hdr;

            #ifdef CONFIG_STRICT_MEMORY_RWX
            int i;
            unsigned long *pAddr, *pData;
            #endif

            if(cmd_mem->bytes_n % 4) {
                printk("ERROR: when writing code, byte amount (0x%X) must be "
                    "multiple of 4!\n", cmd_mem->bytes_n);

                goto cleanup;
            }

            printk("Writing 0x%X bytes to virtual address %p\n", 
                cmd_mem->bytes_n, cmd_mem->addr); 

            #ifdef CONFIG_STRICT_MEMORY_RWX
            pAddr = cmd_mem->addr;
            pData = (void *) cmd_mem->bytes;
            for(i=0; i<(cmd_mem->bytes_n)/4; i++) {
                printk("calling mem_text_write_kernel_word(0x%p, 0x%X);\n", pAddr + i, (unsigned int)pData[i]);
                mem_text_write_kernel_word(pAddr + i, pData[i]);
            }
            #else
            memcpy(cmd_mem->addr, cmd_mem->bytes, cmd_mem->bytes_n);
            flush_icache_range((unsigned long)cmd_mem->addr,
                (unsigned long)cmd_mem->addr + cmd_mem->bytes_n);
            #endif
        }
        break;

        case CMD_VMALLOC:
        {
            int size;
            void *addr;

            struct cmd_mem_generic *cmd_mem = 
                (struct cmd_mem_generic *)cmd_hdr;

            size = cmd_mem->bytes_n;

            /* vmalloc() calls __vmalloc() with some default flags...
                we skip right to the source */
            printk("__vmalloc(0x%X, 0x%X, 0x%X)\n", size, GFP_KERNEL, PAGE_KERNEL_EXEC);
            addr = __vmalloc(size, GFP_KERNEL, PAGE_KERNEL_EXEC);
            if(!addr) {
                printk("ERROR: __vmalloc()\n");
                goto cleanup;
            }
            
            printk("allocation: 0x%p\n", addr);

            /* notify caller */
            cmd_mem->addr = addr;
        }
        break;
        
        case CMD_VFREE:
        {
            struct cmd_mem_generic *cmd_mem = 
                (struct cmd_mem_generic *)cmd_hdr;

            printk("Freeing buffer %p\n", cmd_mem->addr);

            vfree(cmd_mem->addr);
        }
        break;

        case CMD_CALL:
        {
            void (*pfunc)(void *) = 0;

            struct cmd_execute_mem *cmd =
                (struct cmd_execute_mem *)cmd_hdr;

            printk("\"Call\"ing buffer %p(%p)\n", cmd->addr, cmd->arg);

            pfunc = cmd->addr;

            pfunc(cmd->arg);
        }
        break;

        case CMD_CALL_TEST:
        {
            printk("calling test()...\n");
            prdbg_test();
        }
        break;

        default:
            printk("unknown ID: 0x%X\n", cmd_hdr->cmd_id);
    }

    /* copy entire command struct (with bytes populated) to 
       userspace read buffer */
    {
        int temp;
        temp = copy_to_user(buffer, cmd_hdr, cmd_hdr->len); 
    }

    rc = cmd_hdr->len; 
    
    cleanup:

    /* free up buffered command */
    if(cmd_hdr) {
        kfree(cmd_hdr);
        cmd_hdr = 0;
    }

    return rc;
}

static ssize_t 
chrdev_write(struct file *filp, const char *buff, size_t len, 
    loff_t * off)
{
    ssize_t rc = -EINVAL;
    struct cmd_header *tmp_hdr;

    //printk("%s()\n", __func__);

    /* free previous command, if present */
    if(cmd_hdr) {
        kfree(cmd_hdr);
        cmd_hdr = 0;
    }

    /* check claimed size */
    tmp_hdr = (struct cmd_header *)buff;
    if(len != tmp_hdr->len) {
        printk("linux claims incoming struct size 0x%X "
                "struct claims its size is 0x%X\n", (unsigned int)len, 
                (unsigned int)tmp_hdr->len);
        goto cleanup;
    } 

    /* allocate space for it */
    //printk("allocating 0x%X bytes\n", (unsigned int)len);
    cmd_hdr = (struct cmd_header *)kmalloc(len, GFP_USER);
    if(!cmd_hdr) {
        printk("error kmalloc()\n");
        goto cleanup;
    }

    /* copy it */
    memcpy(cmd_hdr, buff, len);

    /* done */
    rc = len;
    cleanup:
    return rc;
}

struct file_operations chrdev_ops = {
    .read = chrdev_read,
    .write = chrdev_write,
    .open = chrdev_open,
    .release = chrdev_release,
};

//-----------------------------------------------------------------------------
// MODULE INIT/RELEASE
//-----------------------------------------------------------------------------

static int __init 
prdbg_init(void)
{
    int rc = -1;
    
    printk("%s()\n", __func__);

    rc = register_chrdev(DEVICE_NUM_MAJOR, DEVICE_FILE_PATH, &chrdev_ops);

    if(rc < 0) {
        printk("ERROR: register_chrdev()\n");
        goto cleanup;
    }

    cleanup:

    return rc;
}

static void __exit 
prdbg_exit(void)
{
    printk("%s()\n", __func__);

    if(cmd_hdr) {
        kfree(cmd_hdr);
        cmd_hdr = 0;
    }

    unregister_chrdev(DEVICE_NUM_MAJOR, DEVICE_FILE_PATH);
}

module_init(prdbg_init);
module_exit(prdbg_exit);

MODULE_LICENSE("GPL");
