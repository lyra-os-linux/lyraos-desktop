/* Fixed read-only transport/authorization checks for the marked VM. */
#include <gio/gio.h>
#include <selinux/selinux.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
static GVariant *call(GDBusConnection *bus,const char *name,const char *path,const char *interface,const char *method,GVariant *args,const char *reply_type) {
 GError *error=NULL;
 GVariant *reply=g_dbus_connection_call_sync(bus,name,path,interface,method,args,G_VARIANT_TYPE(reply_type),G_DBUS_CALL_FLAGS_NONE,5000,NULL,&error);
 if(!reply){fprintf(stderr,"%s.%s: %s\n",interface,method,error->message);g_clear_error(&error);}
 return reply;
}
int main(int argc,char **argv) {
 (void)argv;char *context=NULL;
 if(argc!=1 || getuid()!=1003 || getuid()!=geteuid() || security_getenforce()!=1 || getcon(&context)<0) return 126;
 if(!strstr(context,":lyra_parental_shell_t:")){freecon(context);return 126;}
 printf("uid=%u context=%s enforcing=1\n",getuid(),context);freecon(context);
 GError *error=NULL;GDBusConnection *bus=g_bus_get_sync(G_BUS_TYPE_SYSTEM,NULL,&error);
 if(!bus){fprintf(stderr,"bus: %s\n",error->message);g_clear_error(&error);return 1;}
 GVariant *reply=call(bus,"org.gnome.DisplayManager","/org/gnome/DisplayManager/Manager","org.freedesktop.DBus.Properties","Get",g_variant_new("(ss)","org.gnome.DisplayManager.Manager","Version"),"(v)");
 if(!reply)return 2;
 g_variant_unref(reply);puts("gdm-version-read=PASS");
 reply=call(bus,"org.freedesktop.Accounts","/org/freedesktop/Accounts","org.freedesktop.Accounts","FindUserById",g_variant_new("(x)",(gint64)getuid()),"(o)");
 if(!reply)return 3;
 const char *borrowed;g_variant_get(reply,"(&o)",&borrowed);char *user_path=g_strdup(borrowed);g_variant_unref(reply);
 reply=call(bus,"org.freedesktop.Accounts",user_path,"org.freedesktop.DBus.Properties","Get",g_variant_new("(ss)","org.freedesktop.Accounts.User","Uid"),"(v)");
 if(!reply)return 4;
 GVariant *uid;g_variant_get(reply,"(v)",&uid);gboolean identity=g_variant_is_of_type(uid,G_VARIANT_TYPE_UINT64)&&g_variant_get_uint64(uid)==getuid();g_variant_unref(uid);g_variant_unref(reply);g_free(user_path);
 if(!identity)return 5;
 puts("account-identity-read=PASS");
 const char *actions[]={"org.freedesktop.accounts.user-administration","org.freedesktop.systemd1.manage-units",NULL};
 for(int i=0;actions[i];i++) {
  GVariantBuilder subject,details;
  g_variant_builder_init(&subject,G_VARIANT_TYPE_VARDICT);g_variant_builder_add(&subject,"{sv}","name",g_variant_new_string(g_dbus_connection_get_unique_name(bus)));
  g_variant_builder_init(&details,G_VARIANT_TYPE("a{ss}"));
  reply=call(bus,"org.freedesktop.PolicyKit1","/org/freedesktop/PolicyKit1/Authority","org.freedesktop.PolicyKit1.Authority","CheckAuthorization",g_variant_new("((sa{sv})sa{ss}us)","system-bus-name",&subject,actions[i],&details,(guint32)0,""),"((bba{ss}))");
  if(!reply)return 6;
  gboolean allowed,challenge;GVariant *metadata;
  g_variant_get(reply,"((bb@a{ss}))",&allowed,&challenge,&metadata);g_variant_unref(metadata);g_variant_unref(reply);
  printf("authorization action=%s allowed=%d challenge=%d\n",actions[i],allowed,challenge);
  if(allowed)return 7;
 }
 g_object_unref(bus);return 0;
}
