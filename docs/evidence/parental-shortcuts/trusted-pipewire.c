/* Fixed native PipeWire server entries for the disposable VM only. */
#define _GNU_SOURCE
#include <selinux/selinux.h>
#include <selinux/context.h>
#include <sys/auxv.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <sys/stat.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#ifndef PULSE
#define CONFIG "pipewire.conf"
#else
#define CONFIG "pipewire-pulse.conf"
#endif
static void refuse(const char *why){fprintf(stderr,"trusted-pipewire refused: %s\n",why);exit(126);}
static void trusted(const char *name){
 char path[PATH_MAX];struct stat st;if(!realpath(name,path))refuse("missing resource");
 for(;;){if(lstat(path,&st)||st.st_uid||(st.st_mode&0022)||(!S_ISREG(st.st_mode)&&!S_ISDIR(st.st_mode)))refuse("untrusted resource");
 if(!strcmp(path,"/"))break;
 char *slash=strrchr(path,'/');if(slash==path)slash[1]=0;else *slash=0;}
}
int main(int argc,char **argv){
 (void)argv;
 if(argc!=1||getuid()!=1003||geteuid()!=getuid()||getgid()!=getegid()||security_getenforce()!=1||getauxval(AT_SECURE)!=1)refuse("arguments or identity");
 char *label=NULL;if(getcon(&label))refuse("context");context_t ctx=context_new(label);
 if(!ctx||strcmp(context_type_get(ctx),"lyra_parental_pipewire_t"))refuse("domain");
 fprintf(stderr,"trusted-pipewire context=%s config=%s AT_SECURE=1\n",label,CONFIG);context_free(ctx);freecon(label);
 trusted("/usr/bin/pipewire");trusted("/usr/share/pipewire/" CONFIG);trusted("/usr/lib64/pipewire-0.3");trusted("/usr/lib64/spa-0.2");
 /* Preserve only verified socket activation, never arbitrary configuration. */
 char pid[32],fds[32];snprintf(pid,sizeof pid,"%ld",(long)getpid());
 const char *in_pid=getenv("LISTEN_PID"),*in_fds=getenv("LISTEN_FDS");int count=0;
 if(in_pid||in_fds){
  if(!in_pid||strcmp(in_pid,pid)||!in_fds||(strcmp(in_fds,"1")&&strcmp(in_fds,"2")))refuse("socket activation");
  count=in_fds[0]-'0';
  for(int i=0;i<count;i++){
   struct sockaddr_un sa={0};socklen_t len=sizeof sa;
   if(getsockname(3+i,(struct sockaddr*)&sa,&len)||sa.sun_family!=AF_UNIX)refuse("socket descriptor");
#ifndef PULSE
   if(strcmp(sa.sun_path,"/run/user/1003/pipewire-0")&&strcmp(sa.sun_path,"/run/user/1003/pipewire-0-manager"))refuse("socket path");
#else
   if(strcmp(sa.sun_path,"/run/user/1003/pulse/native"))refuse("socket path");
#endif
  }
 }
 if(clearenv()||chdir("/"))refuse("environment");
#define SET(k,v) do{if(setenv(k,v,1))refuse("setenv");}while(0)
 SET("HOME","/home/parentaltest");SET("USER","parentaltest");SET("LOGNAME","parentaltest");SET("LANG","C.UTF-8");SET("PATH","/usr/bin:/bin");
 SET("XDG_RUNTIME_DIR","/run/user/1003");SET("DBUS_SESSION_BUS_ADDRESS","unix:path=/run/user/1003/bus");
 SET("PIPEWIRE_CONFIG_DIR","/usr/share/pipewire");SET("PIPEWIRE_CONFIG_NAME",CONFIG);
 SET("PIPEWIRE_MODULE_DIR","/usr/lib64/pipewire-0.3");SET("SPA_PLUGIN_DIR","/usr/lib64/spa-0.2");
 if(count){snprintf(fds,sizeof fds,"%d",count);SET("LISTEN_PID",pid);SET("LISTEN_FDS",fds);}
 char *const cmd[]={"/usr/bin/pipewire","-c",CONFIG,NULL};execv(cmd[0],cmd);refuse("exec");
}
