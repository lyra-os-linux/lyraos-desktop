/* Disposable VM probe: exercise SCM_RIGHTS across real SELinux transitions. */
#define _GNU_SOURCE
#include <sys/socket.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <selinux/selinux.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
static void fail(const char *s) { perror(s); exit(125); }
int main(int argc,char **argv) {
 char *context=NULL;
 if (security_getenforce()!=1 || getcon(&context)<0) fail("context");
 printf("uid=%u context=%s enforcing=1\n",getuid(),context);freecon(context);fflush(stdout);
 if(argc==3 && !strcmp(argv[1],"receive")) {
  int sock=atoi(argv[2]);char c=0;char control[CMSG_SPACE(sizeof(int))]={0};
  struct iovec iov={&c,1};struct msghdr msg={0};
  msg.msg_iov=&iov;msg.msg_iovlen=1;msg.msg_control=control;msg.msg_controllen=sizeof(control);
  if(recvmsg(sock,&msg,0)!=1)fail("recvmsg");
  struct cmsghdr *cm=CMSG_FIRSTHDR(&msg);
  if(!cm || cm->cmsg_level!=SOL_SOCKET || cm->cmsg_type!=SCM_RIGHTS) {
   printf("descriptor denied flags=%d\n",msg.msg_flags);return 126;
  }
  int fd;memcpy(&fd,CMSG_DATA(cm),sizeof(fd));char bytes[7]={0};
  if(pread(fd,bytes,6,0)!=6 || strcmp(bytes,"keymap"))fail("read data");
  errno=0;ssize_t written=pwrite(fd,"X",1,0);int write_errno=errno;
  errno=0;void *exec=mmap(NULL,4096,PROT_READ|PROT_EXEC,MAP_PRIVATE,fd,0);int exec_errno=errno;
  printf("descriptor received data=%s write=%zd errno=%d executable_map=%s errno=%d\n",bytes,written,write_errno,exec==MAP_FAILED?"denied":"ALLOWED",exec_errno);
  close(fd);close(sock);
  return written==-1 && exec==MAP_FAILED ? 0:1;
 }
 if(argc!=2) return 125;
 int pair[2];if(socketpair(AF_UNIX,SOCK_STREAM,0,pair))fail("socketpair");
 int fd=memfd_create("mutter-shared",MFD_ALLOW_SEALING|MFD_CLOEXEC);
 if(fd<0 || ftruncate(fd,4096) || pwrite(fd,"keymap",6,0)!=6)fail("memfd");
 if(!strcmp(argv[1],"sealed-rw") || !strcmp(argv[1],"sealed-ro"))
  if(fcntl(fd,F_ADD_SEALS,F_SEAL_SHRINK|F_SEAL_GROW|F_SEAL_WRITE)<0)fail("seals");
 if(!strcmp(argv[1],"sealed-ro")) {
  char path[80];snprintf(path,sizeof(path),"/proc/self/fd/%d",fd);
  int ro=open(path,O_RDONLY|O_CLOEXEC);if(ro<0)fail("reopen readonly");close(fd);fd=ro;
 }
 char *label=NULL;if(fgetfilecon(fd,&label)<0)fail("file context");
 printf("mode=%s label=%s flags=%d seals=%d\n",argv[1],label,fcntl(fd,F_GETFL),fcntl(fd,F_GET_SEALS));freecon(label);fflush(stdout);
 int output[2];if(pipe(output))fail("pipe");
 pid_t child=fork();if(child<0)fail("fork");
 if(!child) {
  close(output[0]);if(dup2(output[1],1)<0 || dup2(output[1],2)<0)fail("dup2");close(output[1]);
  close(pair[0]);char number[32];snprintf(number,sizeof(number),"%d",pair[1]);
  execl("/usr/bin/Xwayland","Xwayland","receive",number,NULL);fail("exec receiver");
 }
 close(output[1]);close(pair[1]);char c='K';char control[CMSG_SPACE(sizeof(int))]={0};struct iovec iov={&c,1};struct msghdr msg={0};
 msg.msg_iov=&iov;msg.msg_iovlen=1;msg.msg_control=control;msg.msg_controllen=sizeof(control);
 struct cmsghdr *cm=CMSG_FIRSTHDR(&msg);cm->cmsg_level=SOL_SOCKET;cm->cmsg_type=SCM_RIGHTS;cm->cmsg_len=CMSG_LEN(sizeof(int));memcpy(CMSG_DATA(cm),&fd,sizeof(fd));
 if(sendmsg(pair[0],&msg,0)!=1)fail("sendmsg");
 close(fd);close(pair[0]);
 char line[4096];ssize_t got;while((got=read(output[0],line,sizeof(line)))>0)
  if(fwrite(line,1,(size_t)got,stdout)!=(size_t)got)fail("stdout");
 close(output[0]);
 int status;if(waitpid(child,&status,0)<0)fail("waitpid");
 int expected=!strcmp(argv[1],"sealed-ro")?0:126;
 printf("receiver=%d expected=%d\n",WIFEXITED(status)?WEXITSTATUS(status):-1,expected);
 return WIFEXITED(status) && WEXITSTATUS(status)==expected ? 0:1;
}
