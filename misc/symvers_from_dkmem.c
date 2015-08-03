/* 
    build a Module.symvers by parsing the relevant data structs from a live
    linux/Android using /dev/kmem and /proc/kallsyms 

    stick this on your phone
    make sure /proc/kallsyms is reporting real symbol information 
      (if not, you may need to echo "1" > /proc/sys/kernel/kptr_restrict or make other adjustments)
    run $./symvers_from_dkmem to see if the output is ok
    run $./symvers_from_dkmem > Module.symvers 
    copy Module.symvers into your kernel source directory (on top of the previously generated one)
    compile your driver, ensuring that modpost builds foo.mod.c and __versions is made ok
*/

#include <stdio.h>

#include "helpers.h"

int 
main(int ac, char **av)
{
    int rc = -1;

    int row, i, j;
    unsigned char buf[256];
	unsigned long addr;

    int num_syms, num_crcs;
    unsigned long addr_syms, addr_syms_stop;
    unsigned long addr_crcs, addr_crcs_stop;
    
    char *sym_tables_info[] = {
        "__start___ksymtab", "__stop___ksymtab", "__start___kcrctab", "__stop___kcrctab",
        "__start___ksymtab_gpl", "__stop___ksymtab_gpl", "__start___kcrctab_gpl", "__stop___kcrctab_gpl",
        "__start___ksymtab_gpl_future", "__stop___ksymtab_gpl_future", "__start___kcrctab_gpl_future", "__stop___kcrctab_gpl_future",
        "__start___ksymtab_unused", "__stop___ksymtab_unused", "__start___kcrctab_unused", "__stop___kcrctab_unused",
        "__start___ksymtab_unused_gpl", "__stop___ksymtab_unused_gpl", "__start___kcrctab_unused_gpl", "__stop___kcrctab_unused_gpl"
    };

    for(row=0; row<5; ++row) {
    	addr_syms = get_kernel_sym(sym_tables_info[row*4+0]);
    	addr_syms_stop = get_kernel_sym(sym_tables_info[row*4+1]);
    	addr_crcs = get_kernel_sym(sym_tables_info[row*4+2]);
    	addr_crcs_stop = get_kernel_sym(sym_tables_info[row*4+3]);
    
    	if(!addr_syms || !addr_syms_stop || !addr_crcs || !addr_crcs_stop) {
            printf("ERROR: resolving symbols %s or %s or %s or %s\n",
                sym_tables_info[row*4+0], sym_tables_info[row*4+1], 
                sym_tables_info[row*4+2], sym_tables_info[row*4+3]
            );
            goto cleanup;
        }
    
        num_crcs = (addr_crcs_stop - addr_crcs)/4;	
        num_syms = (addr_syms_stop - addr_syms)/8;
    
        if(num_crcs != num_syms) {
            printf("something's fucked up, %d symbols but %d crc's\n", num_crcs, num_syms);
            goto cleanup;
        }
    
        for(i=0; i<num_syms; ++i) {
            unsigned long addr_sym_name, addr_sym, crc;
    
            if(kmem_read(addr_syms + 8*i, buf, 8)) {
                printf("ERROR: kmem_read() from address 0x%X\n", addr_syms + 8*i);
                goto cleanup;
            }
    
            addr_sym = *(unsigned long *)buf;
            addr_sym_name = *(unsigned long *)(buf+4);
    
            if(kmem_read(addr_crcs + 4*i, buf, 4)) {
                printf("ERROR: kmem_read() from address 0x%X\n", addr_crcs + 4*i);
                goto cleanup;
            }
    
            crc = *(unsigned long *)buf;
    
            if(kmem_read_str(addr_sym_name, buf, sizeof(buf))) {
                printf("ERROR: kmem_read() from address 0x%X\n", addr_sym_name);
                goto cleanup;
            }
    
            //printf("symbol %d/%d \"%s\" is at address 0x%X, has CRC 0x%X\n",
            //    i+1, num_syms, buf, addr_sym, crc);
            printf("0x%x\t%s\tdummy/path\n", crc, buf);
        }
    }

    rc = 0;
    cleanup:
	return rc;
}

