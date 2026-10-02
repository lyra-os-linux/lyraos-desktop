"""Format/refusal checks; filesystem, locks and crash behavior are native VM tests."""
import importlib.util,json,sys,unittest
from pathlib import Path
SOURCE=Path(__file__).resolve().parents[1]/'docs/evidence/parental-ordinary-withdrawal/withdrawal.py'
spec=importlib.util.spec_from_file_location('parental_withdrawal',SOURCE)
w=importlib.util.module_from_spec(spec);sys.modules[spec.name]=w;spec.loader.exec_module(w)
BASE=dict(schema=1,uid=1002,operation='a'*32,proof_hash='b'*64,phase='blocked',revision=1)
class WithdrawalRecordTests(unittest.TestCase):
    def reject(self,row):
        with self.assertRaises(w.WithdrawalError):w.encode(row)
    def test_roundtrip_blocked_and_retired(self):
        for row in (BASE,dict(BASE,phase='retired',revision=2)):
            self.assertEqual(w.decode(w.encode(row)),row)
    def test_no_phase_can_grant_or_enroll(self):
        for phase in ('active','ordinary','enrolled','recovered','unknown'):
            self.reject(dict(BASE,phase=phase))
    def test_revision_matches_phase_and_is_not_boolean(self):
        for phase,rev in [('blocked',0),('blocked',2),('retired',1),('retired',3),('blocked',True)]:
            self.reject(dict(BASE,phase=phase,revision=rev))
    def test_invalid_operation_and_proof_reference(self):
        for key,value in [('operation','../other'),('operation','A'*32),('operation',True),('proof_hash','b'*63),('proof_hash',None)]:
            self.reject(dict(BASE,**{key:value}))
    def test_identity_is_exact_positive_uid(self):
        for uid in (True,0,-1,2**32-1,'1002'):
            self.reject(dict(BASE,uid=uid))
            with self.assertRaises(w.WithdrawalError):w.Withdrawal.names(uid)
    def test_schema_fields_are_closed(self):
        self.reject(dict(BASE,schema=True));self.reject(dict(BASE,allow=True))
        row=dict(BASE);row.pop('proof_hash');self.reject(row)
    def test_duplicate_json_keys_are_rejected(self):
        payload=json.dumps(BASE)[:-1]+',"phase":"retired"}'
        with self.assertRaises(w.WithdrawalError):w.decode(payload)
    def test_invalid_plan_cannot_prompt_authorization(self):
        store=w.Withdrawal.__new__(w.Withdrawal)
        with self.assertRaises(w.WithdrawalError):store.begin(dict(uid=1002),lambda _:self.fail('prompted for invalid plan'))
if __name__=='__main__':unittest.main()
