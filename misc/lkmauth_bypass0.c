/* patch out the Samsung KNOX/TIMA/LKMAUTH check on insmod for an
    ATT Galaxy S3 (SG-I747) with 4.4.2 

 (this may work on other devices)

here's the patch:

lkmauth+0x160: eb0d11cf     bl    qseecom_shutdown_app <.text+0x344744>
lkmauth+0x164: e3500000     cmp    r0, #0    ; 0x0
lkmauth+0x168: 05864004     streq    r4, [r6, #4]
lkmauth+0x16C: 0a000044     beq    lkmauth+0x284 <.text+0x124>
lkmauth+0x170: e59f0168     ldr    r0, [pc, #360]    ; lkmauth+0x2E0 <.text+0x180>
lkmauth+0x174: eb1cb7cb     bl    printk <.text+0x72df48>
lkmauth+0x178: ea000041     b    lkmauth+0x284 <.text+0x124>
lkmauth+0x17C: e5981144     ldr    r1, [r8, #324]
lkmauth+0x180: e3510000     cmp    r1, #0    ; 0x0
lkmauth+0x184: 1a000002     bne    lkmauth+0x194 <.text+0x34> <-- NOP, always fall to good case 
good_path:
lkmauth+0x188: e59f0154     ldr    r0, [pc, #340]    ; lkmauth+0x2E4 <.text+0x184>
lkmauth+0x18C: eb1cb7c5     bl    printk <.text+0x72df48>
lkmauth+0x190: ea00003c     b    lkmauth+0x288 <.text+0x128> 
bad_path:
lkmauth+0x194: e59f014c     ldr    r0, [pc, #332]    ; lkmauth+0x2E8 <.text+0x188>
lkmauth+0x198: eb1cb7c2     bl    printk <.text+0x72df48>
lkmauth+0x19C: e59f3148     ldr    r3, [pc, #328]    ; lkmauth+0x2EC <.text+0x18c>
lkmauth+0x1A0: e5930018     ldr    r0, [r3, #24]
lkmauth+0x1A4: e3500000     cmp    r0, #0    ; 0x0
lkmauth+0x1A8: 0a000008     beq    lkmauth+0x1D0 <.text+0x70>
lkmauth+0x1AC: e30810d0     movw    r1, #32976    ; 0x80d0
lkmauth+0x1B0: e3a02010     mov    r2, #16    ; 0x10

output of a successful run:

root@d2att:/data/local/tmp # insmod hello.ko                                   
insmod: init_module 'hello.ko' failed (Exec format error)
255|root@d2att:/data/local/tmp # ./lkmauth_bypass0                             
lkmauth bypass go go
lkmauth resolved to: 0xC00C7220
read 512 (0x200) bytes
scanning for check()
detected unpatched version at lkmauth+0x17C, patching...
root@d2att:/data/local/tmp # insmod hello.ko
root@d2att:/data/local/tmp # rmmod hello.ko
root@d2att:/data/local/tmp # ./lkmauth_bypass0                                 
lkmauth bypass go go
lkmauth resolved to: 0xC00C7220
read 512 (0x200) bytes
scanning for check()
detected patched version at lkmauth+0x17C, unpatching...
root@d2att:/data/local/tmp # insmod hello.ko
insmod: init_module 'hello.ko' failed (Exec format error)
255|root@d2att:/data/local/tmp #

 */

#include <stdio.h>

#include "helpers.h"

int 
main(int ac, char **av)
{
    #define WINDOW 512 
    int rc = -1, i;
    unsigned char buf[WINDOW];
    unsigned long addr;

    printf("lkmauth bypass go go\n");

	addr = get_kernel_sym("lkmauth");
	if(!addr) { printf("ERROR: get_kernel_sym(\"lkmauth\")\n"); goto cleanup; }
    printf("lkmauth resolved to: 0x%X\n", addr);
	
    if(kmem_read(addr, buf, WINDOW)) { printf("ERROR: kmem_read()\n"); goto cleanup; }
    printf("read %d (0x%X) bytes\n", WINDOW, WINDOW);
    
    printf("scanning for check\n");
    for(i=0; i<(WINDOW-12); i += 4) {
        //lkmauth+0x17C: e5981144     ldr    r1, [r8, #324]
        //lkmauth+0x180: e3510000     cmp    r1, #0    ; 0x0
        //lkmauth+0x184: 1a000002     bne    lkmauth+0x194 <.text+0x34> <-- NOP 

        if(!memcmp(buf + i, "\x44\x11\x98\xe5\x00\x00\x51\xe3", 8) && buf[i+11] == 0x1A) {
            printf("detected unpatched version at lkmauth+0x%X, patching...\n", i);
            kmem_write(addr + i + 8, "\x00\x00\x00\x00", 4);
            break;
        }

        if(!memcmp(buf + i, "\x44\x11\x98\xe5\x00\x00\x51\xe3\x00\x00\x00\x00", 12)) {
            printf("detected patched version at lkmauth+0x%X, unpatching...\n", i);
            kmem_write(addr + i + 8, "\x02\x00\x00\x1a", 4);
            break;
        }
    }

    if(i >= (WINDOW-12)) { printf("ERROR: never found patch location\n"); goto cleanup; }

    rc = 0;
    cleanup:
	return rc;
}

