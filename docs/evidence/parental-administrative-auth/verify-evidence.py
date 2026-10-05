"""Read-only verification of integrated administrative fixture receipts."""
from pathlib import Path
import hashlib,json
E=Path(__file__).resolve().parent
ROOT=E.parents[2]
def read(name):return json.loads((E/name).read_text())
m=read('manifest.json');assert m['schema']==1
for name,digest in m['files'].items():
 assert Path(name).name==name
 assert hashlib.sha256((E/name).read_bytes()).hexdigest()==digest
actual=json.loads(read('source-hashes.json')['stdout'])
assert read('source-hashes.json')['rc']==0 and len(actual)==14
for name,digest in m['sources'].items():
 assert name.startswith('docs/evidence/') and '..' not in Path(name).parts
 assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
 assert actual[Path(name).name]==digest
r=read('result.json')
assert all(r[k] is True for k in ('passed','restored','cleanup','real_dbus','real_polkit','real_unix_effects'))
assert all(r[k] is False for k in ('password_authentication','guardian_binding','production_integrated'))
assert r['error'] is None and r['state_before']==r['state_after']
assert r['state_after']['selinux']=='Permissive'
assert r['account_hashes_before']==r['account_hashes_after'] and r['configs_before']==r['configs_after']
cases={c['case']:c for c in r['cases']}
assert len(cases)==len(r['cases'])==15
assert set(cases)=={'profile','consumed','noop-grant','remove','noop-remove','payload-change','deny','cancel','revoke','catalog-change','barrier','replay','unauthorized','invalid','own'}
locks=['catalog.lock','.inventory-1002.lock','.gate-1002.lock']
unix=[];noops=[];polkits=[]
for name,c in cases.items():
 response=c['response'];events=c['events']
 assert c['identity_preserved'] is c['peer_preserved'] is True
 uid=1002 if name=='unauthorized' else 1000
 assert response['uid']==uid and all(e['uid']==uid for e in events if 'uid' in e)
 if name=='replay':
  assert response['sender']!=response['new_sender']
  assert [e['sender'] for e in events]==[response['sender'],response['new_sender']]
 else:assert all(e['sender']==response['sender'] for e in events if 'sender' in e)
 p=[e for e in events if e['event']=='polkit'];fx=[e for e in events if e['event'] in ('unix','noop')]
 unix.extend(e for e in fx if e['event']=='unix');noops.extend(e for e in fx if e['event']=='noop');polkits.extend(p)
 assert all(e['locks_free']==locks for e in p) and all(e['locks_held']==locks for e in fx)
 if name not in ('catalog-change','barrier'):assert c['before']==c['after']
 else:
  unchanged=('inventory','ledger') if name=='catalog-change' else ('catalog','inventory')
  assert all(c['before'][part]==c['after'][part] for part in unchanged)
  if name=='barrier':assert set(c['after']['ledger'])-set(c['before']['ledger'])=={'.deny-1002'}
 if name in ('profile','consumed','noop-grant','remove','noop-remove','payload-change'):
  assert response['result']=='OrdinaryMutationDispatched' and len(p)==len(fx)==1 and p[0]['returncode']==0
  if name=='consumed':assert response['repeat_error'].endswith('.Denied')
  if name.startswith('noop-'):assert fx[0]['event']=='noop' and c['accounts_before']==c['accounts_after']
  else:assert fx[0]['event']=='unix' and fx[0]['returncode']==0
 elif name=='own':
  assert response['result']=='OrdinaryEligible' and not p and not fx
  assert c['accounts_before']==c['accounts_after']
 else:
  expected='InvalidParameters' if name=='invalid' else 'Conflict' if name=='catalog-change' else 'Blocked' if name=='barrier' else 'Denied'
  assert response['error'].endswith('.'+expected) and not fx and c['accounts_before']==c['accounts_after']
  if name in ('replay','unauthorized','invalid'):assert not p
  else:
   assert len(p)==1
   assert p[0]['returncode']==(1 if name=='deny' else 3 if name=='cancel' else 0)
   if name=='cancel':assert response['agent_calls']==['org.lyraos.parental.fixture.challenge']
 for e in p:
  digest=e['parameter_digest'];assert len(digest)==64 and all(ch in '0123456789abcdef' for ch in digest)
  reference='profile' if name=='profile' else 'remove' if name in ('remove','noop-remove') else 'consumed'
  expected=next(e['parameter_digest'] for e in cases[reference]['events'] if e['event']=='polkit')
  assert digest==expected
assert len({next(e['parameter_digest'] for e in cases[n]['events'] if e['event']=='polkit') for n in ('profile','consumed','remove')})==3
assert len(unix)==4 and len(noops)==2 and len(polkits)==11
assert [e['argv'] for e in unix]==[
 ['/usr/sbin/usermod','-c','Lyra fixture $(literal)','-G','users','--','ordinaryuser'],
 ['/usr/sbin/usermod','-aG','wheel','--','ordinaryuser'],
 ['/usr/bin/gpasswd','-d','ordinaryuser','wheel'],
 ['/usr/sbin/usermod','-aG','wheel','--','ordinaryuser']]
assert [e['is_admin'] for e in noops]==[True,False]
assert read('execution.json')['rc']==0
assert json.loads(read('execution.json')['stdout'])==dict(passed=True,cases=15,error=None,cleanup=True)
assert read('cleanup-check.json')['rc']==read('poweroff.json')['rc']==read('guard.json')['rc']==0
assert json.loads(read('guard.json')['stdout'])['guard'] is True
assert json.loads(read('cleanup-check.json')['stdout'])==dict(passed=True,cleanup=True)
off=read('vm-off.json');disk=read('disk.json')
assert off['vm_off'] is True and off['qemu_returncode']==0 and off['backing_before']==off['backing_after']
assert disk['filename']==off['same_disk'] and disk['backing-filename-format']=='raw'
print('PASS: 15 integrated D-Bus/Polkit cases; 11 decisions, four Unix commands, two no-ops; denied/stale/replayed calls have no effects; restored, cleaned, unchanged backing, VM OFF. Product integration still pending.')
