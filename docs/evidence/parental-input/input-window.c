/* Real Wayland keyboard delivery in the marked, disposable session only. */
#include <gtk/gtk.h>
#include <gdk/gdkwayland.h>
#include <selinux/selinux.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
static gboolean typed;
static gboolean stop(gpointer unused) { (void)unused;gtk_main_quit();return G_SOURCE_REMOVE; }
static void changed(GtkEditable *entry,gpointer unused) {
    (void)unused;
    const char *text=gtk_entry_get_text(GTK_ENTRY(entry));
    printf("keyboard-text=%s\n",text);fflush(stdout);
    if(!strcmp(text,"a")) {typed=TRUE;gtk_main_quit();}
}
int main(int argc,char **argv) {
    char *context=NULL;
    if(argc!=1 || getuid()!=1003 || geteuid()!=1003 || security_getenforce()!=1 || getcon(&context)<0) return 126;
    gboolean restricted=strstr(context,":lyra_parental_probe_t:")!=NULL;
    printf("context=%s\n",context);freecon(context);
    if(!restricted || !gtk_init_check(&argc,&argv) || !GDK_IS_WAYLAND_DISPLAY(gdk_display_get_default())) return 1;
    GtkWidget *window=gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window),"Lyra Wayland keyboard fixture");
    GtkWidget *entry=gtk_entry_new();gtk_container_add(GTK_CONTAINER(window),entry);
    g_signal_connect(entry,"changed",G_CALLBACK(changed),NULL);
    gtk_widget_show_all(window);gtk_widget_grab_focus(entry);
    puts("wayland-keyboard-ready");fflush(stdout);
    g_timeout_add_seconds(25,stop,NULL);gtk_main();gtk_widget_destroy(window);
    return typed?0:2;
}
