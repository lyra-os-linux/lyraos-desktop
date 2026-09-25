/* A real GTK/ATK window for the disposable accessibility experiment. */
#include <gtk/gtk.h>
#include <selinux/selinux.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
static gboolean stop(gpointer unused) { (void)unused; gtk_main_quit(); return G_SOURCE_REMOVE; }
int main(int argc, char **argv) {
    char *context = NULL;
    if (argc != 1 || getuid() != 1003 || security_getenforce() != 1 || getcon(&context) < 0) return 126;
    gboolean restricted = strstr(context, ":lyra_parental_probe_t:") != NULL;
    printf("context=%s\n", context);freecon(context);
    if (!restricted || !gtk_init_check(&argc, &argv)) return 1;
    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window), "Lyra accessibility fixture");
    GtkWidget *button = gtk_button_new_with_label("Lyra restricted accessible button");
    gtk_container_add(GTK_CONTAINER(window), button);
    gtk_widget_show_all(window);
    puts("accessible-window-ready");fflush(stdout);
    g_timeout_add_seconds(40, stop, NULL);
    gtk_main();gtk_widget_destroy(window);return 0;
}
