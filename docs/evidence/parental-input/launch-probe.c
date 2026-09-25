/* Fixed Shell-domain launch cases for the disposable VM; not installed in product. */
#define _POSIX_C_SOURCE 200809L
#include <selinux/selinux.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv) {
 char *context=NULL;
 if(argc!=2 || getuid()!=1003 || geteuid()!=1003 || security_getenforce()!=1 || getcon(&context)<0) return 126;
 int correct=strstr(context,":lyra_parental_shell_t:")!=NULL;
 printf("launcher-boundary uid=%u context=%s\n",getuid(),context);freecon(context);fflush(stdout);
 if(!correct)return 126;
 const char *helper="/usr/libexec/gio-launch-desktop";
 if(!strcmp(argv[1],"approved"))execl(helper,helper,"/opt/lyra-parental-probe/probe",(char*)NULL);
 else if(!strcmp(argv[1],"anonymous"))execl(helper,helper,"/opt/lyra-parental-probe/probe","--anon",(char*)NULL);
 else if(!strcmp(argv[1],"shell"))execl(helper,helper,"/usr/bin/bash","-c","true",(char*)NULL);
 else if(!strcmp(argv[1],"python"))execl(helper,helper,"/usr/bin/python3","-c","print(42)",(char*)NULL);
 else if(!strcmp(argv[1],"copy"))execl(helper,helper,"/home/parentaltest/copied-true",(char*)NULL);
 else if(!strcmp(argv[1],"loader"))execl(helper,helper,"/usr/lib64/ld-linux-x86-64.so.2","/home/parentaltest/copied-true",(char*)NULL);
 return 125;
}
