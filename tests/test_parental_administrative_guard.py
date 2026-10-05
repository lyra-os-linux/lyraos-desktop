"""Dispatch ordering/refusals; trusted effect records calls, never mutates Unix."""
import importlib.util
import sys
import unittest
import test_parental_service_withdrawal as f

spec = importlib.util.spec_from_file_location('parental_administrative_guard', f.lab.ROOT / 'docs/evidence/parental-administrative-guard/guard.py')
g = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = g
spec.loader.exec_module(g)


class Tests(f.lab.Fixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.row = f.lab.catalog()
        self.identities = {a['identity']['uid']: a['identity'] for a in self.row['accounts']}
        self.store = f.Store(self.identities)
        self.inventory = f.Inventory(self.identities)
        self.uid = 1001; self.allow = True; self.now = 100.0
        self.calls = []
        self.bridge = self.new_bridge()
        self.guard = g.Guard(self.bridge)
        self.effects = []

    new_bridge = f.Tests.new_bridge
    expect = f.Tests.expect
    authorize = f.Tests.authorize

    def plan(self, method='UpdateUser'):
        return self.guard.plan(':1.20', 'a'*32, 1, method)

    def effect(self, method, account):
        self.assertTrue(self.inventory.locked_now)
        self.assertTrue(self.store.locked)
        self.effects.append((method, account.identity.uid))

    def execute(self, plan, auth=None, effect=None):
        return self.guard.execute(':1.20', plan.admission.identifier,
                                  auth or self.authorize, effect or self.effect)

    def test_ordinary_supported_dispatch_does_not_touch_ledger_or_peer(self):
        for method in ('UpdateUser', 'SetAdmin'):
            self.setUp()
            before = {uid: row.files.copy() for uid, row in self.store.rows.items()}
            plan = self.plan(method)
            self.assertEqual(self.execute(plan), 'OrdinaryMutationDispatched')
            self.assertEqual(self.effects, [(method, 1002)])
            self.assertEqual(before, {uid: row.files for uid, row in self.store.rows.items()})
            self.assertEqual(len(self.calls), 1)

    def test_create_remove_and_arbitrary_method_never_dispatch(self):
        for method in ('CreateUser', 'RemoveUser', 'usermod', '', True):
            self.expect('UnsupportedOperation', lambda: self.plan(method))
        self.assertFalse(self.calls or self.effects)

    def test_supervised_and_unknown_catalog_refused_before_auth(self):
        row = self.row
        row['accounts'][0].update(kind='supervised', policy='c'*64, adapters={'gdm': 'd'*64})
        (self.directory/'catalog.json').write_bytes(f.lab.encoded(row))
        self.expect('UnsupportedOperation', self.plan)
        (self.directory/'catalog.json').unlink()
        self.expect('RecoveryRequired', self.plan)
        self.assertFalse(self.calls or self.effects)

    def test_each_negative_ledger_component_blocks_even_positive_catalog(self):
        for name in ('marker', 'journal', '.operation-1002.json'):
            self.setUp(); self.store.rows[1002].files[name] = b'corrupt-negative'
            self.expect('Blocked', self.plan)
            self.assertFalse(self.calls or self.effects)

    def test_missing_proof_and_identity_divergence_do_not_dispatch(self):
        self.store.rows[1002].files['proof'] = None
        self.expect('RecoveryRequired', self.plan)
        self.setUp(); self.identities[1002] = dict(self.identities[1002], gid=9999)
        self.expect('InvalidIdentity', self.plan)
        self.assertFalse(self.calls or self.effects)

    def test_denial_truthy_or_callback_error_before_dispatch(self):
        for auth, code in [(lambda _: False, 'Denied'), (lambda _: 1, 'Denied'),
                           (lambda _: (_ for _ in ()).throw(OSError()), 'AuthorizationFailure')]:
            self.setUp(); plan = self.plan()
            self.expect(code, lambda: self.execute(plan, auth))
            self.assertFalse(self.effects)

    def test_payload_mutation_does_not_redirect_target_or_method(self):
        plan = self.plan('SetAdmin')
        def auth(payload):
            self.authorize(payload)
            payload['method']='RemoveUser';payload['target']['uid']=1000
            return True
        self.execute(plan, auth)
        self.assertEqual(self.effects, [('SetAdmin', 1002)])

    def test_block_published_during_authorization_prevents_dispatch(self):
        plan = self.plan()
        def auth(payload):
            self.authorize(payload)
            self.store.rows[1002].files['marker'] = b'new-negative-intent'
            return True
        self.expect('Blocked', lambda: self.execute(plan, auth))
        self.assertFalse(self.effects)
        self.assertEqual(self.store.rows[1002].files['marker'], b'new-negative-intent')

    def test_catalog_or_inventory_or_proof_changed_during_auth(self):
        for target in ('catalog', 'inventory', 'proof'):
            self.setUp(); plan = self.plan()
            def auth(payload):
                self.authorize(payload)
                if target=='catalog':
                    self.row['revision']=2
                    (self.directory/'catalog.json').write_bytes(f.lab.encoded(self.row))
                elif target=='inventory':self.inventory.digest='e'*64
                else:self.store.rows[1002].files['proof']=b'changed'
                return True
            self.expect('Conflict', lambda: self.execute(plan, auth))
            self.assertFalse(self.effects)

    def test_capability_caller_or_expiration_rechecked_after_auth(self):
        for target, code in [('capability','Denied'),('caller','Denied'),('expiration','Conflict')]:
            self.setUp(); plan = self.plan()
            def auth(payload):
                self.authorize(payload)
                if target=='capability':self.allow=False
                elif target=='caller':self.uid=0
                else:self.now=160.0
                return True
            self.expect(code, lambda: self.execute(plan, auth))
            self.assertFalse(self.effects)

    def test_other_sender_and_restart_do_not_recover_mutation_plan(self):
        plan = self.plan()
        self.expect('Denied', lambda: self.guard.execute(':1.21',plan.admission.identifier,self.authorize,self.effect))
        fresh = g.Guard(self.new_bridge())
        self.expect('Denied', lambda: fresh.execute(':1.20',plan.admission.identifier,self.authorize,self.effect))
        self.assertFalse(self.calls or self.effects)

    def test_single_dispatch_and_shared_reentrancy_guard(self):
        plan = self.plan()
        def auth(payload):
            self.authorize(payload)
            self.expect('Busy', lambda: self.execute(plan))
            return True
        self.execute(plan, auth)
        self.expect('Denied', lambda: self.execute(plan))
        self.assertEqual(len(self.effects), 1)

    def test_effect_exception_does_not_compensate_or_erase_proof(self):
        plan = self.plan(); before = self.store.rows[1002].files.copy()
        def effect(method, account):raise RuntimeError('adapter failure')
        with self.assertRaises(RuntimeError):self.execute(plan,effect=effect)
        self.assertEqual(before,self.store.rows[1002].files)
        self.expect('Denied', lambda: self.execute(plan))


if __name__=='__main__':unittest.main()
