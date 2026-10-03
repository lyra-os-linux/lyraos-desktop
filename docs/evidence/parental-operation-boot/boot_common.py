"""Guest-only factory and immutable on-disk boot snapshots."""
from pathlib import Path
exec((Path(__file__).resolve().parent/'op-common.py').read_text())
def persistent():
    catalog={p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=p.stat().st_mode&0o777,uid=p.stat().st_uid,gid=p.stat().st_gid,nlink=p.stat().st_nlink,lock_inode=p.stat().st_ino if p.name.startswith('.inventory-') else None) for p in CATALOG.iterdir()}
    return dict(proofs=state(),catalog=catalog)
def expect(code,action):
    try:action()
    except ops.GateError as e:assert e.code==code,(e.code,code)
    else:raise AssertionError('expected '+code)
