"""Exercise the actual patched initialization function with real GLib objects."""
import pathlib,subprocess,tempfile,sys,shlex,json
source=pathlib.Path(sys.argv[1])/'src/x11/meta-x11-display.c'
text=source.read_text();start=text.index('static gboolean\nmeta_x11_display_init_frames_client (');end=text.index('\nstatic void\ninitialize_dbus_interface',start)
function=text[start:end]
prefix=r'''
#include <gio/gio.h>
typedef struct {void *display;GSubprocess *frames_client;GCancellable *frames_client_cancellable;} MetaX11Display;
static gboolean fail_spawn=TRUE,callback_done=FALSE;
static const char *get_display_name(void *display){(void)display;return ":test";}
static GSubprocess *meta_frame_launch_client(MetaX11Display *display,const char *name){(void)display;(void)name;if(fail_spawn)return NULL;return g_subprocess_new(G_SUBPROCESS_FLAGS_NONE,NULL,"/usr/bin/true",NULL);}
static void on_frames_client_died(GObject *source,GAsyncResult *result,gpointer data){(void)data;g_assert_true(g_subprocess_wait_finish(G_SUBPROCESS(source),result,NULL));callback_done=TRUE;}
'''
main=r'''
int main(void){
 MetaX11Display display={0};GError *error=NULL;
 g_assert_false(meta_x11_display_init_frames_client(&display,&error));
 g_assert_error(error,G_IO_ERROR,G_IO_ERROR_FAILED);g_clear_error(&error);
 g_assert_null(display.frames_client);g_assert_null(display.frames_client_cancellable);
 /* A caller without an error destination must also fail cleanly. */
 g_assert_false(meta_x11_display_init_frames_client(&display,NULL));
 fail_spawn=FALSE;
 g_assert_true(meta_x11_display_init_frames_client(&display,&error));g_assert_no_error(error);
 while(!callback_done)g_main_context_iteration(NULL,TRUE);
 g_clear_object(&display.frames_client);g_clear_object(&display.frames_client_cancellable);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);(p/'test.c').write_text(prefix+function+main)
 flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','gio-2.0'],text=True))
 subprocess.run(['cc','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test'),*flags],check=True)
 subprocess.run([str(p/'test')],check=True,timeout=10)
print(json.dumps(dict(passed=True,cases=['spawn failure returns error without async wait','failure without error destination','successful spawn and completion']),indent=2))
