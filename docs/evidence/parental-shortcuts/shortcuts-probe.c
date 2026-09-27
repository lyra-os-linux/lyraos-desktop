/* Fixed native portal exercise in the restricted account; no arbitrary targets. */
#define _GNU_SOURCE
#include <gio/gio.h>
#include <selinux/selinux.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static const char *dest="org.freedesktop.portal.Desktop";
static const char *path="/org/freedesktop/portal/desktop";
static const char *iface="org.freedesktop.portal.GlobalShortcuts";
static GMainLoop *loop;
static char *handle, *session;
static guint response=99, activated, deactivated;
static GVariant *results;
static GVariant *empty(void) {return g_variant_new_array(G_VARIANT_TYPE("{sv}"),NULL,0);}
static GVariant *call(GDBusConnection *bus,const char *target,const char *interface,
                      const char *method,GVariant *args) {
    GError *error=NULL;
    GVariant *reply=g_dbus_connection_call_sync(bus,dest,target,interface,method,args,NULL,
        G_DBUS_CALL_FLAGS_NONE,10000,NULL,&error);
    if(!reply){fprintf(stderr,"%s: %s\n",method,error->message);g_clear_error(&error);}
    return reply;
}
static gboolean timeout_cb(gpointer data) {(void)data;g_main_loop_quit(loop);return G_SOURCE_REMOVE;}
static void response_cb(GDBusConnection *bus,const char *sender,const char *object,
    const char *interface,const char *signal,GVariant *params,gpointer data) {
    (void)bus;(void)sender;(void)interface;(void)signal;(void)data;
    if(!handle || strcmp(handle,object))return;
    g_variant_get(params,"(u@a{sv})",&response,&results);
    g_main_loop_quit(loop);
}
static gboolean request(GDBusConnection *bus,const char *method,GVariant *args,const char *phase) {
    g_clear_pointer(&handle,g_free);g_clear_pointer(&results,g_variant_unref);response=99;
    GVariant *reply=call(bus,path,iface,method,args);if(!reply)return FALSE;
    g_variant_get(reply,"(o)",&handle);g_variant_unref(reply);
    if(phase)printf("phase=%s\n",phase);
    guint timer=g_timeout_add_seconds(25,timeout_cb,NULL);
    g_main_loop_run(loop);
    if(response!=99)g_source_remove(timer);
    printf("%s-response=%u\n",method,response);
    return response!=99;
}
static void signal_cb(GDBusConnection *bus,const char *sender,const char *object,
    const char *interface,const char *signal,GVariant *params,gpointer data) {
    (void)bus;(void)sender;(void)object;(void)interface;(void)data;
    const char *observed,*id;guint64 stamp;GVariant *options;
    g_variant_get(params,"(&o&st@a{sv})",&observed,&id,&stamp,&options);
    if(!strcmp(observed,session) && !strcmp(id,"fixture")) {
        if(!strcmp(signal,"Activated"))activated++;
        if(!strcmp(signal,"Deactivated"))deactivated++;
        printf("shortcut-signal=%s timestamp=%" G_GUINT64_FORMAT "\n",signal,stamp);
        if(activated && deactivated)g_main_loop_quit(loop);
    }
    g_variant_unref(options);
}
static gboolean registered(GDBusConnection *bus) {
    GVariant *r=call(bus,path,"org.freedesktop.host.portal.Registry","Register",
        g_variant_new("(s@a{sv})","org.lyra.ShortcutsFixture",empty()));
    if(!r)return FALSE;
    g_variant_unref(r);return TRUE;
}
static GVariant *shortcuts(void) {
    GVariantBuilder options,items;
    g_variant_builder_init(&options,G_VARIANT_TYPE_VARDICT);
    g_variant_builder_add(&options,"{sv}","description",g_variant_new_string("Lyra fixture action"));
    g_variant_builder_add(&options,"{sv}","preferred_trigger",g_variant_new_string("CTRL+SHIFT+F8"));
    g_variant_builder_init(&items,G_VARIANT_TYPE("a(sa{sv})"));
    g_variant_builder_add(&items,"(sa{sv})","fixture",&options);
    return g_variant_builder_end(&items);
}
static gboolean foreign_denied(GDBusConnection *bus,const char *method) {
    GError *error=NULL;
    GVariant *args=!strcmp(method,"ListShortcuts") ?
        g_variant_new("(o@a{sv})",session,empty()) :
        g_variant_new("(o@a(sa{sv})s@a{sv})",session,shortcuts(),"",empty());
    GVariant *r=g_dbus_connection_call_sync(bus,dest,path,iface,method,args,NULL,
        G_DBUS_CALL_FLAGS_NONE,5000,NULL,&error);
    gboolean denied=!r && g_error_matches(error,G_DBUS_ERROR,G_DBUS_ERROR_ACCESS_DENIED);
    printf("foreign-%s-denied=%d\n",method,denied);
    if(r)g_variant_unref(r);
    g_clear_error(&error);return denied;
}
static gboolean list_matches(GDBusConnection *bus,gsize expected) {
    if(!request(bus,"ListShortcuts",g_variant_new("(o@a{sv})",session,empty()),NULL) || response)return FALSE;
    GVariant *items=g_variant_lookup_value(results,"shortcuts",G_VARIANT_TYPE("a(sa{sv})"));
    if(!items)return FALSE;
    gboolean ok=g_variant_n_children(items)==expected;
    if(expected==1 && ok) {
        const char *id;GVariant *options;
        g_variant_get_child(items,0,"(&s@a{sv})",&id,&options);
        const char *description=NULL;
        ok=!strcmp(id,"fixture") && g_variant_lookup(options,"trigger_description","&s",&description) && *description;
        g_variant_unref(options);
    }
    printf("listed-shortcuts=%zu expected=%zu matches=%d\n",g_variant_n_children(items),expected,ok);
    g_variant_unref(items);return ok;
}
int main(int argc,char **argv) {
    setvbuf(stdout,NULL,_IONBF,0);
    char *label=NULL;
    if(argc!=2 || getuid()!=1003 || geteuid()!=1003 || security_getenforce()!=1 || getcon(&label))return 126;
    if(!strstr(label,":lyra_parental_probe_t:"))return 126;
    printf("context=%s enforcing=1\n",label);freecon(label);
    gboolean cancel=!strcmp(argv[1],"cancel");
    if(!cancel && strcmp(argv[1],"activate"))return 64;
    GError *error=NULL;
    GDBusConnection *bus=g_bus_get_sync(G_BUS_TYPE_SESSION,NULL,&error);
    if(!bus || !registered(bus))return 1;
    loop=g_main_loop_new(NULL,FALSE);
    g_dbus_connection_signal_subscribe(bus,dest,"org.freedesktop.portal.Request","Response",NULL,NULL,
        G_DBUS_SIGNAL_FLAGS_NONE,response_cb,NULL,NULL);
    GVariantBuilder options;
    g_variant_builder_init(&options,G_VARIANT_TYPE_VARDICT);
    g_variant_builder_add(&options,"{sv}","session_handle_token",g_variant_new_string("lyra_shortcuts"));
    if(!request(bus,"CreateSession",g_variant_new("(a{sv})",&options),NULL) || response)return 2;
    if(!g_variant_lookup(results,"session_handle","s",&session))return 3;
    printf("session=%s\n",session);
    if(!list_matches(bus,0))return 4;
    if(!cancel) {
        GDBusConnection *other=g_dbus_connection_new_for_address_sync("unix:path=/run/user/1003/bus",
            G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT|G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,NULL,NULL,&error);
        if(!other || !registered(other) || !foreign_denied(other,"ListShortcuts") || !foreign_denied(other,"BindShortcuts"))return 5;
        g_object_unref(other);
    }
    g_dbus_connection_signal_subscribe(bus,dest,iface,"Activated",path,NULL,G_DBUS_SIGNAL_FLAGS_NONE,signal_cb,NULL,NULL);
    g_dbus_connection_signal_subscribe(bus,dest,iface,"Deactivated",path,NULL,G_DBUS_SIGNAL_FLAGS_NONE,signal_cb,NULL,NULL);
    if(!request(bus,"BindShortcuts",g_variant_new("(o@a(sa{sv})s@a{sv})",session,shortcuts(),"",empty()),
        cancel?"shortcuts-cancel":"shortcuts-bind"))return 6;
    if(cancel) {
        if(response==0 || !list_matches(bus,0))return 7;
        puts("cancel-left-no-bindings=1");
    } else {
        if(response || !list_matches(bus,1))return 8;
        puts("phase=shortcuts-activate");
        guint timer=g_timeout_add_seconds(20,timeout_cb,NULL);g_main_loop_run(loop);
        if(activated && deactivated)g_source_remove(timer);
        if(activated!=1 || deactivated!=1)return 9;
    }
    GVariant *reply=call(bus,session,"org.freedesktop.portal.Session","Close",NULL);
    if(!reply)return 10;
    g_variant_unref(reply);
    if(!cancel) {
        guint before_a=activated,before_d=deactivated;
        puts("phase=shortcuts-released");
        g_timeout_add_seconds(10,timeout_cb,NULL);g_main_loop_run(loop);
        if(activated!=before_a || deactivated!=before_d)return 11;
        puts("closed-session-no-signals=1");
        if(!foreign_denied(bus,"ListShortcuts"))return 12;
    }
    puts("shortcuts-probe-passed=1");return 0;
}
