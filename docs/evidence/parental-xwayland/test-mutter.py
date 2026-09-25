"""Compile and exercise the actual upstream anonymous-file implementation."""
import pathlib,subprocess,tempfile,sys,json,shlex
root=pathlib.Path(sys.argv[1]).resolve();src=root/'src/core/meta-anonymous-file.c';header=(root/'src/core/meta-anonymous-file.h').read_text()
with tempfile.TemporaryDirectory(prefix='lyra-mutter-fd-') as td:
 p=pathlib.Path(td);(p/'core').mkdir()
 (p/'config.h').write_text('#define HAVE_MEMFD_CREATE 1\n#define HAVE_MKOSTEMP 1\n#define HAVE_POSIX_FALLOCATE 1\n')
 header=header.replace('#include "meta/common.h"','#include <glib.h>\n#include <stdint.h>\n#include <unistd.h>\n#include <string.h>').replace('#include "core/util-private.h"','#define META_EXPORT_TEST')
 (p/'core/meta-anonymous-file.h').write_text(header)
 code='''#define _GNU_SOURCE
#include <fcntl.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
static int fail_open;
static int controlled_open(const char *path,int flags) {
 if(fail_open) {errno=EACCES;return -1;}return open(path,flags);
}
#define open controlled_open
#include "'''+str(src)+'''"
#undef open
static int count_fds(void) {int n=0;for(int i=0;i<256;i++) if(fcntl(i,F_GETFD)>=0)n++;return n;}
int main(void) {
 int before=count_fds();
 MetaAnonymousFile *f=meta_anonymous_file_new(7,(const uint8_t *)"keymap");assert(f);
 assert(meta_anonymous_file_size(f)==7);
 fail_open=1;errno=0;
 assert(meta_anonymous_file_open_fd(f,META_ANONYMOUS_FILE_MAPMODE_PRIVATE)==-1 && errno==EACCES);
 fail_open=0;
 int ro=meta_anonymous_file_open_fd(f,META_ANONYMOUS_FILE_MAPMODE_PRIVATE);assert(ro>=0);
 assert((fcntl(ro,F_GETFL)&O_ACCMODE)==O_RDONLY);
 assert(fcntl(ro,F_GETFD)&FD_CLOEXEC);
 assert((fcntl(ro,F_GET_SEALS)&READONLY_SEALS)==READONLY_SEALS);
 char data[7];assert(pread(ro,data,7,0)==7 && !strcmp(data,"keymap"));
 assert(pwrite(ro,"X",1,0)==-1 && errno==EBADF);
 char *private=mmap(NULL,7,PROT_READ|PROT_WRITE,MAP_PRIVATE,ro,0);assert(private!=MAP_FAILED);
 private[0]='X';munmap(private,7);assert(pread(ro,data,7,0)==7 && !strcmp(data,"keymap"));
 int current=count_fds();
 for(int i=0;i<1000;i++) {
  int next=meta_anonymous_file_open_fd(f,META_ANONYMOUS_FILE_MAPMODE_PRIVATE);assert(next==ro);
  meta_anonymous_file_close_fd(next);assert(fcntl(ro,F_GETFD)>=0);
 }
 assert(count_fds()==current);
 int rw=meta_anonymous_file_open_fd(f,META_ANONYMOUS_FILE_MAPMODE_SHARED);assert(rw>=0 && rw!=ro);
 assert((fcntl(rw,F_GETFL)&O_ACCMODE)==O_RDWR);
 char *shared=mmap(NULL,7,PROT_READ|PROT_WRITE,MAP_SHARED,rw,0);assert(shared!=MAP_FAILED);
 shared[0]='S';munmap(shared,7);assert(pread(ro,data,7,0)==7 && !strcmp(data,"keymap"));
 meta_anonymous_file_close_fd(rw);assert(fcntl(rw,F_GETFD)==-1 && errno==EBADF);
 meta_anonymous_file_free(f);assert(count_fds()==before);
 f=meta_anonymous_file_new(0,NULL);assert(f);ro=meta_anonymous_file_open_fd(f,META_ANONYMOUS_FILE_MAPMODE_PRIVATE);assert(ro>=0);
 meta_anonymous_file_close_fd(ro);meta_anonymous_file_free(f);assert(count_fds()==before);
 puts("PASS: failure/retry, readonly/CLOEXEC/seals/data, private COW, shared compatibility, 1000 opens without leaks, free, empty file");
}
'''
 (p/'test.c').write_text(code)
 flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','glib-2.0'],text=True))
 subprocess.run(['cc','-std=gnu17','-Wall','-Wextra','-Werror','-I'+str(p),str(p/'test.c'),'-o',str(p/'test')]+flags,check=True)
 r=subprocess.run([str(p/'test')],capture_output=True,text=True,check=True)
 upstream=root/'src/tests/anonymous-file.c'
 subprocess.run(['cc','-D_GNU_SOURCE','-std=gnu17','-I'+str(p),str(src),str(upstream),'-o',str(p/'upstream')]+flags,check=True)
 upstream_result=subprocess.run([str(p/'upstream')],capture_output=True,text=True,check=True)
 print(json.dumps(dict(status='passed',stdout=r.stdout,source=str(src),upstream_test=dict(path='src/tests/anonymous-file.c',rc=upstream_result.returncode)),indent=2))
