"""Scoped login adapters; authority and process observers are root-selected.

Use native logind/systemd revocation, never stop the shared GDM/SSH daemons.
This is an experimental factory, not automatic discovery of all login routes.
"""
from contextlib import contextmanager
from coordinator import GateError
from manager_adapters import UserManager

class AdmissionView:
    def __init__(self, classification, verify_route):
        self.base = classification
        self.identity = classification.identity
        self.verify_route = verify_route

    def check_route(self):
        if self.verify_route() is not True:
            raise GateError('UnverifiedAdmission')

    @contextmanager
    def verified(self, target):
        with self.base.verified(target):
            self.check_route()
            yield
            self.check_route()

    def inhibited(self, target):
        with self.verified(target):
            return True

class LoginRoute(UserManager):
    def __init__(self, route, classification, verify_route, execute, observe,
                 authorize_revocation, settle_seconds=25):
        if route not in ('gdm-password', 'sshd'):
            raise ValueError('unsupported admission route')
        self.route = route
        super().__init__(AdmissionView(classification, verify_route), execute,
                         observe, authorize_revocation, settle_seconds)
