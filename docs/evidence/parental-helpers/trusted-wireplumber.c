/* Disposable VM experiment, no setuid or capabilities. A mandatory SELinux
 * transition isolates the payload from callers that can choose arguments/env. */
#define _GNU_SOURCE
#include <ftw.h>
#include <selinux/selinux.h>
#include <selinux/context.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void refuse(const char *why) {
    fprintf(stderr, "trusted-wireplumber fixture refused: %s\n", why);
    exit(126);
}
static int trusted(const char *path, const struct stat *st, int kind,
                   struct FTW *where) {
    (void)where;
    if ((kind != FTW_F && kind != FTW_D) || st->st_uid ||
        (st->st_mode & 0022) || (!S_ISREG(st->st_mode) && !S_ISDIR(st->st_mode))) {
        fprintf(stderr, "untrusted file: %s\n", path);
        return 1;
    }
    return 0;
}
int main(int argc, char **argv) {
    (void)argv;
    if (argc != 1) refuse("arguments are not accepted");
    if (getuid() != 1003 || geteuid() != getuid() || getgid() != getegid())
        refuse("not the disposable account");
    if (is_selinux_enabled() != 1 || security_getenforce() != 1)
        refuse("SELinux is not enforcing");
    char *label = NULL;
    if (getcon(&label)) refuse("cannot read context");
    context_t context = context_new(label);
    const char *type = context ? context_type_get(context) : NULL;
    if (!type || strcmp(type, "lyra_parental_wireplumber_t"))
        refuse("unexpected domain");
    fprintf(stderr, "trusted-wireplumber fixture: context=%s\n", label);
    context_free(context); freecon(label);
    const char *trees[] = {"/usr/share/wireplumber", "/usr/lib64/wireplumber-0.5",
                          "/usr/share/pipewire", NULL};
    for (int i = 0; trees[i]; i++)
        if (nftw(trees[i], trusted, 16, FTW_PHYS)) refuse("untrusted configuration tree");
    if (clearenv()) refuse("cannot clear environment");
#define SET(k,v) do { if (setenv(k,v,1)) refuse("cannot set environment"); } while (0)
    SET("HOME", "/home/parentaltest"); SET("USER", "parentaltest");
    SET("LOGNAME", "parentaltest"); SET("LANG", "C.UTF-8");
    SET("PATH", "/usr/bin:/bin"); SET("GIO_USE_VFS", "local");
    SET("XDG_RUNTIME_DIR", "/run/user/1003");
    SET("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1003/bus");
    SET("XDG_DATA_DIRS", "/usr/share"); SET("XDG_CONFIG_DIRS", "/usr/etc/xdg:/etc/xdg");
    SET("WIREPLUMBER_CONFIG_DIR", "/usr/share/wireplumber");
    SET("WIREPLUMBER_DATA_DIR", "/usr/share/wireplumber");
    SET("WIREPLUMBER_MODULE_DIR", "/usr/lib64/wireplumber-0.5");
    SET("PIPEWIRE_CONFIG_DIR", "/usr/share/pipewire");
    SET("PIPEWIRE_CONFIG_NAME", "client.conf");
    SET("PIPEWIRE_MODULE_DIR", "/usr/lib64/pipewire-0.3");
    SET("SPA_PLUGIN_DIR", "/usr/lib64/spa-0.2");
    /* Lua's environment-dependent package paths are also reset. */
    SET("LUA_PATH", "/usr/share/wireplumber/scripts/lib/?.lua");
    SET("LUA_CPATH", "");
    if (chdir("/")) refuse("cannot enter trusted working directory");
    char *const command[] = {"/usr/bin/wireplumber", "-c", "wireplumber.conf",
                            "-p", "main", NULL};
    execv(command[0], command);
    refuse("cannot execute payload");
}
