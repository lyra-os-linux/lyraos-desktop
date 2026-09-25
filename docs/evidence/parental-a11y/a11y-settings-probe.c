/* Fixed native behavioral probe, disposable UID 1003 only. */
#include <gio/gio.h>
#include <selinux/selinux.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>

static gboolean wait_value(GSettings *settings, gboolean wanted) {
    gint64 deadline = g_get_monotonic_time() + 5000000;
    while (g_get_monotonic_time() < deadline) {
        while (g_main_context_iteration(NULL, FALSE)) {}
        if (g_settings_get_boolean(settings, "toolkit-accessibility") == wanted) return TRUE;
        g_usleep(20000);
    }
    return FALSE;
}

int main(int argc, char **argv) {
    (void)argv;
    char *context = NULL;
    if (argc != 1 || getuid() != 1003 || getuid() != geteuid() || security_getenforce() != 1 || getcon(&context) < 0) return 126;
    printf("context=%s enforcing=1\n", context);
    gboolean restricted = strstr(context, ":lyra_parental_probe_t:") != NULL;
    freecon(context);
    if (!restricted) return 126;
    GSettings *apps = g_settings_new("org.gnome.desktop.a11y.applications");
    GSettings *interface = g_settings_new("org.gnome.desktop.interface");
    /* A fresh fixture has no user database; establish a deterministic baseline. */
    if (!g_settings_set_boolean(apps, "screen-reader-enabled", FALSE) ||
        !g_settings_set_boolean(apps, "screen-magnifier-enabled", FALSE) ||
        !g_settings_set_boolean(apps, "screen-keyboard-enabled", FALSE) ||
        !g_settings_set_boolean(interface, "toolkit-accessibility", FALSE)) return 1;
    g_settings_sync();
    const gboolean wanted[] = {TRUE, FALSE, TRUE};
    for (guint i = 0; i < G_N_ELEMENTS(wanted); i++) {
        if (!g_settings_set_boolean(apps, "screen-keyboard-enabled", wanted[i])) return 2;
        g_settings_sync();
        gboolean observed = wait_value(interface, wanted[i]);
        printf("keyboard=%d toolkit-observed=%d expected=%d\n", wanted[i], g_settings_get_boolean(interface, "toolkit-accessibility"), wanted[i]);
        if (!observed) return 3;
    }
    g_object_unref(apps); g_object_unref(interface);
    return 0;
}
