from helper import *
ROLES=Path('/var/lib/lyra-parental-roles-test')
PEER=1000;TARGET=1002

def state():
    return {p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=p.stat().st_mode&0o777,
        uid=p.stat().st_uid,gid=p.stat().st_gid,nlink=p.stat().st_nlink,
        gate_inode=p.stat().st_ino if p.name.startswith('.gate-') else None) for p in PROOFS.iterdir()}

def write_rows(directory,name,rows):
    data=('LYRA-ROLE-INDEX-V1\n'+''.join('|'.join(str(r[k]) for k in ('state','user','uid','gid','group','generation'))+'\n' for r in rows)).encode()
    fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:writer.RegistryStore._atomic(fd,name,data)
    finally:os.close(fd)
    run(['restorecon','-R',str(directory)])

def deny_attempt(checks,name):
    run(['systemctl','reset-failed','user@1002.service'],check=False)
    cursor=json.loads(run(['journalctl','-n','1','-o','json'])['stdout'])['__CURSOR']
    peer_before=show(PEER)['MainPID']
    child=run(['systemctl','start','user@1002.service'],check=False);unit=show(TARGET)
    journal=run(['journalctl','-b','--after-cursor='+cursor,'-u','user@1002.service','--no-pager','-o','cat'])['stdout']
    assert child['rc']!=0 and unit['MainPID']=='0' and unit['ExecMainStatus']=='224',(child,unit,journal)
    assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in journal
    assert show(PEER)['MainPID']==peer_before and peer_before!='0'
    record(checks,name,unit=unit,journal=journal,peer_pid=peer_before,peer_context=context(PEER))
