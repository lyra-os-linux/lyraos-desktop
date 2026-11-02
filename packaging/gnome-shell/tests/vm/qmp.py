#!/usr/bin/env python3
"""Minimal QMP client for the SHELL-01 VM regression.

  qmp.py SOCKET screendump FILE.png
  qmp.py SOCKET keys KEY[-KEY...] ...      e.g. meta_l ret ctrl-alt-t
  qmp.py SOCKET type TEXT                  types TEXT (ASCII) and nothing else
  qmp.py SOCKET usb-add ID | usb-del ID    hotplug a usb-audio device on xhci
  qmp.py SOCKET click X Y [W H]             left click via usb-tablet (default 1280x800)
  qmp.py SOCKET hmp COMMAND                raw human monitor command
"""
import json
import socket
import sys
import time

SHIFTED = {'!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8',
           '(': '9', ')': '0', '_': 'minus', '+': 'equal', '{': 'bracket_left',
           '}': 'bracket_right', '|': 'backslash', ':': 'semicolon', '"': 'apostrophe',
           '<': 'comma', '>': 'dot', '?': 'slash', '~': 'grave_accent'}
PLAIN = {' ': 'spc', '-': 'minus', '=': 'equal', '[': 'bracket_left', ']': 'bracket_right',
         '\\': 'backslash', ';': 'semicolon', "'": 'apostrophe', ',': 'comma', '.': 'dot',
         '/': 'slash', '`': 'grave_accent', '\n': 'ret'}


class Qmp:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(path)
        self.file = self.sock.makefile('rw')
        json.loads(self.file.readline())
        self.cmd('qmp_capabilities')

    def cmd(self, name, **arguments):
        self.file.write(json.dumps({'execute': name, 'arguments': arguments}) + '\n')
        self.file.flush()
        while True:
            reply = json.loads(self.file.readline())
            if 'return' in reply or 'error' in reply:
                if 'error' in reply:
                    raise SystemExit(f"QMP {name}: {reply['error']}")
                return reply['return']

    def keys(self, combo):
        names = combo.split('-')
        self.cmd('send-key', keys=[{'type': 'qcode', 'data': n} for n in names], **{'hold-time': 60})
        time.sleep(0.05)


def keys_for(char):
    if char.isalpha():
        return ('shift-' if char.isupper() else '') + char.lower()
    if char.isdigit():
        return char
    if char in SHIFTED:
        return 'shift-' + SHIFTED[char]
    if char in PLAIN:
        return PLAIN[char]
    raise SystemExit(f'cannot type {char!r}')


def main():
    path, action, *rest = sys.argv[1:]
    qmp = Qmp(path)
    if action == 'screendump':
        qmp.cmd('screendump', filename=rest[0], format='png')
    elif action == 'keys':
        for combo in rest:
            qmp.keys(combo)
            time.sleep(0.3)
    elif action == 'type':
        for char in ' '.join(rest):
            qmp.keys(keys_for(char))
    elif action == 'usb-add':
        qmp.cmd('device_add', driver='usb-audio', id=rest[0], bus='xhci.0', audiodev='snd0')
    elif action == 'usb-del':
        qmp.cmd('device_del', id=rest[0])
    elif action == 'click':
        x, y, w, h = (list(map(int, rest)) + [1280, 800])[:4]
        move = [{'type': 'abs', 'data': {'axis': 'x', 'value': x * 32767 // (w - 1)}},
                {'type': 'abs', 'data': {'axis': 'y', 'value': y * 32767 // (h - 1)}}]
        qmp.cmd('input-send-event', events=move)
        time.sleep(0.2)
        for down in (True, False):
            qmp.cmd('input-send-event', events=[{'type': 'btn', 'data': {'button': 'left', 'down': down}}])
            time.sleep(0.1)
    elif action == 'hmp':
        print(qmp.cmd('human-monitor-command', **{'command-line': ' '.join(rest)}))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
