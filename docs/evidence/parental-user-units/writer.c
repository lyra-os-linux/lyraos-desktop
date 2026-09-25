#include <sys/stat.h>
#include <sys/xattr.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
int main(int argc,char **argv) {
 if(argc!=4) return 90;
 char ctx[256]={0},label[256]={0};int fd=open("/proc/self/attr/current",O_RDONLY);
 if(fd<0 || read(fd,ctx,sizeof(ctx)-1)<0)return 91;
 close(fd);printf("uid=%d context=%s\n",getuid(),ctx);
 if(mkdir(argv[1],0700)<0 && errno!=EEXIST){perror("mkdir");return 92;}
 int dir=open(argv[1],O_RDONLY|O_DIRECTORY|O_NOFOLLOW);if(dir<0)return 93;
 fd=openat(dir,argv[2],O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);close(dir);
 if(fd<0){perror("create");return 94;}
 const char *head="[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=";
 if(dprintf(fd,"%s%s\n",head,argv[3])<0 || fsync(fd)<0)return 95;
 if(fgetxattr(fd,"security.selinux",label,sizeof(label)-1)<0)return 96;
 close(fd);printf("label=%s\n",label);return 0;
}
