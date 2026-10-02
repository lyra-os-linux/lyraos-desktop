"""Cron adapter decisions; native cron/PAM coverage requires the VM matrix."""
import sys,unittest
import test_parental_manager_adapters as f
sys.modules['coordinator']=f.c
c=f.load('cron_adapter',f.ROOT/'docs/evidence/parental-cron-adapter/cron-adapter.py')
class Tests(unittest.TestCase):
    execute=f.Tests.execute
    expect=f.Tests.expect
    def setUp(self):
        f.Tests.setUp(self);self.catalog=True;self.admission=True;self.empty=False;self.stops=[];self.auth=lambda t,j:True
        self.jobs=(c.Job('ordinaryuser','user','c'*64),c.Job('target','system','d'*64))
        self.adapter=c.Cron(self.classification,self.jobs,lambda i,j:self.catalog,lambda i,j:self.admission,self.stop,lambda j:self.empty,lambda t,j:self.auth(t,j),settle_seconds=0)
    def stop(self,i,j):self.assertTrue(self.s.locked);self.stops.append(i.uid);self.empty=True;return True
    def test_inhibit_only_verifies_existing_fence(self):
        self.assertTrue(self.adapter.inhibit(self.t));self.assertFalse(self.adapter.quiescent(self.t));self.assertFalse(self.stops)
    def test_denied_revocation_does_not_stop(self):
        self.auth=lambda t,j:False;self.expect('Denied',lambda:self.adapter.revoke(self.t));self.assertFalse(self.stops)
    def test_truthy_denied(self):
        self.auth=lambda t,j:1;self.expect('Denied',lambda:self.adapter.revoke(self.t));self.assertFalse(self.stops)
    def test_authority_failure(self):
        def fail(t,j):raise OSError()
        self.auth=fail;self.expect('AuthorizationFailure',lambda:self.adapter.revoke(self.t));self.assertFalse(self.stops)
    def test_catalog_changed_during_authorization(self):
        def grant(t,j):self.catalog=False;return True
        self.auth=grant;self.expect('UnverifiedProducerCatalog',lambda:self.adapter.revoke(self.t));self.assertFalse(self.stops)
    def test_admission_changed_during_authorization(self):
        def grant(t,j):self.admission=False;return True
        self.auth=grant;self.expect('UnverifiedAdmission',lambda:self.adapter.revoke(self.t));self.assertFalse(self.stops)
    def test_identity_changed_during_authorization(self):
        def grant(t,j):self.id_ok=False;return True
        self.auth=grant;self.expect('InvalidIdentity',lambda:self.adapter.revoke(self.t));self.assertFalse(self.stops)
    def test_operation_changed_during_authorization(self):
        def grant(t,j):self.s.files['marker']=None;return True
        self.auth=grant;self.expect('UnverifiedClassification',lambda:self.adapter.revoke(self.t));self.assertFalse(self.stops)
    def test_missing_admission_blocks_even_when_no_processes(self):
        self.empty=True;self.admission=False;self.expect('UnverifiedAdmission',lambda:self.adapter.quiescent(self.t))
    def test_truthy_admission_is_not_verified(self):
        self.admission=1;self.expect('UnverifiedAdmission',lambda:self.adapter.inhibit(self.t))
    def test_truthy_catalog_is_not_verified(self):
        self.catalog=1;self.expect('UnverifiedProducerCatalog',lambda:self.adapter.inhibit(self.t))
    def test_stop_failure(self):
        self.adapter.stop_payloads=lambda i,j:False;self.expect('Busy',lambda:self.adapter.revoke(self.t))
    def test_remaining_processes_refuse_completion(self):
        self.adapter.stop_payloads=lambda i,j:True;self.expect('UnverifiedQuiescence',lambda:self.adapter.revoke(self.t))
    def test_post_stop_admission_revalidation(self):
        def stop(i,j):self.admission=False;self.empty=True;return True
        self.adapter.stop_payloads=stop;self.expect('UnverifiedAdmission',lambda:self.adapter.revoke(self.t))
    def test_post_stop_catalog_revalidation(self):
        def stop(i,j):self.catalog=False;self.empty=True;return True
        self.adapter.stop_payloads=stop;self.expect('UnverifiedProducerCatalog',lambda:self.adapter.revoke(self.t))
    def test_retry_keeps_negative_authority(self):
        old=self.s.files.copy();self.adapter.revoke(self.t);self.adapter.inhibit(self.t);self.adapter.revoke(self.t);self.assertEqual(self.s.files,old);self.assertEqual(self.stops,[1002,1002])
    def test_other_uid_never_stopped(self):
        self.expect('InvalidIdentity',lambda:self.adapter.revoke(f.o.Target(1000,'a'*32,'b'*64)));self.assertFalse(self.stops)
    def test_empty_catalog_unsupported(self):
        with self.assertRaises(f.c.GateError):c.Cron(self.classification,(),lambda i,j:True,lambda i,j:True,self.stop,lambda j:True,self.auth)
    def test_invalid_job_and_duplicates(self):
        for job in (c.Job('../bad','user','c'*64),c.Job('a','root','c'*64),c.Job('a','user','x'*64)):
            with self.subTest(job=job),self.assertRaises(f.c.GateError):c.Cron(self.classification,(job,),lambda i,j:True,lambda i,j:True,self.stop,lambda j:True,self.auth)
        with self.assertRaises(f.c.GateError):c.Cron(self.classification,(self.jobs[0],self.jobs[0]),lambda i,j:True,lambda i,j:True,self.stop,lambda j:True,self.auth)
    def test_unbounded_wait_rejected(self):
        with self.assertRaises(ValueError):c.Cron(self.classification,self.jobs,lambda i,j:True,lambda i,j:True,self.stop,lambda j:True,self.auth,settle_seconds=31)
if __name__=='__main__':unittest.main()
