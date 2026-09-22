#include <systemd/sd-bus.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
int main(int argc,char **argv) {
 if(argc!=2) return 90;
 char context[256]={0};int fd=open("/proc/self/attr/current",O_RDONLY);
 if(fd<0 || read(fd,context,sizeof(context)-1)<0) return 91;
 close(fd);printf("uid=%d context=%s name=%s\n",getuid(),context,argv[1]);fflush(stdout);
 sd_bus *bus=NULL;int r=sd_bus_default_user(&bus);
 if(r<0) {fprintf(stderr,"connect=%d\n",r);return 92;}
 r=sd_bus_request_name(bus,argv[1],0);
 if(r<0) {fprintf(stderr,"request=%d\n",r);sd_bus_unref(bus);return 93;}
 struct timespec start,now;clock_gettime(CLOCK_MONOTONIC,&start);
 do {
  r=sd_bus_process(bus,NULL);if(r<0)break;
  if(r==0)sd_bus_wait(bus,1000000);
  clock_gettime(CLOCK_MONOTONIC,&now);
 } while(now.tv_sec-start.tv_sec<20);
 sd_bus_flush_close_unref(bus);return r<0?94:0;
}
