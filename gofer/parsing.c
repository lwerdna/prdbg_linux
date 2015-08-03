#include <string.h>
#include <stdio.h>

/* convert 'A' -> 0x0A */
int parse_nib(char *str, unsigned int *result)
{
    int rc = 0;

    char c = *str;

    if(c>='0' && c<='9') {
        *result = c-'0';
    }
    else if(c>='a' && c<='f') {
        *result = 10 + (c-'a');
    }
    else if(c>='A' && c<='F') {
        *result = 10 + (c-'A');
    }
    else {
        rc = -1;
    }

    return rc;
}

/* convert 'AA' -> 0xAA */
int parse_byte(char *str, unsigned char *byte)
{
    int rc = -1;
    unsigned int nA, nB;

    if(!parse_nib(str, &nA) && !parse_nib(str+1, &nB)) {
        *byte = (nA<<4)|nB;
        rc = 0;
    }

    return rc;
}

/* convert 'AA:BB:CC:DD:EE:FF' -> "\xAA\xBB\xCC\xDD\xEE\xFF" */
int parse_mac(char *mac, unsigned char *bytes)
{
    int i;
    int rc = -1;
    int loc_seps[5] = {2,5,8,11,14};
    int loc_bytes[6] = {0,3,6,9,12,15};

    if(strlen(mac) != (2*6 + 5)) {
        printf("ERROR: expected 17, but strlen(mac)==%d\n", strlen(mac));
        goto cleanup;
    }

    for(i=0; i<5; ++i) {
        char *x = mac + loc_seps[i];

        if(*x != ':') {
            printf("ERROR: mac[%d] was not a colon\n", loc_seps[i]);
            goto cleanup;
        }

        *x = '\0';
    }
   
    for(i=0; i<6; ++i) {
        if(parse_byte(mac + loc_bytes[i], bytes+i)) {
            printf("ERROR: mac[%d] was not a valid byte\n", loc_bytes[i]);
            goto cleanup;
        }
    }

    rc = 0;
 
    cleanup:
    return rc;

}

/* convert "DEADBEEF" -> 0xDEADBEEF */
int parse_addr(char *hex, unsigned long *result)
{
    int rc = -1;
   
    unsigned int temp;

    /* allow '0x' prefix */
    if(hex[0]=='0' && (hex[1]=='x' || hex[1]=='X')) {
        hex += 2;
    }


    *result = 0;
    while(*hex) {
        if(parse_nib(hex, &temp)) {
            goto cleanup;
        }

        *result = (*result << 4) | temp;
        hex++;
    }

    rc = 0;
    cleanup:
    return rc;
}

/* convert "DEADBEEF" -> 0xDEADBEEF */
int parse_uint(char *hex, unsigned int *result)
{
    int rc = -1;
    
    unsigned int temp;

    /* allow '0x' prefix */
    if(hex[0]=='0' && (hex[1]=='x' || hex[1]=='X')) {
        hex += 2;
    }


    *result = 0;
    while(*hex) {
        if(parse_nib(hex, &temp)) {
            goto cleanup;
        }

        *result = (*result << 4) | temp;
        hex++;
    }

    rc = 0;
    cleanup:
    return rc;
}

/* convert ["AB", "CD", "EF", "12", ...] -> "\xAB\xCD\xEF\x12..." */
int parse_byte_list(char **str_bytes, int n_bytes, unsigned char *result)
{
    int rc = -1;
    int i = 0;

    while(i < n_bytes) {
        if(parse_byte(str_bytes[i], result+i)) {
            goto cleanup;
        }

        i++;
    }

    rc = 0;

    cleanup:
    return rc;
}

/* convert "DEADBEEF LBABE"    or 
           "DEADBEEF DEAE79AC" -> [0xDEADBEEF, 0xDEAE79AC] */
int parse_addr_range(int ac, char **av, unsigned long *addr, unsigned long *len)
{
    int rc = -1;

    if(ac >= 3) {
        if(!parse_addr(av[2], addr)) {
            rc = 0;
        }
    }

    if(ac >= 4) {
        /* allow 'L' prefix (windbg length nomenclature) */
        if(av[3][0]=='L') {
            rc = parse_addr(av[3]+1, len);
        }
        /* otherwise this parameter is an end address and
            we calculate a length manually */
        else {
            rc = -1;

            if(!parse_addr(av[3], len)) {
                if(*len > *addr) {
                    *len = *len - *addr;
                    rc = 0;
                }
            }
        }
    }
    else {
        *len = 4;
    }

    printf("parsed address: 0x%08X\n", *addr);
    printf("parsed length: 0x%08X\n", *len);

    return rc;
}

/* convert "DEADBEEF AB CD EF ..." -> [0xDEADBEEF, "\xAB\xCD\xEF..."] */
int parse_addr_bytelist(int ac, char **av, unsigned long *addr, unsigned char *bytes)
{
    int rc = -1;
    int i;

    if(ac >= 3) {
        if(parse_addr(av[2], addr)) {
            goto cleanup;
        }
    }

    if(ac >= 4 && !parse_byte_list(av+3, ac-3, bytes)) {
        rc = 0;

        printf("parsed address: 0x%08X\n", *addr);
        printf("parsed bytes: ");
        for(i=0; i<(ac-3); ++i) {
            printf("%02X ", bytes[i] & 0xFF);
        }
        printf("\n");
    }

    cleanup:
    return rc;
}

/* this parses commands like search, which take form:
    search <start_address> <end_address> <0_or_more_bytes>
*/
int parse_addr_range_bytelist(int ac, char **av, unsigned long *addr, unsigned long *len, unsigned char *bytes)
{
    int rc = -1;
    int i;

    if(parse_addr_range(ac, av, addr, len)) {
        goto cleanup;
    }

    if(parse_byte_list(av+4, ac-4, bytes)) {
        goto cleanup;
    }

    rc = 0;
    cleanup:
    return rc;
}

