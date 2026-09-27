/* Fixed calls made as the restricted account; no configurable D-Bus target. */
#define _GNU_SOURCE
#include <gio/gio.h>
#include <gio/gunixfdlist.h>
#include <selinux/selinux.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static GMainLoop *chooser_loop;
static char *chooser_handle;
static guint chooser_result = 99;
static gboolean chooser_file_matches;
static gboolean overview_hidden;
static gboolean focus_chooser(gpointer data) {
    GError *error=NULL;
    GVariant *reply=g_dbus_connection_call_sync(data,"org.gnome.Shell","/org/gnome/Shell",
        "org.freedesktop.DBus.Properties","Set",g_variant_new("(ssv)",
        "org.gnome.Shell","OverviewActive",g_variant_new_boolean(FALSE)),
        NULL,G_DBUS_CALL_FLAGS_NONE,3000,NULL,&error);
    overview_hidden=reply!=NULL;
    if(reply)g_variant_unref(reply);
    else {fprintf(stderr,"hide overview: %s\n",error->message);g_error_free(error);}
    printf("overview-hidden=%d\n",overview_hidden);fflush(stdout);
    return G_SOURCE_REMOVE;
}
static void chooser_response(GDBusConnection *bus, const gchar *sender,
    const gchar *path, const gchar *iface, const gchar *signal,
    GVariant *parameters, gpointer data) {
    (void)bus; (void)sender; (void)iface; (void)signal; (void)data;
    if (!chooser_handle || strcmp(path, chooser_handle)) return;
    GVariant *results = NULL;
    g_variant_get(parameters,"(u@a{sv})",&chooser_result,&results);
    gchar **uris=NULL;
    if(g_variant_lookup(results,"uris","^as",&uris)) {
        chooser_file_matches=uris[0] && !uris[1] && !strcmp(uris[0],"file:///home/parentaltest/chooser.txt");
        if(uris[0])printf("filechooser-uri=%s\n",uris[0]);
        g_strfreev(uris);
    }
    g_variant_unref(results); g_main_loop_quit(chooser_loop);
}
static gboolean chooser_timeout(gpointer data) {
    (void)data;g_main_loop_quit(chooser_loop);return G_SOURCE_REMOVE;
}
static int chooser(GDBusConnection *bus,gboolean select_file) {
    GError *error = NULL;
    chooser_loop=g_main_loop_new(NULL,FALSE);
    guint subscription=g_dbus_connection_signal_subscribe(bus,
        "org.freedesktop.portal.Desktop","org.freedesktop.portal.Request","Response",
        NULL,NULL,G_DBUS_SIGNAL_FLAGS_NONE,chooser_response,NULL,NULL);
    GVariantBuilder options;
    g_variant_builder_init(&options,G_VARIANT_TYPE_VARDICT);
    g_variant_builder_add(&options,"{sv}","handle_token",g_variant_new_string("lyra_chooser"));
    g_variant_builder_add(&options,"{sv}","current_folder",g_variant_new_bytestring("/home/parentaltest"));
    GVariant *reply=g_dbus_connection_call_sync(bus,"org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop","org.freedesktop.portal.FileChooser","OpenFile",
        g_variant_new("(ssa{sv})","","Lyra restricted file chooser",&options),
        G_VARIANT_TYPE("(o)"),G_DBUS_CALL_FLAGS_NONE,10000,NULL,&error);
    if (!reply) { fprintf(stderr,"chooser: %s\n",error->message); return 20; }
    g_variant_get(reply,"(o)",&chooser_handle);g_variant_unref(reply);
    printf("filechooser-ready=%s\n",chooser_handle);fflush(stdout);
    guint focus_timer=g_timeout_add(1500,focus_chooser,bus);
    guint timer=g_timeout_add_seconds(30,chooser_timeout,NULL);
    g_main_loop_run(chooser_loop);
    if(!overview_hidden && g_main_context_find_source_by_id(NULL,focus_timer))g_source_remove(focus_timer);
    if (chooser_result!=99) g_source_remove(timer);
    else {
        reply=g_dbus_connection_call_sync(bus,"org.freedesktop.portal.Desktop",chooser_handle,
            "org.freedesktop.portal.Request","Close",NULL,NULL,G_DBUS_CALL_FLAGS_NONE,3000,NULL,NULL);
        if(reply)g_variant_unref(reply);
    }
    printf("filechooser-response=%u\n",chooser_result);
    g_dbus_connection_signal_unsubscribe(bus,subscription);
    g_free(chooser_handle);g_main_loop_unref(chooser_loop);
    return overview_hidden && (select_file ? chooser_result==0 && chooser_file_matches : chooser_result==1) ? 0 : 21;
}
static int document_roundtrip(GDBusConnection *bus) {
    const char *source = "/home/parentaltest/.local/share/flatpak/db/elf-test";
    GError *error = NULL;
    gchar *data = NULL; gsize size = 0;
    if (!g_file_get_contents("/usr/bin/true", &data, &size, &error)) return 3;
    int fd = open(source, O_CREAT|O_EXCL|O_RDWR|O_CLOEXEC, 0700);
    if (fd < 0) return 4;
    gsize done = 0;
    while (done < size) {
        ssize_t n = write(fd, data + done, size - done);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return 5;
        done += n;
    }
    GUnixFDList *fds = g_unix_fd_list_new();
    int index = g_unix_fd_list_append(fds, fd, &error);
    if (index < 0) return 6;
    GVariant *reply = g_dbus_connection_call_with_unix_fd_list_sync(bus,
        "org.freedesktop.portal.Documents", "/org/freedesktop/portal/documents",
        "org.freedesktop.portal.Documents", "Add", g_variant_new("(hbb)", index, FALSE, TRUE),
        G_VARIANT_TYPE("(s)"), G_DBUS_CALL_FLAGS_NONE, 10000, fds, NULL, NULL, &error);
    close(fd); g_object_unref(fds);
    if (!reply) { fprintf(stderr, "Add: %s\n", error->message); return 7; }
    const char *id; g_variant_get(reply, "(&s)", &id);
    gchar *path = g_strdup_printf("/run/user/1003/doc/%s/elf-test", id);
    gchar *copy = NULL; gsize copied = 0;
    if (!g_file_get_contents(path, &copy, &copied, &error) || copied != size || memcmp(data, copy, size)) {
        fprintf(stderr, "document read failed: %s\n", error ? error->message : "bytes differ"); return 8;
    }
    fd = open(path, O_RDONLY|O_CLOEXEC);
    if (fd < 0) return 9;
    void *mapping = mmap(NULL, size, PROT_READ|PROT_EXEC, MAP_PRIVATE, fd, 0);
    int denied = errno;
    if (mapping != MAP_FAILED) munmap(mapping, size);
    close(fd);
    pid_t child = fork();
    if (child < 0) return 10;
    if (!child) { char *args[] = {path, NULL}; execv(path,args); _exit(errno == EACCES ? 126 : 125); }
    int status;
    if (waitpid(child,&status,0) != child) return 11;
    printf("document id=%s bytes=%zu mmap_errno=%d exec_status=%d\n", id, size, denied,
        WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    GVariant *deleted = g_dbus_connection_call_sync(bus, "org.freedesktop.portal.Documents",
        "/org/freedesktop/portal/documents", "org.freedesktop.portal.Documents", "Delete",
        g_variant_new("(s)", id), NULL, G_DBUS_CALL_FLAGS_NONE, 10000, NULL, &error);
    gboolean ok = deleted && mapping == MAP_FAILED && denied == EACCES &&
        WIFEXITED(status) && WEXITSTATUS(status) == 126 && unlink(source) == 0;
    if (deleted) g_variant_unref(deleted);
    g_variant_unref(reply); g_free(path); g_free(copy); g_free(data);
    return ok ? 0 : 12;
}
int main(int argc, char **argv) {
    char *label = NULL;
    if (argc != 2 || getuid() != 1003 || geteuid() != 1003 ||
        security_getenforce() != 1 || getcon(&label)) return 126;
    if (!strstr(label, ":lyra_parental_probe_t:")) return 126;
    printf("context=%s\n", label); freecon(label);
    GError *error = NULL;
    GDBusConnection *bus = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, &error);
    if (!bus) { fprintf(stderr, "%s\n", error->message); return 1; }
    if (!strcmp(argv[1], "chooser")) return chooser(bus,FALSE);
    if (!strcmp(argv[1], "chooser-select")) return chooser(bus,TRUE);
    if (!strcmp(argv[1], "document-roundtrip")) return document_roundtrip(bus);
    const char *name, *path, *iface, *method;
    GVariant *args = NULL;
    if (!strcmp(argv[1], "settings")) {
        name = "org.freedesktop.portal.Desktop";
        path = "/org/freedesktop/portal/desktop";
        iface = "org.freedesktop.portal.Settings";
        method = "Read";
        args = g_variant_new("(ss)", "org.gnome.desktop.interface", "color-scheme");
    } else if (!strcmp(argv[1], "documents")) {
        name = "org.freedesktop.portal.Documents";
        path = "/org/freedesktop/portal/documents";
        iface = "org.freedesktop.portal.Documents";
        method = "GetMountPoint";
    } else if (!strcmp(argv[1], "permissions")) {
        name = "org.freedesktop.impl.portal.PermissionStore";
        path = "/org/freedesktop/impl/portal/PermissionStore";
        iface = "org.freedesktop.impl.portal.PermissionStore";
        method = "List";
        args = g_variant_new("(s)", "documents");
    } else if (!strcmp(argv[1], "permission-write") || !strcmp(argv[1], "permission-read")) {
        name = "org.freedesktop.impl.portal.PermissionStore";
        path = "/org/freedesktop/impl/portal/PermissionStore";
        iface = "org.freedesktop.impl.portal.PermissionStore";
        if (!strcmp(argv[1], "permission-write")) {
            const char *permissions[] = {"read", NULL};
            method = "SetPermission";
            args = g_variant_new("(sbss^as)", "lyra-parental-test", TRUE,
                "fixture", "org.lyra.ParentFixture", permissions);
        } else {
            method = "Lookup";
            args = g_variant_new("(ss)", "lyra-parental-test", "fixture");
        }
    } else return 64;
    GVariant *reply = g_dbus_connection_call_sync(bus, name, path, iface, method,
        args, NULL, G_DBUS_CALL_FLAGS_NONE, 10000, NULL, &error);
    if (!reply) { fprintf(stderr, "%s\n", error->message); return 2; }
    char *printed = g_variant_print(reply, TRUE);
    printf("%s=%s\n", argv[1], printed);
    if (!strcmp(argv[1], "permission-read") &&
        (!strstr(printed, "org.lyra.ParentFixture") || !strstr(printed, "'read'"))) return 13;
    g_free(printed); g_variant_unref(reply); g_object_unref(bus);
    return 0;
}
