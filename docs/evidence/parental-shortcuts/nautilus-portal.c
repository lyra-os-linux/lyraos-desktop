/* VM-only D-Bus entry. Keep GTK drawing out of executable-memory/JIT paths. */
#define _GNU_SOURCE
#include <selinux/selinux.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1 || getuid()!=geteuid())return 126;
    if(getuid()==1003) {
        char *label=NULL;
        if(security_getenforce()!=1 || getcon(&label))return 126;
        if(!strstr(label,":lyra_parental_probe_t:"))return 126;
        freecon(label);
        if(setenv("GSK_RENDERER","cairo",1))return 126;
    }
    char *const command[]={"/usr/bin/nautilus","--gapplication-service",NULL};
    execv(command[0],command);perror("nautilus-portal");return 126;
}
