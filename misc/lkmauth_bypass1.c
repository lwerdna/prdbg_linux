/*  patch out the Samsung KNOX/TIMA/LKMAUTH check in insmod for a 
      Note 4 (SM-N910L) Android 4.4.4

 (this may work on other devices)

this patch relies on logic that skips lkmauth when lkmauth_bootmode is set:

#ifdef TIMA_LKM_AUTH_ENABLED
	if (lkmauth_bootmode != BOOTMODE_RECOVERY &&
	    lkmauth(info->hdr, info->len) != RET_LKMAUTH_SUCCESS) {
		pr_err
		    ("TIMA: lkmauth--unable to load kernel module; module len is %lu.\n",
		     info->len);
		return -ENOEXEC;
	}
#endif

load_module+0x90: 3a0004bf 	bcc	c0086194 <.text+0x1314>
load_module+0x94: e59faf88 	ldr	sl, [pc, #3976]	; c0085e24 <.text+0xfa4>
load_module+0x98: e59a2004 	ldr	r2, [sl, #4]
load_module+0x9C: e3520002 	cmp	r2, #2	; 0x2 <-- compare to BOOTMODE_RECOVERY
load_module+0xA0: 0a0000a4 	beq	kernel!load_module+0x338 <.text+0x2b8> <-- PATCH PATCH!
load_module+0xA4: e24b5044 	sub	r5, fp, #68	; 0x44
load_module+0xA8: e59f1f78 	ldr	r1, [pc, #3960]	; c0085e28 <.text+0xfa8>
load_module+0xAC: e3a02010 	mov	r2, #16	; 0x10
*/

#include <stdio.h>

#include "helpers.h"

int 
main(int ac, char **av)
{
    #define WINDOW 256
    int rc = -1;
    int i;
    unsigned char buf[WINDOW];
	unsigned long addr;

    printf("lkmauth bypass\n");

	addr = get_kernel_sym("load_module");
	if(!addr) {
        printf("ERROR: get_kernel_sym(\"load_module\")\n");
        goto cleanup;
    }
	
    if(kmem_read(addr, buf, WINDOW)) {
        printf("ERROR: kmem_read()\n");
        goto cleanup;
    }
    
    printf("scanning for check\n");
    for(i=0; i<(WINDOW-8); i += 4) {
        // e3520002 	cmp	r2, #2	; 0x2
        // 0a0000a4 	beq	kernel!load_module+0x338 <.text+0x2b8>    
        if(!memcmp(buf + i, "\x02\x00\x52\xe3", 4) && buf[i+7] == 0x0A) {
            printf("detected unpatched version at load_module+0x%X, patching...\n", i);
            kmem_write(addr + i + 7, "\xEA", 1);
            break;
        }

        if(!memcmp(buf + i, "\x02\x00\x52\xe3", 4) && buf[i+7] == 0xEA) {
            printf("detected patched version at load_module+0x%X, unpatching...\n", i);
            kmem_write(addr + i + 7, "\x0A", 1);
            break;
        }
    }

    rc = 0;
    cleanup:
	return rc;
}

