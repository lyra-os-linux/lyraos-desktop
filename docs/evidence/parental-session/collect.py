import importlib.util,json,pathlib,sys
OUT=pathlib.Path(__file__).resolve().parent
CONTROL=(pathlib.Path(sys.argv[2])/'analysis/2026-09-25/parental-gdm/control.py') if len(sys.argv)>2 else OUT.parent/'parental-gdm/control.py'
spec=importlib.util.spec_from_file_location('vm_control',CONTROL);control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
tag=sys.argv[1]
paths={'session':'/root/trusted-shell-session.json','audit':'/root/trusted-shell-audit.json','progress':'/root/trusted-shell-progress.json','faults':'/root/trusted-shell-config-faults.json','restoration':'/root/xwayland-'+tag+'-result.json','stderr':'/root/xwayland-'+tag+'-stderr.log','shell-stderr':'/root/trusted-shell-stderr.log'}
code='import json,subprocess\npaths='+repr(paths)+'''\nassert not pathlib.Path('/root/lyra-xwayland-recovery/active.json').exists(), 'Recovery pending'
print(json.dumps({k:pathlib.Path(v).read_text() if pathlib.Path(v).exists() else None for k,v in paths.items()}))'''
data=json.loads(control.code(code))
for key,value in data.items():
 if value is not None:(OUT/(key+'-'+tag+('.log' if 'stderr' in key else '.json'))).write_text(value)
print('Collected:',', '.join(k for k,v in data.items() if v is not None))
