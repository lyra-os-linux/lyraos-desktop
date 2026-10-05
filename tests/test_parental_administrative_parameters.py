"""Sealed administrative effect inputs. Argv builder is never executed."""
import dataclasses
import importlib.util
import sys
import unittest
import test_parental_administrative_guard as f

spec = importlib.util.spec_from_file_location('parental_administrative_parameters', f.f.lab.ROOT / 'docs/evidence/parental-administrative-parameters/parameters.py')
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)


class Tests(f.f.lab.Fixture, unittest.TestCase):
    new_bridge = f.Tests.new_bridge
    expect = f.Tests.expect
    authorize = f.Tests.authorize

    def setUp(self):
        super().setUp()
        self.row = f.f.lab.catalog()
        self.identities = {a['identity']['uid']: a['identity'] for a in self.row['accounts']}
        self.store = f.f.Store(self.identities); self.inventory = f.f.Inventory(self.identities)
        self.uid = 1001; self.allow = True; self.now = 100.0; self.calls = []
        self.bridge = self.new_bridge(); self.base = f.g.Guard(self.bridge)
        self.groups = {'users': 100, 'audio': 101, 'wheel': 10}
        self.guard = p.SealedGuard(self.base, lambda n: self.groups.get(n))
        self.effects = []

    def values(self):return dict(full_name='Conta fictícia', groups=['audio','users'], is_admin=False)
    def plan(self, method='UpdateUser', values=None):
        return self.guard.plan(':1.20', 'a'*32, 1, method, self.values() if values is None else values)
    def effect(self, method, account, parameters):
        self.assertTrue(self.store.locked and self.inventory.locked_now)
        self.effects.append(p.command(f.f.c, method, account, parameters))
    def execute(self, plan, auth=None, adapter=None):
        return self.guard.execute(':1.20',plan.base.admission.identifier,
                                  auth or self.authorize, adapter or self.effect)

    def test_input_lists_cannot_change_authorized_effect_after_plan(self):
        values=self.values();plan=self.plan(values=values)
        values['groups'].append('wheel');values['is_admin']=True;values['full_name']='outro'
        self.execute(plan)
        self.assertEqual(self.effects[0],('/usr/sbin/usermod','-c','Conta fictícia','-G','audio,users','--','user1002'))
        self.assertFalse(self.calls[0]['parameters']['is_admin'])
        self.assertEqual(plan.parameter_digest,plan.parameters.digest())

    def test_auth_payload_changes_do_not_change_group_admin_or_target(self):
        plan=self.plan()
        def auth(payload):
            self.authorize(payload)
            payload['parameters']['groups'].append(dict(name='wheel',gid=10))
            payload['parameters']['is_admin']=True;payload['target']['uid']=1000
            payload['parameter_digest']='f'*64
            return True
        self.execute(plan,auth)
        self.assertEqual(self.effects[0][-1],'user1002')
        self.assertEqual(self.effects[0][4],'audio,users')

    def test_parameters_deeply_immutable_and_canonical(self):
        plan=self.plan()
        with self.assertRaises(dataclasses.FrozenInstanceError):plan.parameters.is_admin=True
        swapped=self.values();swapped['groups'].reverse()
        other=self.plan(values=swapped)
        self.assertEqual(plan.parameter_digest,other.parameter_digest)

    def test_admin_add_and_remove_wheel_are_explicit_separate_commands(self):
        for value, expected in [(True,('/usr/sbin/usermod','-aG','wheel','--','user1002')),
                                (False,('/usr/bin/gpasswd','-d','user1002','wheel'))]:
            self.setUp();plan=self.plan('SetAdmin',dict(is_admin=value));self.execute(plan)
            self.assertEqual(self.effects,[expected])
            self.assertEqual(self.calls[0]['parameters']['is_admin'],value)

    def test_invalid_parameters_and_unknown_groups_before_authorization(self):
        bad=[dict(self.values(),is_admin=1),dict(self.values(),groups=['wheel']),
             dict(self.values(),groups=['users','users']),dict(self.values(),groups=['--root']),
             dict(self.values(),groups=['missing']),dict(self.values(),full_name='a:b'),
             dict(self.values(),full_name='a\nb'),dict(self.values(),full_name=''),
             dict(self.values(),full_name='x'*129),dict(self.values(),groups=('users',)),
             dict(self.values(),extra='shell')]
        for values in bad:self.expect('InvalidParameters',lambda:self.plan(values=values))
        self.assertFalse(self.calls or self.effects)

    def test_password_and_photo_explicitly_unsupported_not_retained(self):
        for name in ('password','photo'):
            self.expect('UnsupportedOperation',lambda:self.plan(values=dict(self.values(),**{name:'fixture-only'})))
        self.assertFalse(self.guard._plans or self.base._plans or self.calls)

    def test_denied_capability_precedes_group_resolution(self):
        self.allow=False
        self.guard.resolve_group=lambda n:self.fail('group lookup before permission')
        self.expect('Denied',self.plan)

    def test_group_gid_changed_or_removed_during_auth_prevents_dispatch(self):
        for value in (9999,None):
            self.setUp();plan=self.plan()
            def auth(payload):self.authorize(payload);self.groups['audio']=value;return True
            self.expect('AuthorizationFailure',lambda:self.execute(plan,auth))
            self.assertFalse(self.effects)

    def test_group_changed_after_dialog_rechecked_at_adapter_boundary(self):
        plan=self.plan();original=self.base.planner.validate
        def validate(sender,identifier):
            result=original(sender,identifier)
            if self.calls:self.groups['users']=9999
            return result
        self.base.planner.validate=validate
        self.expect('Conflict',lambda:self.execute(plan))
        self.assertFalse(self.effects)
        self.expect('Denied',lambda:self.execute(plan))

    def test_profile_shell_metacharacters_remain_one_literal_argv(self):
        values=self.values();values['full_name']='$(fixture-only) ; echo literal'
        plan=self.plan(values=values);self.execute(plan)
        self.assertEqual(self.effects[0][2],values['full_name'])
        self.assertEqual(len(self.effects[0]),7)

    def test_effect_failure_consumes_both_plan_layers_no_compensation(self):
        plan=self.plan();before=self.store.rows[1002].files.copy()
        def effect(*args):raise RuntimeError('fixture adapter failure')
        with self.assertRaises(RuntimeError):self.execute(plan,adapter=effect)
        self.assertEqual(before,self.store.rows[1002].files)
        self.assertFalse(self.guard._plans)
        self.expect('Denied',lambda:self.execute(plan))

    def test_admin_false_cannot_smuggle_wheel_in_full_group_replacement(self):
        values=self.values();values['groups']=['wheel']
        self.expect('InvalidParameters',lambda:self.plan(values=values))
        values['is_admin']=True;plan=self.plan(values=values);self.execute(plan)
        self.assertEqual(self.effects[0][4],'wheel')


if __name__=='__main__':unittest.main()
