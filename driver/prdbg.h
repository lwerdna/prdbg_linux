
/* these are defines for the character device for i/o from user/kernel */

#define DEVICE_FILE_PATH "/dev/prdbg"

/* since in <kernel source>/Documentation/devices.txt 260 (OSD SCSI device
    was the last one listed */
#define DEVICE_NUM_MAJOR 500
/* doesn't matter */
#define DEVICE_NUM_MINOR 1

struct cmd_header
{
    int cmd_id;
    int len; /* of total data, including this header */
};

/* list of commands */

/* memory read/write */
#define CMD_MEM_READ            0
#define CMD_MEM_WRITE           1

/* memory write with considerations for overwriting live code
    (flush instruction cache, etc.) */
#define CMD_MEM_WRITE_CODE      2

/* allocate/free */
#define CMD_VMALLOC             10
#define CMD_VFREE               11

struct cmd_mem_generic
{
    struct cmd_header hdr;

    void *addr;
    unsigned int bytes_n;
    unsigned char bytes[256];
};

/* call arbitrary void (*func)(void) */
#define CMD_CALL                20

/* call test */
#define CMD_CALL_TEST           30

struct cmd_execute_mem
{
    struct cmd_header hdr;

    void *addr;
    void *arg;
};



