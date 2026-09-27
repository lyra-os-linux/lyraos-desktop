"""Read-only compatibility checks inside the marked disposable VM."""
import json,pathlib,subprocess
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[]
for cmd in [
 ['rpm','-q','gjs','gnome-shell','gstreamer','typelib-1_0-Gst-1_0'],
 ['rpm','-V','gjs','gnome-shell','gstreamer','typelib-1_0-Gst-1_0'],
 ['runuser','-u','ordinaryuser','--','id','-Z'],
 ['runuser','-u','ordinaryuser','--','gjs','-c','const Gst=imports.gi.Gst; print(Gst.init_check(null));'],
 ['runuser','-u','ordinaryuser','--','gjs','-c','const Gst=imports.gi.Gst; print(JSON.stringify(Gst.init_check([])));']]:
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
 rows.append(dict(argv=cmd,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
print(json.dumps(rows,indent=2))
