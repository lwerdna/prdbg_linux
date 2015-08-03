int parse_nib(char *str, unsigned int *result);
int parse_byte(char *str, unsigned char *byte);
int parse_mac(char *mac, unsigned char *bytes);

int parse_uint(char *hex, unsigned int *result);
int parse_ulonglong(char *hex, unsigned long long *result);
int parse_byte_list(char **str_bytes, int n_bytes, unsigned char *result);
int parse_addr_range(int ac, char **av, unsigned long *addr, unsigned long *len);
int parse_bytelist(int ac, char **av, unsigned char *bytes);
int parse_addr_bytelist(int ac, char **av, unsigned long *addr, unsigned char *bytes);
int parse_addr_range_bytelist(int ac, char **av, unsigned long *addr, unsigned long *len, unsigned char *bytes);

