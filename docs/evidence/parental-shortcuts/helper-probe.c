/* Native fixed-method client in the restricted account, never a general D-Bus tool. */
#define _GNU_SOURCE
#include <gio/gio.h>
#include <selinux/selinux.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <errno.h>
static GVariant *call(GDBusConnection *bus,const char *name,const char *path,const char *iface,const char *method,GVariant *args) {
    GError *error=NULL;
    GVariant *reply=g_dbus_connection_call_sync(bus,name,path,iface,method,args,NULL,G_DBUS_CALL_FLAGS_NONE,15000,NULL,&error);
    if(!reply){fprintf(stderr,"%s: %s\n",method,error->message);g_error_free(error);return NULL;}
    gchar *text=g_variant_print(reply,TRUE);printf("%s=%s\n",method,text);g_free(text);return reply;
}
static int notifications(GDBusConnection *bus) {
    const char *name="org.gnome.Shell.Notifications",*path="/org/freedesktop/Notifications",*iface="org.freedesktop.Notifications";
    GVariant *reply=call(bus,name,path,iface,"GetCapabilities",NULL);if(!reply)return 2;g_variant_unref(reply);
    reply=call(bus,name,path,iface,"GetServerInformation",NULL);if(!reply)return 3;g_variant_unref(reply);
    GVariantBuilder hints;g_variant_builder_init(&hints,G_VARIANT_TYPE_VARDICT);
    g_variant_builder_add(&hints,"{sv}","transient",g_variant_new_boolean(TRUE));
    g_variant_builder_add(&hints,"{sv}","urgency",g_variant_new_byte(0));
    reply=call(bus,name,path,iface,"Notify",g_variant_new("(susss@asa{sv}i)","Lyra fixture",0u,"","Restricted notification","Disposable account test",g_variant_new_strv(NULL,0),&hints,0));
    if(!reply)return 4;
    guint id=0;g_variant_get(reply,"(u)",&id);g_variant_unref(reply);if(!id)return 5;
    GError *error=NULL;
    GDBusConnection *other=g_dbus_connection_new_for_address_sync("unix:path=/run/user/1003/bus",G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT|G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,NULL,NULL,&error);
    if(!other)return 6;
    reply=g_dbus_connection_call_sync(other,name,path,iface,"CloseNotification",g_variant_new("(u)",id),NULL,G_DBUS_CALL_FLAGS_NONE,5000,NULL,&error);
    gboolean denied=!reply && g_error_matches(error,G_DBUS_ERROR,G_DBUS_ERROR_INVALID_ARGS);
    printf("foreign-notification-close-denied=%d\n",denied);
    if(reply)g_variant_unref(reply);
    g_clear_error(&error);g_object_unref(other);
    reply=call(bus,name,path,iface,"CloseNotification",g_variant_new("(u)",id));if(!reply)return 7;
    g_variant_unref(reply);return denied?0:8;
}
static int boundaries(void) {
    const char *names[]={"notifications","screensaver","screencast"};
    for(unsigned i=0;i<3;i++) {
        char path[160];snprintf(path,sizeof path,"/run/user/1003/lyra-%s-memory-probe",names[i]);
        errno=0;int fd=open(path,O_RDWR|O_CLOEXEC);int error=errno;
        if(fd>=0){close(fd);return 21;}
        if(error!=EACCES)return 22;
        fd=open(path,O_RDONLY|O_CLOEXEC);if(fd<0)return 23;
        errno=0;void *map=mmap(NULL,4096,PROT_READ|PROT_EXEC,MAP_PRIVATE,fd,0);error=errno;close(fd);
        if(map!=MAP_FAILED){munmap(map,4096);return 24;}
        if(error!=EACCES)return 25;
        printf("%s private-memory write=denied execute-map=denied errno=%d\n",names[i],error);
    }
    errno=0;int fd=open("/run/user/1003/lyra-screencast-private/registry.bin",O_WRONLY|O_CLOEXEC);int error=errno;
    if(fd>=0){close(fd);return 26;}
    if(error!=EACCES)return 27;
    puts("screencast private-registry write=denied");return 0;
}
int main(int argc,char **argv) {
    char *label=NULL;
    if(argc!=2 || getuid()!=1003 || geteuid()!=1003 || security_getenforce()!=1 || getcon(&label))return 126;
    if(!strstr(label,":lyra_parental_probe_t:"))return 126;
    printf("context=%s enforcing=1\n",label);freecon(label);
    if(!strcmp(argv[1],"boundaries"))return boundaries();
    GError *error=NULL;GDBusConnection *bus=g_bus_get_sync(G_BUS_TYPE_SESSION,NULL,&error);
    if(!bus){fprintf(stderr,"bus: %s\n",error->message);return 1;}
    if(!strcmp(argv[1],"notifications"))return notifications(bus);
    GVariant *reply=NULL;
    if(!strcmp(argv[1],"screensaver")) {
        reply=call(bus,"org.gnome.ScreenSaver","/org/gnome/ScreenSaver","org.gnome.ScreenSaver","GetActive",NULL);
        if(!reply)return 9;
        gboolean active;g_variant_get(reply,"(b)",&active);g_variant_unref(reply);if(active)return 10;
        reply=call(bus,"org.gnome.ScreenSaver","/org/gnome/ScreenSaver","org.gnome.ScreenSaver","GetActiveTime",NULL);
    } else if(!strcmp(argv[1],"lock")) {
        reply=call(bus,"org.gnome.ScreenSaver","/org/gnome/ScreenSaver","org.gnome.ScreenSaver","Lock",NULL);
        if(!reply)return 12;
        g_variant_unref(reply);reply=NULL;
        gboolean active=FALSE;
        /* Lock's screen-shown reply may precede the active-state animation. */
        gint64 deadline=g_get_monotonic_time()+5*G_TIME_SPAN_SECOND;
        while(!active && g_get_monotonic_time()<deadline) {
            if(reply)g_variant_unref(reply);
            reply=call(bus,"org.gnome.ScreenSaver","/org/gnome/ScreenSaver","org.gnome.ScreenSaver","GetActive",NULL);
            if(!reply)return 13;
            g_variant_get(reply,"(b)",&active);
            if(!active)g_usleep(100000);
        }
        if(!active)return 14;
    } else if(!strcmp(argv[1],"screencast")) {
        const char *name="org.gnome.Shell.Screencast",*path="/org/gnome/Shell/Screencast",*iface="org.gnome.Shell.Screencast";
        reply=call(bus,name,path,"org.freedesktop.DBus.Properties","Get",g_variant_new("(ss)",iface,"ScreencastSupported"));
        if(!reply)return 15;
        GVariant *supported=NULL;g_variant_get(reply,"(v)",&supported);
        gboolean available=g_variant_get_boolean(supported);g_variant_unref(supported);g_variant_unref(reply);
        if(!available)return 16;
        GVariantBuilder options;g_variant_builder_init(&options,G_VARIANT_TYPE_VARDICT);
        g_variant_builder_add(&options,"{sv}","framerate",g_variant_new_int32(10));
        reply=call(bus,name,path,iface,"Screencast",g_variant_new("(sa{sv})","/run/user/1003/lyra-screencast-fixture",&options));
        if(!reply)return 17;
        gboolean recording;const char *file;g_variant_get(reply,"(b&s)",&recording,&file);
        if(!recording || !g_str_has_prefix(file,"/run/user/1003/lyra-screencast-fixture."))return 18;
        printf("recording-file=%s\n",file);g_variant_unref(reply);
        g_usleep(3000000);
        reply=call(bus,name,path,iface,"StopScreencast",NULL);
        if(!reply)return 19;
        g_variant_get(reply,"(b)",&recording);if(!recording)return 20;
    } else return 64;
    if(!reply)return 11;
    g_variant_unref(reply);g_object_unref(bus);return 0;
}
