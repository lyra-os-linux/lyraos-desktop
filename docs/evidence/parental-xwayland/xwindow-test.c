#define _POSIX_C_SOURCE 200809L
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <selinux/selinux.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
int main(void) {
    char *context=NULL;
    if (getcon(&context)<0 || !strstr(context,":lyra_parental_probe_t:")) return 2;
    printf("context=%s\n",context);freecon(context);
    Display *display=XOpenDisplay(NULL);
    if (!display) return 3;
    Window window=XCreateSimpleWindow(display,DefaultRootWindow(display),100,100,400,240,0,0,0x35679a);
    XStoreName(display,window,"Lyra restricted X11 window");
    XMapWindow(display,window);XFlush(display);
    Atom extents=XInternAtom(display,"_NET_FRAME_EXTENTS",False);
    int passed=0;
    for (int attempt=0;attempt<80 && !passed;attempt++) {
        Atom actual;int format;unsigned long count,remaining;unsigned char *data=NULL;
        int status=XGetWindowProperty(display,window,extents,0,4,False,XA_CARDINAL,&actual,&format,&count,&remaining,&data);
        if (status==Success && actual==XA_CARDINAL && format==32 && count==4) {
            unsigned long *values=(unsigned long*)data;
            if (values[2]>0) {
                printf("framed-window=%lu extents=%lu,%lu,%lu,%lu\n",window,values[0],values[1],values[2],values[3]);passed=1;
            }
        }
        if(data)XFree(data);
        struct timespec delay={.tv_nsec=100000000};nanosleep(&delay,NULL);
    }
    XDestroyWindow(display,window);XCloseDisplay(display);
    if(!passed)fprintf(stderr,"No server-side frame extents within eight seconds\n");
    return passed?0:4;
}
