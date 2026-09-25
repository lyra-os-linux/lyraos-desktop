/* Verify the X11 AT_SPI_BUS discovery path using the real libatspi client. */
#include <atspi/atspi.h>
#include <selinux/selinux.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
static gboolean find_button(AtspiAccessible *object, unsigned depth) {
    if (!object || depth > 6) return FALSE;
    GError *error = NULL;
    gchar *name = atspi_accessible_get_name(object, &error);
    gboolean found = !error && !g_strcmp0(name, "Lyra restricted accessible button") && atspi_accessible_get_role(object, NULL) == ATSPI_ROLE_PUSH_BUTTON;
    g_free(name);g_clear_error(&error);
    if (found) return TRUE;
    int n = atspi_accessible_get_child_count(object, &error);
    g_clear_error(&error);
    for (int i = 0; i < n && i < 100; i++) {
        AtspiAccessible *child = atspi_accessible_get_child_at_index(object, i, &error);
        g_clear_error(&error);
        if (child) { found = find_button(child, depth + 1);g_object_unref(child); }
        if (found) return TRUE;
    }
    return FALSE;
}
int main(int argc, char **argv) {
    (void)argv;
    char *context = NULL;
    if (argc != 1 || getuid() != 1003 || security_getenforce() != 1 || getcon(&context) < 0) return 126;
    gboolean restricted = strstr(context, ":lyra_parental_probe_t:") != NULL;
    printf("context=%s\n", context);freecon(context);
    if (!restricted || g_getenv("WAYLAND_DISPLAY") || g_getenv("AT_SPI_BUS_ADDRESS") ||
        g_strcmp0(g_getenv("DBUS_SESSION_BUS_ADDRESS"), "unix:path=/run/user/1003/no-session-bus-for-test")) return 126;
    atspi_set_timeout(1000, 2000);
    if (atspi_init()) return 1;
    AtspiAccessible *desktop = atspi_get_desktop(0);
    gboolean found = FALSE;
    for (int i = 0; desktop && i < 20 && !found; i++) {
        while (g_main_context_iteration(NULL, FALSE)) {}
        found = find_button(desktop, 0);
        if (!found) g_usleep(250000);
    }
    if (desktop) g_object_unref(desktop);
    printf("x11-only-discovery accessible-button=%s\n", found ? "PASS" : "FAIL");
    atspi_exit();return found ? 0 : 2;
}
