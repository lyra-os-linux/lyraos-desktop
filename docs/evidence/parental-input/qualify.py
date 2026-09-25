"""Check collected native evidence, including negative controls and restoration."""
import json,pathlib,re,sys
out=pathlib.Path(__file__).resolve().parent
tag=sys.argv[1]
def read(name):return json.loads((out/(name+'-'+tag+'.json')).read_text())
def stream(name):
 text=(out/(name+'-'+tag+'.json')).read_text();decoder=json.JSONDecoder();items=[]
 while text.strip():
  item,end=decoder.raw_decode(text.lstrip());items.append(item);text=text.lstrip()[end:]
 return items
rows=stream('session')[-1]
assert isinstance(rows,list)
def selected(needle):return [r for r in rows if needle in r['argv']]
def one(needle):
 r=selected(needle);assert len(r)==1,(needle,r);return r[0]
for mode in ['keyboard','fonts','data-not-code','approved','blocked']:
 r=[r for r in selected('/opt/lyra-parental-probe/input-probe') if r['argv'][-1]==mode];assert len(r)==1 and r[0]['rc']==0,r
assert "('xkb', 'us')" in one('keyboard')['stdout']
for mode in ['shortcut-approved','shortcut-blocked']:assert one(mode)['rc']==0
r=one('/opt/lyra-parental-probe/input-window')
assert r['rc']==0 and 'wayland-keyboard-ready' in r['stdout'] and 'keyboard-text=a' in r['stdout'],r
services=one('org.gnome.SettingsDaemon.Keyboard.service')['stdout']
assert services.count('ActiveState=active')==2 and services.count('NRestarts=0')==2,services
assert all(r['rc']==0 for r in selected('/opt/lyra-parental-probe/settings-probe'))
assert len(selected('/opt/lyra-parental-probe/settings-probe'))==9
assert one('continuity-45s')['rc']==0
assert one('/opt/lyra-parental-probe/xwindow-test')['rc']==0
assert one('/usr/libexec/lyra/parental-services-probe')['rc']==0
assert one('/opt/lyra-parental-probe/a11y-settings-probe')['rc']==0
assert [r['rc'] for r in selected('/opt/lyra-parental-probe/accessible-client')]==[0,1,0]
assert [r['rc'] for r in selected('/usr/etc/xdg/Xwayland-session.d/00-at-spi')]==[64,1,0]
assert one('gtk-ready')['rc']==0
app=one('/opt/lyra-parental-probe/accessible-app');assert app['rc']==0 and 'no writable cache directories' not in app['stderr'],app
assert one('getenforce')['stdout'].strip()=='Enforcing'
audit=read('audit');assert audit['lost_delta']==0 and not audit['limited']
denials=[d['line'] for d in audit['denials']]
assert any('comm="gsd-media-keys"' in l and 'execute' in l and 'shell_exec_t' in l for l in denials)
assert any('lyra_parental_fontcache_t' in l and 'execute' in l for l in denials)
assert not any('comm="gsd-keyboard"' in l and 'lyra_parental_shell_memory_t' in l and '{ write }' in l for l in denials)
assert not any('comm="gsd-media-keys"' in l and 'lyra_parental_shell_memory_t' in l and '{ write }' in l for l in denials)
restore=stream('restoration')
assert any(isinstance(r,dict) and r.get('restored') is True for r in restore)
assert not (out/('stderr-'+tag+'.log')).read_text().strip()
progress=read('progress');launch=[r for r in progress if r['argv'][0]=='runuser' and '/usr/libexec/lyra/parental-launch-probe' in r['argv']]
assert len(launch)==6 and [r['rc'] for r in launch]==[0,255,255,255,255,126],launch
keys=json.loads((out/(tag+'-keys.json')).read_text());assert keys==['approved','blocked','typing'],keys
failed=one('--failed')['stdout']
summary=dict(passed=True,tag=tag,keyboard_services=services,failed_user_units=failed,physical_vm_keys=keys,shortcut_positive=True,shortcut_shell_denied=True,wayland_typing=True,font_cache=True,font_cache_nonexecutable=True,shell_launch_boundary_cases=6,dconf_calls=9,a11y_clients=[0,1,0],audit_lost_delta=0,audit_limited=False,production_enabled=False)
(out/('summary-'+tag+'.json')).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
