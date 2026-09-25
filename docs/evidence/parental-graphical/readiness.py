import pathlib,subprocess,json
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rows=[]
for a in [['df','-h','/'],['rpm','-q','zypper','gdm','gnome-shell','gnome-session'],['ls','/etc/zypp/repos.d']]:
 p=subprocess.run(a,capture_output=True,text=True,timeout=20);rows.append({'argv':a,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
print(json.dumps(rows,indent=2))
