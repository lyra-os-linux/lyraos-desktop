"""Execute via host.py code, which supplies Path and checks VM markers."""
import subprocess,json
base=Path('/root/ordinary-withdrawal')
for name in ('result.json','exit-status','stdout.log','stderr.log'):
 (base/name).unlink(missing_ok=True)
source="from pathlib import Path; import subprocess; b=Path('/root/ordinary-withdrawal'); f=(b/'stdout.log').open('w'); g=(b/'stderr.log').open('w'); p=subprocess.run(['/usr/bin/python3','-u',str(b/'native.py')],stdout=f,stderr=g); f.close(); g.close(); (b/'exit-status').write_text(str(p.returncode)+'\\n')"
p=subprocess.Popen(['/usr/bin/python3','-c',source],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
print(json.dumps({'launcher_pid':p.pid,'detached':True}))
