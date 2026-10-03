"""Closed source + loaded-name fence, trusted callbacks, no coverage issuer."""
from dataclasses import dataclass
from coordinator import GateError
@dataclass(frozen=True)
class Plan:
    sources: object
    loaded: frozenset
class BrokerFence:
    def __init__(self,namespace,classify,bus_names,absent):
        self.namespace=namespace;self.classify=classify;self.bus_names=bus_names;self.absent=frozenset(absent)
    def loaded(self):
        names=self.bus_names()
        if type(names) is not set or len(names)>4096 or any(type(n) is not str for n in names):raise GateError('UnverifiedAdmission')
        if self.absent&names:raise GateError('UnverifiedAdmission')
        return frozenset(names)
    def classified(self):
        if self.classify() is not True:raise GateError('UnsupportedProducer')
    def plan(self):
        with self.namespace.locked():
            sources=self.namespace.snapshot();self.classified();loaded=self.loaded()
            self.namespace.check(sources)
            if self.loaded()!=loaded:raise GateError('Conflict')
            return Plan(sources,loaded)
    def check(self,plan):
        if type(plan) is not Plan:raise GateError('InvalidPlan')
        self.namespace.check(plan.sources);self.classified()
        if self.loaded()!=plan.loaded:raise GateError('Conflict')
        return plan
    def execute(self,plan,authorize,effects):
        self.check(plan)
        def auth(_):return authorize(plan)
        def checked(effect):
            def run():
                self.check(plan);result=effect();self.check(plan);return result
            return run
        return self.namespace.execute(plan.sources,auth,[checked(effect) for effect in effects])
