"""Recognize a completed rejection in the diagnostic GDM journal.

The caller supplies a journal slice taken after its cursor and the actual
manager PID. A module load warning, even for Lyra, is not an admission result.
"""
import re

MODULE = '/usr/lib64/security/pam_lyra_transition_fixture.so'


def rejection(log, manager_pid, user, missing_module=False):
    rows = log.splitlines()
    manager = f' gdm[{int(manager_pid)}]: '
    if any(manager in row and "Emitting 'session-started' signal" in row for row in rows):
        return None
    workers = {}
    for index, row in enumerate(rows):
        match = re.search(r' gdm-autologin\]\[(\d+)\]: (.*)', row)
        if match:
            workers.setdefault(int(match[1]), []).append((index, match[2]))
    for pid, messages in workers.items():
        if any('GdmSessionWorker: state SESSION_STARTED' in message for _, message in messages):
            continue
        def worker_index(text, after=-1):
            return next((i for i, message in messages if i > after and text in message), None)
        def manager_index(text, after):
            return next((i for i, row in enumerate(rows) if i > after and manager in row and text in row), None)
        initialized = worker_index(f'initializing PAM; service=gdm-autologin username={user} seat=')
        if initialized is None:
            continue
        cause = worker_index(f'PAM unable to dlopen({MODULE}):' if missing_module else
                             'pam_lyra_transition_fixture(gdm-autologin:session): Experimental supervised admission rejected session', initialized)
        opening = worker_index('attempting to change state to SESSION_OPENED', initialized)
        if cause is None or opening is None:
            continue
        closed = worker_index('GdmSessionWorker: state NONE', max(cause, opening))
        if closed is None:
            continue
        stopping = manager_index(f'GdmSessionWorkerJob: Stopping job pid:{pid}', closed)
        if stopping is None:
            continue
        failed = manager_index("GdmSession: Emitting 'session-start-failed' signal", stopping)
        if failed is None:
            continue
        exited = manager_index(f'GdmSessionWorkerJob: child (pid:{pid}) done (status:', failed)
        if exited is not None:
            return dict(manager_pid=int(manager_pid), worker_pid=pid,
                        lines=[rows[i] for i in (initialized, cause, opening, closed, stopping, failed, exited)])
    return None
