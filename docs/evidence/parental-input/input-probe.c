/* Fixed operations for the disposable UID 1003 fixture, not a product helper. */
#define _GNU_SOURCE
#include <gio/gio.h>
#include <selinux/selinux.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

#include <fontconfig/fontconfig.h>
static int data_not_code(void) {
    const char *path = "/home/parentaltest/.cache/fontconfig/elf-probe";
    gchar *contents = NULL;
    gsize size = 0;
    if (!g_file_get_contents("/usr/bin/true", &contents, &size, NULL)) return 3;
    int fd = open(path, O_CREAT | O_EXCL | O_RDWR | O_CLOEXEC, 0700);
    if (fd < 0) { perror("create-data"); return 4; }
    gsize written = 0;
    while (written < size) {
        ssize_t n = write(fd, contents + written, size - written);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return 5;
        written += n;
    }
    char *label = NULL;
    if (fgetfilecon(fd, &label) < 0) return 6;
    printf("data-label=%s bytes=%zu\n", label, size);
    gboolean correct = strstr(label, ":lyra_parental_fontcache_t:") != NULL;
    freecon(label);
    void *mapping = mmap(NULL, size, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, 0);
    int map_error = errno;
    if (mapping != MAP_FAILED) munmap(mapping, size);
    pid_t pid = fork();
    if (pid < 0) return 7;
    if (!pid) { char *args[] = {(char *)path, NULL}; execv(path, args); _exit(errno == EACCES ? 126 : 125); }
    int status = 0;
    if (waitpid(pid, &status, 0) != pid) return 8;
    printf("data-exec-status=%d executable-map-errno=%d\n", WIFEXITED(status) ? WEXITSTATUS(status) : -1, map_error);
    close(fd); g_free(contents);
    if (unlink(path)) return 9;
    return correct && mapping == MAP_FAILED && map_error == EACCES && WIFEXITED(status) && WEXITSTATUS(status) == 126 ? 0 : 10;
}

static int configure(gboolean blocked) {
    const char *path = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/lyra-test/";
    GSettings *key = g_settings_new_with_path("org.gnome.settings-daemon.plugins.media-keys.custom-keybinding", path);
    const char *command = blocked ? "/usr/bin/bash -c 'echo forbidden > /home/parentaltest/.config/dconf/shortcut-blocked'" : "/opt/lyra-parental-probe/input-probe mark-approved";
    gboolean ok = g_settings_set_string(key,"name","Lyra restricted shortcut test") &&
        g_settings_set_string(key,"command",command) &&
        g_settings_set_string(key,"binding","<Super><Shift>F9") &&
        g_settings_set_boolean(key,"enable-in-lockscreen",FALSE);
    GSettings *keys = g_settings_new("org.gnome.settings-daemon.plugins.media-keys");
    const char *paths[] = {path,NULL};
    ok = ok && g_settings_set_strv(keys,"custom-keybindings",paths);
    g_settings_sync();
    printf("shortcut blocked=%d accepted=%d\n",blocked,ok);
    g_object_unref(key);g_object_unref(keys);
    return ok ? 0 : 1;
}
int main(int argc,char **argv) {
    char *context=NULL;
    if (argc!=2 || getuid()!=1003 || geteuid()!=1003 || security_getenforce()!=1 || getcon(&context)<0) return 126;
    if (!strstr(context,":lyra_parental_probe_t:")) { freecon(context);return 126; }
    printf("uid=%u context=%s enforcing=1\n",getuid(),context);freecon(context);
    if (!strcmp(argv[1],"approved")) return configure(FALSE);
    if (!strcmp(argv[1],"blocked")) return configure(TRUE);
    if (!strcmp(argv[1],"data-not-code")) return data_not_code();
    if (!strcmp(argv[1],"mark-approved")) {
        int fd=open("/home/parentaltest/.config/dconf/shortcut-approved",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
        if(fd<0) return 2;
        int ok=write(fd,"approved\n",9)==9;close(fd);return ok?0:3;
    }
    if (!strcmp(argv[1],"fonts")) {
        if(!FcInit()) return 4;
        FcCache *cache=FcDirCacheRead((const FcChar8 *)"/usr/share/fonts/truetype",FcTrue,NULL);
        if(!cache) return 5;
        int count=FcCacheNumFont(cache);
        printf("fontcache fonts=%d dir=%s\n",count,FcCacheDir(cache));
        FcDirCacheUnload(cache);FcFini();return count>0?0:6;
    }
    if (!strcmp(argv[1],"keyboard")) {
        GSettings *settings=g_settings_new("org.gnome.desktop.input-sources");
        GVariant *sources=g_settings_get_value(settings,"sources");
        gchar *value=g_variant_print(sources,TRUE);
        printf("keyboard-sources=%s\n",value);
        int result=g_variant_n_children(sources)>0?0:7;
        g_free(value);g_variant_unref(sources);g_object_unref(settings);return result;
    }
    return 64;
}
