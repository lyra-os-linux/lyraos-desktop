#define _GNU_SOURCE
#include <errno.h>
#include <ffi.h>
#include <fcntl.h>
#include <selinux/selinux.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void callback(ffi_cif *cif, void *result, void **args, void *data) {
    (void)cif; (void)args;
    *(int *)result = *(int *)data;
}
int main(int argc, char **argv) {
    char *context = NULL;
    if (getcon(&context)) return 125;
    printf("uid=%ld context=%s enforcing=%d\n",(long)getuid(),context,security_getenforce());
    freecon(context);
    fflush(stdout);
    if (argc==3 && !strcmp(argv[1],"--write")) {
        int fd=open(argv[2],O_WRONLY);
        printf("write_open success=%d errno=%d\n",fd>=0,errno);
        if (fd<0) return errno==EACCES ? 126 : 125;
        int ok=write(fd,"X",1)==1;
        close(fd);
        return ok ? 0 : 125;
    }
    ffi_cif cif;
    void *code = NULL;
    errno = 0;
    ffi_closure *closure = ffi_closure_alloc(sizeof(ffi_closure), &code);
    printf("ffi_closure_alloc success=%d errno=%d (%s)\n",closure!=NULL,errno,strerror(errno));
    if (!closure) return 126;
    int expected=42;
    if (ffi_prep_cif(&cif,FFI_DEFAULT_ABI,0,&ffi_type_sint,NULL)!=FFI_OK) return 125;
    if (ffi_prep_closure_loc(closure,&cif,callback,&expected,code)!=FFI_OK) return 125;
    int actual=((int (*)(void))code)();
    printf("callback result=%d\n",actual);
    ffi_closure_free(closure);
    return actual==42 ? 0 : 125;
}
