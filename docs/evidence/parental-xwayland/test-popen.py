"""Exercise the patched upstream Popen/Pclose implementation, not a duplicate."""
import pathlib,subprocess,tempfile,json,sys
root=pathlib.Path(sys.argv[1]);source=(root/'os/utils.c').read_text()
start=source.index('static struct pid {');end=source.index('/* fopen that drops privileges */',start)
close_start=source.index('int\nPclose(void *iop)',end);close_end=source.index('\nint\nFclose(',close_start)
headers='''#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <sys/wait.h>
#include <string.h>
#define DebugF(...) ((void)0)
static void OsBlockSignals(void) {}
static void OsReleaseSignals(void) {}
'''
main='''
int main(int argc, char **argv) {
 FILE *p;
 if (argc<2) return 125;
 if (!strcmp(argv[1],"invalid")) {
  const char *const empty[]={NULL};const char *const cmd[]={"/bin/true",NULL};
  return PopenArgv(NULL,"r") || PopenArgv(empty,"r") ||
         PopenArgv(cmd,NULL) || PopenArgv(cmd,"x") || PopenArgv(cmd,"r+") ||
         Popen(NULL,"r");
 }
 if (argc<3) return 125;
 p=!strcmp(argv[1],"legacy") ? Popen(argv[2],"r") : PopenArgv((const char *const *)(argv+2),argv[1]);
 if (!p) return 125;
 char buffer[4096];size_t n;
 if (!strcmp(argv[1],"w")) {
  while ((n=fread(buffer,1,sizeof(buffer),stdin)))
   if (fwrite(buffer,1,n,p)!=n) return 124;
 } else {
  while ((n=fread(buffer,1,sizeof(buffer),p)))
   if (fwrite(buffer,1,n,stdout)!=n) return 124;
 }
 int status=Pclose(p);
 return status>=0 && WIFEXITED(status) ? WEXITSTATUS(status) : 123;
}
'''
results=[]
with tempfile.TemporaryDirectory(prefix='lyra-popen-') as td:
 p=pathlib.Path(td);c=p/'probe.c';binary=p/'probe';c.write_text(headers+source[start:end]+source[close_start:close_end]+main)
 subprocess.run(['cc','-std=gnu17','-Wall','-Wextra','-Werror','-Wwrite-strings',str(c),'-o',str(binary)],check=True)
 def check(name,args,expected=0,output=None,data=None):
  r=subprocess.run([str(binary)]+args,input=data,capture_output=True,text=True,timeout=5)
  assert r.returncode==expected,(name,r.returncode,r.stderr)
  if output is not None:assert r.stdout==output,(name,r.stdout)
  results.append(dict(name=name,status='passed',returncode=r.returncode))
 marker=p/'executed';literal=f'$(touch {marker}); spaces "quotes" `touch {marker}`'
 check('literal-shell-metacharacters',['r','/usr/bin/printf','%s',literal],output=literal);assert not marker.exists()
 check('read-pipe',['r','/usr/bin/printf','%s','keyboard-data'],output='keyboard-data')
 outfile=p/'output with spaces;literal'
 check('write-pipe',['w','/usr/bin/tee',str(outfile)],data='keymap\n',output='keymap\n');assert outfile.read_text()=='keymap\n'
 check('missing-executable',['r',str(p/'missing')],expected=127)
 check('child-failure',['r','/usr/bin/false'],expected=1)
 check('invalid-arguments',['invalid'])
 check('legacy-shell-semantics',['legacy','printf "%s" "$((6 * 7))"'],output='42')
 check('no-path-search',['r','printf','unsafe'],expected=127)
print(json.dumps(dict(status='passed',checks=results),indent=2))
