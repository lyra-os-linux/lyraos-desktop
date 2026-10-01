/* VM-only cron payload: record identity, then keep a job alive. */
#include <stdio.h>
#include <unistd.h>
#include <time.h>
int main(int argc,char **argv) {
 if(argc!=2)return 90;
 FILE *f=fopen(argv[1],"a");if(!f)return 91;
 if(fprintf(f,"%u %u %lld\n",(unsigned)getuid(),(unsigned)getpid(),(long long)time(NULL))<0)return 92;
 if(fclose(f))return 93;
 sleep(1800);return 0;
}
