/* Disposable SELinux/GNOME integration probe. NOT a production launcher.
 * No setuid/capabilities. Entry transition and executable trust are enforced
 * by the temporary VM policy. No caller-provided command or arguments.
 */
#define _GNU_SOURCE
#include <ctype.h>
#include <fcntl.h>
#include <gio/gio.h>
#include <pwd.h>
#include <selinux/selinux.h>
#include <selinux/context.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/auxv.h>
#include <unistd.h>

static void refuse(const char *why) {
    fprintf(stderr, "trusted-shell fixture refused: %s\n", why);
    exit(126);
}

static void trusted_regular(const char *path) {
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    struct stat st;
    if (fd < 0 || fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid != 0 ||
        (st.st_mode & (S_IWGRP | S_IWOTH)))
        refuse("missing or untrusted administrator configuration");
    close(fd);
}

static int locale_valid(const char *value) {
    if (!value || !*value || strlen(value) > 128) return 0;
    for (const unsigned char *p = (const unsigned char *)value; *p; p++)
        if (!isalnum(*p) && !strchr("_.@-", *p)) return 0;
    return 1;
}

int main(int argc, char **argv) {
    (void)argv;
    if (argc != 1) refuse("arguments are not accepted");
    if (!getuid() || getuid() != geteuid() || getgid() != getegid())
        refuse("unexpected credentials");
    if (is_selinux_enabled() != 1 || security_getenforce() != 1)
        refuse("SELinux is not enforcing");
    char *label = NULL;
    if (getcon(&label) < 0) refuse("cannot read context");
    context_t context = context_new(label);
    const char *type = context ? context_type_get(context) : NULL;
    if (!type || strcmp(type, "lyra_parental_shell_t"))
        refuse("not in trusted shell domain");
    fprintf(stderr, "trusted-shell fixture: uid=%lu context=%s AT_SECURE=%lu\n",
            (unsigned long)getuid(), label, getauxval(AT_SECURE));
    context_free(context);
    freecon(label);
    trusted_regular("/etc/dconf/profile/lyra-supervised-test");
    trusted_regular("/etc/dconf/db/lyra-supervised-test");

    struct passwd *pw = getpwuid(getuid());
    if (!pw || !pw->pw_dir || pw->pw_dir[0] != '/' || !pw->pw_name)
        refuse("missing local identity");
    char *home = strdup(pw->pw_dir), *user = strdup(pw->pw_name);
    if (!home || !user) refuse("allocation failure");
    char runtime[128];
    snprintf(runtime, sizeof runtime, "/run/user/%lu", (unsigned long)getuid());
    int fd = open(runtime, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    struct stat st;
    if (fd < 0 || fstat(fd, &st) || st.st_uid != getuid() || (st.st_mode & 0077))
        refuse("untrusted runtime directory");
    close(fd);

    /* The fresh environment excludes GNOME_SHELL_JS, GJS_PATH, alternate
     * schema/backend/profile paths, typelibs, GIO modules and loader options.
     * Only validated locale data survives from the caller. Session identity
     * is obtained by the real desktop/logind using the process credentials.
     */
    const char *locale_keys[] = {"LANG", "LC_ALL", "LC_CTYPE", "LC_MESSAGES",
        "LC_TIME", "LC_NUMERIC", "LC_MONETARY", "LC_MEASUREMENT", "LC_PAPER", NULL};
    char *locale_values[10] = {0};
    for (int i = 0; locale_keys[i]; i++) {
        const char *value = getenv(locale_keys[i]);
        if (value && !locale_valid(value)) refuse("invalid locale");
        if (value && !(locale_values[i] = strdup(value))) refuse("allocation failure");
    }
    if (clearenv()) refuse("cannot clear environment");
#define SET(k, v) do { if (setenv((k), (v), 1)) refuse("cannot set environment"); } while (0)
    SET("HOME", home); SET("USER", user); SET("LOGNAME", user);
    SET("PATH", "/usr/bin:/bin"); SET("LANG", "C.UTF-8");
    SET("XDG_RUNTIME_DIR", runtime);
    char bus[256];
    snprintf(bus, sizeof bus, "unix:path=%s/bus", runtime);
    SET("DBUS_SESSION_BUS_ADDRESS", bus);
    SET("XDG_DATA_DIRS", "/usr/local/share:/usr/share");
    SET("XDG_CONFIG_DIRS", "/etc/xdg:/usr/etc/xdg");
    SET("XDG_SESSION_TYPE", "wayland"); SET("XDG_SESSION_CLASS", "user");
    SET("XDG_CURRENT_DESKTOP", "GNOME"); SET("DESKTOP_SESSION", "gnome");
    SET("GDMSESSION", "gnome"); SET("GNOME_SHELL_SESSION_MODE", "user");
    SET("DCONF_PROFILE", "/etc/dconf/profile/lyra-supervised-test");
    SET("GSETTINGS_BACKEND", "dconf");
    GSettings *settings = g_settings_new("org.gnome.shell");
    const char *keys[] = {"allow-extension-installation", "development-tools",
                         "disable-user-extensions"};
    for (int i = 0; i < 3; i++) {
        if (g_settings_is_writable(settings, keys[i]) ||
            g_settings_get_boolean(settings, keys[i]) != (i == 2))
            refuse("desktop restrictions are not locked and effective");
    }
    g_object_unref(settings);
    fprintf(stderr, "trusted-shell fixture: desktop restrictions locked and effective\n");
    for (int i = 0; locale_keys[i]; i++)
        if (locale_values[i]) SET(locale_keys[i], locale_values[i]);
    if (chdir(home)) refuse("cannot enter home");
#ifdef LYRA_TEST_WAYLAND_ONLY
    /* Separate diagnostic run; not an approved product compatibility change. */
    char *const command[] = {"/usr/bin/gnome-shell", "--no-x11", NULL};
#else
    char *const command[] = {"/usr/bin/gnome-shell", NULL};
#endif
    execv(command[0], command);
    refuse("cannot execute desktop");
}
