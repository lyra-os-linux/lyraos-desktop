/* Stream lifecycle in the disposable VM. Does not qualify physical speakers. */
#include <pulse/simple.h>
#include <pulse/error.h>
#include <selinux/selinux.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(void) {
    char *label = NULL;
    if (getuid()!=1003 || geteuid()!=1003 || security_getenforce()!=1 || getcon(&label)) return 126;
    if (!strstr(label, ":lyra_parental_probe_t:")) return 126;
    printf("context=%s\n",label);freecon(label);
    const pa_sample_spec spec = {.format=PA_SAMPLE_S16LE,.rate=48000,.channels=2};
    int error=0;
    pa_simple *stream=pa_simple_new("unix:/run/user/1003/pulse/native",
        "Lyra restricted audio probe",PA_STREAM_PLAYBACK,NULL,"Silent VM fixture",
        &spec,NULL,NULL,&error);
    if (!stream) { fprintf(stderr,"connect: %s\n",pa_strerror(error));return 1; }
    int16_t silence[4800*2]={0};
    int written=pa_simple_write(stream,silence,sizeof silence,&error);
    int drained=written<0 ? -1 : pa_simple_drain(stream,&error);
    if(written<0 || drained<0) fprintf(stderr,"stream: %s\n",pa_strerror(error));
    printf("rate=48000 channels=2 bytes=%zu written=%d drained=%d\n",sizeof silence,written,drained);
    pa_simple_free(stream);
    return written==0 && drained==0 ? 0 : 2;
}
