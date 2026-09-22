#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/mman.h>
int main(int argc, char **argv) {
 char context[256]={0};
 int fd=open("/proc/self/attr/current",O_RDONLY);
 if(fd<0 || read(fd,context,sizeof(context)-1)<0) return 90;
 close(fd);
 printf("uid=%d context=%s\n",getuid(),context);fflush(stdout);
 if(argc<2) return 0;
 if(!strcmp(argv[1],"--anon")) {
  void *p=mmap(NULL,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
  if(p==MAP_FAILED) return 95;
  int rc=mprotect(p,4096,PROT_READ|PROT_EXEC),e=errno;
  munmap(p,4096);
  if(rc<0){printf("mprotect_errno=%d\n",e);return e==EACCES?126:96;}
  return 0;
 }
 if(!strcmp(argv[1],"--map")) {
  if(argc!=3) return 91;
  fd=open(argv[2],O_RDONLY); if(fd<0) {perror("open");return 92;}
  void *p=mmap(NULL,4096,PROT_READ|PROT_EXEC,MAP_PRIVATE,fd,0);
  int e=errno;close(fd);
  if(p==MAP_FAILED){printf("mmap_errno=%d\n",e);return e==EACCES?126:93;}
  munmap(p,4096);return 0;
 }
 execv(argv[1],argv+1);int e=errno;
 printf("exec_errno=%d\n",e);return e==EACCES?126:94;
}
