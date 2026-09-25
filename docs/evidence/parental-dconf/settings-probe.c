/* Fixed operations for the disposable UID 1003 fixture, not a product helper. */
#define _GNU_SOURCE
#include <gio/gio.h>
#include <dconf/dconf.h>
#include <selinux/selinux.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static const char *keys[] = {"allow-extension-installation", "development-tools", "disable-user-extensions"};
static const gboolean expected[] = {FALSE, FALSE, TRUE};

static int protected_keys(gboolean attempt) {
    GSettings *settings = g_settings_new("org.gnome.shell");
    for (guint i = 0; i < G_N_ELEMENTS(keys); i++) {
        gboolean value = g_settings_get_boolean(settings, keys[i]);
        gboolean writable = g_settings_is_writable(settings, keys[i]);
        gboolean accepted = attempt && g_settings_set_boolean(settings, keys[i], !expected[i]);
        printf("protected key=%s value=%d writable=%d accepted=%d\n", keys[i], value, writable, accepted);
        if (value != expected[i] || writable || accepted) return 1;
    }
    g_settings_sync();
    g_object_unref(settings);
    return 0;
}

static int raw_write(void) {
    DConfClient *client = dconf_client_new();
    for (guint i = 0; i < G_N_ELEMENTS(keys); i++) {
        gchar *path = g_strconcat("/org/gnome/shell/", keys[i], NULL);
        GError *error = NULL;
        gboolean ok = dconf_client_write_sync(client, path, g_variant_new_boolean(!expected[i]), NULL, NULL, &error);
        printf("alternate-profile-write key=%s accepted=%d error=%s\n", keys[i], ok, error ? error->message : "none");
        g_clear_error(&error);
        g_free(path);
        if (!ok) return 2;
    }
    g_object_unref(client);
    return 0;
}

static int data_not_code(void) {
    const char *path = "/home/parentaltest/.config/dconf/elf-probe";
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
    gboolean correct = strstr(label, ":lyra_parental_settings_t:") != NULL;
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

int main(int argc, char **argv) {
    char *context = NULL;
    if (argc != 2 || getuid() != 1003 || getuid() != geteuid() || security_getenforce() != 1 || getcon(&context) < 0) return 126;
    if (!strstr(context, ":lyra_parental_probe_t:")) { freecon(context); return 126; }
    printf("uid=%u context=%s enforcing=1\n", getuid(), context); freecon(context);
    const char *profile = g_getenv("DCONF_PROFILE");
    gboolean raw = !strcmp(argv[1], "raw-write");
    if (!profile || strcmp(profile, raw ? "/etc/dconf/profile/lyra-supervised-raw-test" : "/etc/dconf/profile/lyra-supervised-test")) return 126;
    if (raw) return raw_write();
    if (!strcmp(argv[1], "locked")) return protected_keys(TRUE);
    if (!strcmp(argv[1], "effective")) return protected_keys(FALSE);
    if (!strcmp(argv[1], "data-not-code")) return data_not_code();
    if (!strcmp(argv[1], "system-write")) {
        const char *paths[] = {"/etc/dconf/profile/lyra-supervised-test", "/etc/dconf/db/lyra-supervised-test"};
        for (guint i = 0; i < G_N_ELEMENTS(paths); i++) {
            int fd = open(paths[i], O_WRONLY | O_CLOEXEC);
            int saved = errno;
            if (fd >= 0) { close(fd); return 11; }
            printf("system-write path=%s errno=%d\n", paths[i], saved);
            if (saved != EACCES) return 12;
        }
        return 0;
    }
    GSettings *settings = g_settings_new("org.gnome.desktop.interface");
    int result = 126;
    if (!strcmp(argv[1], "write")) {
        gboolean ok = g_settings_set_string(settings, "clock-format", "12h");
        g_settings_sync();
        printf("preference-write accepted=%d\n", ok);
        result = ok ? 0 : 13;
    } else if (!strcmp(argv[1], "read")) {
        gchar *value = g_settings_get_string(settings, "clock-format");
        printf("preference-read clock-format=%s\n", value);
        result = strcmp(value, "12h") ? 14 : 0;
        g_free(value);
    }
    g_object_unref(settings);
    return result;
}
