from common import *
from withdrawal import Withdrawal,WithdrawalError,Plan,decode
PROOFS=Path('/var/lib/lyra-ordinary-attestation-test')
def decode_proof(data,uid):
    if not data.startswith(b'LYRA-ROLE-INDEX-V1\n') or not data.endswith(b'\n') or len(data.splitlines())!=2:
        raise WithdrawalError('InvalidProof')
    parts=data.splitlines()[1].split(b'|')
    if len(parts)!=6 or parts[0]!=b'ordinary':raise WithdrawalError('InvalidProof')
    rows=writer.decode_registry(writer.HEADER+b'active|'+b'|'.join(parts[1:])+b'\n')
    if rows[0]['uid']!=uid:raise WithdrawalError('InvalidProof')
    return rows[0]
def make(crash_at=None):return Withdrawal(PROOFS,writer.RegistryStore._atomic,decode_proof,crash_at)
