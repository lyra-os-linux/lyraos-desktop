/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Publish the accessibility bus address when XWayland starts on demand. */
#include <gio/gio.h>
#include <X11/Xlib.h>
#include <X11/Xatom.h>
#include <string.h>

static int x_error;
static int record_x_error(Display *display, XErrorEvent *event) {
    (void)display;
    x_error = event->error_code;
    return 0;
}

int main(int argc, char **argv) {
    (void)argv;
    if (argc != 1) return 64;
    GError *error = NULL;
    GDBusConnection *bus = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, &error);
    if (!bus) {
        g_printerr("Cannot connect to session bus: %s\n", error->message);
        g_clear_error(&error);
        return 1;
    }
    GVariant *reply = g_dbus_connection_call_sync(bus, "org.a11y.Bus", "/org/a11y/bus",
        "org.a11y.Bus", "GetAddress", NULL, G_VARIANT_TYPE("(s)"),
        G_DBUS_CALL_FLAGS_NONE, 5000, NULL, &error);
    g_object_unref(bus);
    if (!reply) {
        g_printerr("Cannot query accessibility bus: %s\n", error->message);
        g_clear_error(&error);
        return 1;
    }
    const char *address;
    g_variant_get(reply, "(&s)", &address);
    size_t length = strlen(address);
    if (!length || length > 4096) { g_variant_unref(reply); return 1; }
    Display *display = XOpenDisplay(NULL);
    if (!display) { g_printerr("Cannot open X11 display\n"); g_variant_unref(reply); return 1; }
    XSetErrorHandler(record_x_error);
    XChangeProperty(display, DefaultRootWindow(display), XInternAtom(display, "AT_SPI_BUS", False),
        XA_STRING, 8, PropModeReplace, (const unsigned char *)address, (int)length);
    XSync(display, False);
    XCloseDisplay(display);
    g_variant_unref(reply);
    return x_error ? 1 : 0;
}
