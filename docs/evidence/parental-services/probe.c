#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/xattr.h>
int main(int argc, char **argv) {
 char context[256]={0};
 int fd=open("/proc/self/attr/current",O_RDONLY);
 if(fd<0 || read(fd,context,sizeof(context)-1)<0) return 90;
 close(fd);
 printf("uid=%d context=%s\n",getuid(),context);fflush(stdout);
 if(argc<2) return 0;
 if(!strcmp(argv[1],"--memfd")) {
  if(argc!=3) return 105;
  int in=open(argv[2],O_RDONLY),out=memfd_create("lyra-write-exec",0);
  if(in<0 || out<0) return 106;
  char buf[8192],label[256]={0};ssize_t n;long total=0;
  while((n=read(in,buf,sizeof(buf)))>0) {
   for(ssize_t off=0;off<n;) {
    ssize_t w=write(out,buf+off,(size_t)(n-off));
    if(w<=0) return 107;
    off+=w;
   }
   total+=n;
  }
  if(n<0 || fgetxattr(out,"security.selinux",label,sizeof(label)-1)<0) return 108;
  close(in);
  void *m=mmap(NULL,4096,PROT_READ|PROT_EXEC,MAP_PRIVATE,out,0);
  int map_errno=m==MAP_FAILED?errno:0;
  if(m!=MAP_FAILED) munmap(m,4096);
  printf("written=%ld label=%s memfd_map_errno=%d\n",total,label,map_errno);fflush(stdout);
  char *child[]={"memfd-fixture",NULL},*env[]={NULL};
  fexecve(out,child,env);int exec_errno=errno;close(out);
  printf("memfd_exec_errno=%d\n",exec_errno);
  return map_errno==EACCES && exec_errno==EACCES?126:109;
 }
 if(!strcmp(argv[1],"--copy-exec")) {
  if(argc!=4) return 97;
  int in=open(argv[2],O_RDONLY),out=-1;
  if(in<0) return 98;
  out=open(argv[3],O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0700);
  if(out<0){perror("create");close(in);return 99;}
  char buffer[8192],label[256]={0};ssize_t n;long total=0;
  while((n=read(in,buffer,sizeof(buffer)))>0) {
   for(ssize_t offset=0;offset<n;) {
    ssize_t w=write(out,buffer+offset,(size_t)(n-offset));
    if(w<=0){close(in);close(out);return 100;}offset+=w;
   }
   total+=n;
  }
  if(n<0 || fsync(out)<0){close(in);close(out);return 101;}
  if(fgetxattr(out,"security.selinux",label,sizeof(label)-1)<0){close(in);close(out);return 102;}
  close(in);if(close(out)<0)return 103;
  printf("written=%ld label=%s\n",total,label);fflush(stdout);
  char *child[]={argv[3],NULL};execv(argv[3],child);int e=errno;
  printf("created_exec_errno=%d\n",e);return e==EACCES?126:104;
 }
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
