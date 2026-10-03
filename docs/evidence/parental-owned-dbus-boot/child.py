from boot_common import *
meta=config();gate=owned_factory();gate.crash_at='effect-synced'
def authorize(row):unlocked_authority();return True
gate.resume(1002,meta['operation'],('dbus-activation',PREFIX+TARGET[3]),authorize)
raise AssertionError('expected native exit91')
