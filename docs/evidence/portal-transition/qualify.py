"""Offline recheck of executed zypper transitions and restored VM inventory."""
import hashlib,json,pathlib
from policy import NAME,SUSE,STAGING,validate_plan
OUT=pathlib.Path(__file__).resolve().parent
def read(name):return json.loads((OUT/name).read_text())
for name,digest in read('source-hashes.json').items():
 assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==digest
rounds=[]
for prefix in ['main','translated']:
 names=[NAME] if prefix=='main' else [NAME,NAME+'-lang']
 for action in ['upgrade','idempotent','return']:
  row=read(prefix+'-'+action+'.json');assert row['passed']
  assert set(row['before'])==set(row['after'])==set(names)
  target=SUSE if action=='return' else STAGING
  assert all(tuple(v)==target for v in row['after'].values())
  changed=[] if action=='idempotent' else names
  assert validate_plan(row['dry_run'],row['before'],row['after'])==sorted(changed)
  assert validate_plan(row['applied'],row['before'],row['after'])==sorted(changed)
  assert row['changed']==sorted(changed)
  unchanged=lambda rows:[r for r in rows if r.split('\t')[0] not in names]
  assert unchanged(row['before_inventory'])==unchanged(row['after_inventory'])
  if action=='idempotent':assert row['before_inventory']==row['after_inventory']
  rounds.append(row['tag'])
commands=read('commands.json')
assert all(r['rc']==0 for r in commands)
signatures=[r for r in commands if r['argv'][:2]==['rpmkeys','--checksig']]
assert len(signatures)==4 and all('signatures OK' in r['stdout'] for r in signatures)
assert sum(r['argv'][0]=='zypper' and '--dry-run' in r['argv'] for r in commands)==6
assert sum(r['argv'][0]=='zypper' and '--dry-run' not in r['argv'] for r in commands)==6
# Successful returns must have used zypper. Emergency RPM downgrade did not run.
assert not any(r['argv'][:2]==['rpm','-Uvh'] for r in commands)
assert read('restored.json')==dict(restored=True,inventory_equal=True,config_equal=True,keys_equal=True)
final_inventory=next(r['stdout'].splitlines() for r in reversed(commands) if r['argv'][:2]==['rpm','-qa'] and '--qf' in r['argv'])
assert sorted(final_inventory)==read('baseline.json')['inventory']
assert read('verified-final.json')['passed']
assert read('unit.json')['state']=='Result=success\nActiveState=inactive\nSubState=dead\n'
assert not (OUT/'stderr.log').read_text()
print(json.dumps(dict(passed=True,rounds=rounds,unrelated_packages_unchanged=True,
 language_presence_preserved=True,configuration_restored=True,production_enabled=False,
 future_suse_successor_qualified=False,iso_qualified=False),indent=2))
