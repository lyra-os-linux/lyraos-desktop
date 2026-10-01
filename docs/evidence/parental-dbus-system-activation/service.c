/* VM-only activation payload; normal mapping, no parental MAC claim. */
#include <systemd/sd-bus.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>
#include <time.h>
static int probe(sd_bus_message *m, void *userdata, sd_bus_error *error) {
 (void)userdata; (void)error;
 return sd_bus_reply_method_return(m,"uu",(uint32_t)getuid(),(uint32_t)getpid());
}
static const sd_bus_vtable vtable[]={
 SD_BUS_VTABLE_START(0),
 SD_BUS_METHOD("Probe","","uu",probe,SD_BUS_VTABLE_UNPRIVILEGED),
 SD_BUS_VTABLE_END
};
int main(int argc,char **argv) {
 if(argc!=2)return 90;
 sd_bus *bus=NULL;sd_bus_slot *slot=NULL;
 int r=sd_bus_default_system(&bus);
 if(r<0)return 91;
 r=sd_bus_add_object_vtable(bus,&slot,"/org/lyra/ParentalDbusFixture","org.lyra.ParentalDbusFixture",vtable,NULL);
 if(r<0)return 92;
 r=sd_bus_request_name(bus,argv[1],0);
 if(r<0){fprintf(stderr,"request_name=%d\n",r);return 93;}
 printf("name=%s uid=%u pid=%u\n",argv[1],(unsigned)getuid(),(unsigned)getpid());fflush(stdout);
 struct timespec start,now;clock_gettime(CLOCK_MONOTONIC,&start);
 do {
  r=sd_bus_process(bus,NULL);if(r<0)break;
  if(r==0)sd_bus_wait(bus,1000000);
  clock_gettime(CLOCK_MONOTONIC,&now);
 }while(now.tv_sec-start.tv_sec<300);
 sd_bus_slot_unref(slot);sd_bus_flush_close_unref(bus);return r<0?94:0;
}
