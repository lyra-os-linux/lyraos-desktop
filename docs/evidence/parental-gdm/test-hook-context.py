"""Compile the actual patched GDM function with SELinux fault injection stubs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

source = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('run-script.c.inc')).read_text()
start = source.index('static gboolean\nrun_script (')
end = source.find('\nstatic void\n', start)
if end < 0: end = len(source)
function = source[start:end]
prefix = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int gboolean;
#define TRUE 1
#define FALSE 0
typedef struct {
    int is_program_session;
    char *username, *x11_display_name;
    int display_is_local;
    char *hostname, *x11_authority_file;
} GdmSessionWorker;
static int enabled, fail_get, fail_clear, fail_restore, hook_result;
static int gets, clears, restores, hooks, warnings, frees;
static const char *pending;
int is_selinux_enabled(void) { return enabled; }
int getexeccon(char **ctx) {
    gets++;
    if (fail_get) return -1;
    *ctx = pending ? strdup(pending) : NULL;
    return 0;
}
int setexeccon(const char *ctx) {
    if (ctx) {
        restores++;
        if (fail_restore) return -1;
        assert(strcmp(ctx, "restricted-session") == 0);
        pending = "restricted-session";
    } else {
        clears++;
        if (fail_clear) return -1;
        pending = NULL;
    }
    return 0;
}
void freecon(char *ctx) { if (ctx) frees++; free(ctx); }
void g_warning(const char *message, ...) { warnings++; }
int gdm_run_script(const char *dir, const char *user, const char *display,
                   const char *host, const char *authority) {
    hooks++;
    assert(pending == NULL); /* Root hook never consumes the user's context. */
    assert(strcmp(dir, "/root-hook") == 0 && strcmp(user, "fixture") == 0);
    assert(host == NULL); /* Preserve local-session arguments. */
    return hook_result;
}
static void reset(void) {
    enabled = hook_result = 1;
    fail_get = fail_clear = fail_restore = 0;
    gets = clears = restores = hooks = warnings = frees = 0;
    pending = "restricted-session";
}
'''
tests = r'''
int main(void) {
    GdmSessionWorker worker = {0, "fixture", ":0", 1, "host", "authority"};
#ifdef HAVE_SELINUX
    reset();
    assert(run_script(&worker, "/root-hook"));
    assert(gets == 1 && clears == 1 && restores == 1 && hooks == 1 && frees == 1);
    assert(pending && !warnings);
    reset(); fail_get = 1;
    assert(!run_script(&worker, "/root-hook"));
    assert(!hooks && !clears && pending && warnings == 1);
    reset(); fail_clear = 1;
    assert(!run_script(&worker, "/root-hook"));
    assert(!hooks && !restores && pending && warnings == 1 && frees == 1);
    reset(); fail_restore = 1;
    assert(!run_script(&worker, "/root-hook"));
    assert(hooks == 1 && restores == 1 && !pending && warnings == 1 && frees == 1);
    reset(); hook_result = 0;
    assert(!run_script(&worker, "/root-hook"));
    assert(hooks == 1 && restores == 1 && pending && !warnings && frees == 1);
    reset(); pending = NULL;
    assert(run_script(&worker, "/root-hook"));
    assert(gets == 1 && !clears && !restores && hooks == 1 && !frees);
    reset(); enabled = 0; pending = NULL;
    assert(run_script(&worker, "/root-hook"));
    assert(!gets && !clears && !restores && hooks == 1);
    reset(); worker.is_program_session = 1;
    assert(run_script(&worker, "/root-hook"));
    assert(!gets && !hooks && pending);
    puts("8 SELinux hook cases PASS");
#else
    reset(); pending = NULL;
    assert(run_script(&worker, "/root-hook"));
    assert(!gets && hooks == 1);
    worker.is_program_session = 1;
    assert(run_script(&worker, "/root-hook"));
    assert(hooks == 1);
    puts("2 non-SELinux hook cases PASS");
#endif
    return 0;
}
'''
results = []
with tempfile.TemporaryDirectory(prefix='lyra-gdm-hook-test-') as tmp:
    cfile = Path(tmp) / 'hook.c'
    cfile.write_text(prefix + function + tests)
    for selinux in (True, False):
        exe = Path(tmp) / ('selinux' if selinux else 'no-selinux')
        args = ['gcc', '-std=gnu17', '-Wall', '-Wextra', '-Werror',
                '-Wno-unused-parameter', '-o', str(exe), str(cfile)]
        if selinux:
            args.insert(1, '-DHAVE_SELINUX')
        subprocess.run(args, check=True)
        result = subprocess.check_output([str(exe)], text=True).strip()
        results.append(dict(selinux_build=selinux, result=result))
print(json.dumps(dict(function_sha256=hashlib.sha256(function.encode()).hexdigest(),
                     results=results), indent=2))
