/* Fixed upstream GJS entrypoints for the disposable VM; never a general launcher. */
#define _GNU_SOURCE
#include <selinux/selinux.h>
#include <selinux/context.h>
#include <sys/auxv.h>
#include <sys/stat.h>
#include <limits.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#ifndef HELPER_KIND
#error HELPER_KIND must select one fixed service
#endif
#if HELPER_KIND == 1
#define SERVICE "org.gnome.Shell.Notifications"
#define DOMAIN "lyra_parental_notifications_t"
#elif HELPER_KIND == 2
#define SERVICE "org.gnome.ScreenSaver"
#define DOMAIN "lyra_parental_screensaver_t"
#elif HELPER_KIND == 3
#define SERVICE "org.gnome.Shell.Screencast"
#define DOMAIN "lyra_parental_screencast_t"
#define SCRIPT "/usr/libexec/lyra-gnome-screencast/" SERVICE
#else
#error Invalid HELPER_KIND
#endif
#ifndef SCRIPT
#define SCRIPT "/usr/share/gnome-shell/" SERVICE
#endif
static void refuse(const char *why) {
    fprintf(stderr,"trusted-helper %s refused: %s\n",SERVICE,why);exit(126);
}
static void trusted_path(const char *name) {
    char path[PATH_MAX]; struct stat st;
    if(!realpath(name,path))refuse("missing trusted resource");
    for(;;) {
        if(lstat(path,&st) || st.st_uid || (st.st_mode&0022) ||
           (!S_ISREG(st.st_mode) && !S_ISDIR(st.st_mode)))refuse("untrusted resource or parent");
        if(!strcmp(path,"/"))break;
        char *slash=strrchr(path,'/');if(slash==path)slash[1]=0;else *slash=0;
    }
}
int main(int argc,char **argv) {
    (void)argv;
    if(argc!=1 || getuid()!=1003 || geteuid()!=getuid() || getgid()!=getegid())refuse("identity or arguments");
    if(security_getenforce()!=1 || getauxval(AT_SECURE)!=1)refuse("enforcing secure transition required");
    char *label=NULL;if(getcon(&label))refuse("context unavailable");
    context_t ctx=context_new(label);
    if(!ctx || strcmp(context_type_get(ctx),DOMAIN))refuse("unexpected domain");
    fprintf(stderr,"trusted-helper %s context=%s AT_SECURE=1\n",SERVICE,label);
    context_free(ctx);freecon(label);
    trusted_path("/usr/bin/gjs");
    trusted_path(SCRIPT);
#if HELPER_KIND == 3
    trusted_path("/usr/libexec/lyra-gnome-screencast/gstreamerCompat.js");
#endif
    trusted_path("/usr/share/gnome-shell/" SERVICE ".src.gresource");
    trusted_path("/usr/lib64/gnome-shell");
#if HELPER_KIND == 3
    const char *cache="/run/user/1003/lyra-screencast-private";
    if(mkdir(cache,0700) && errno!=EEXIST)refuse("private cache unavailable");
    struct stat cache_stat;
    if(lstat(cache,&cache_stat) || !S_ISDIR(cache_stat.st_mode) || cache_stat.st_uid!=1003 ||
       (cache_stat.st_mode&0077))refuse("untrusted cache");
    char *cache_label=NULL;if(lgetfilecon(cache,&cache_label)<0)refuse("cache label unavailable");
    context_t cache_ctx=context_new(cache_label);
    if(!cache_ctx || strcmp(context_type_get(cache_ctx),"lyra_parental_screencast_cache_t"))refuse("untrusted cache label");
    context_free(cache_ctx);freecon(cache_label);
#endif
    if(clearenv() || chdir("/"))refuse("cannot reset execution environment");
#define SET(k,v) do {if(setenv(k,v,1))refuse("environment setup");} while(0)
    SET("HOME","/home/parentaltest");SET("USER","parentaltest");SET("LOGNAME","parentaltest");
    SET("LANG","C.UTF-8");SET("PATH","/usr/bin:/bin");
    SET("XDG_RUNTIME_DIR","/run/user/1003");SET("DBUS_SESSION_BUS_ADDRESS","unix:path=/run/user/1003/bus");
    SET("XDG_DATA_DIRS","/usr/share");SET("XDG_CONFIG_DIRS","/usr/etc/xdg:/etc/xdg");
    SET("XDG_SESSION_TYPE","wayland");SET("WAYLAND_DISPLAY","wayland-0");
    SET("GDK_BACKEND","wayland");
    SET("ORC_CODE","backup");
    SET("GJS_DISABLE_JIT","1");SET("GIO_USE_VFS","local");SET("GSK_RENDERER","cairo");
    SET("DCONF_PROFILE","/etc/dconf/profile/lyra-supervised-test");
    SET("GST_PLUGIN_PATH_1_0","");SET("GST_PLUGIN_SYSTEM_PATH_1_0","/usr/lib64/gstreamer-1.0");
#if HELPER_KIND == 3
    SET("XDG_CACHE_HOME","/run/user/1003/lyra-screencast-private");
    SET("GST_REGISTRY","/run/user/1003/lyra-screencast-private/registry.bin");
    SET("GST_REGISTRY_FORK","no");
#endif
    char *const cmd[]={"/usr/bin/gjs","-m",SCRIPT,NULL};
    execv(cmd[0],cmd);refuse("cannot execute fixed service");
}
