#!/usr/bin/env python3
"""Validate with the official KIWI schema, including the live initrd options."""
from pathlib import Path

from kiwi.xml_description import XMLDescription
from kiwi.xml_state import XMLState

root = Path(__file__).resolve().parents[1]
state = XMLState(XMLDescription(str(root / 'kiwi/config.xml')).load())
assert state.get_build_type_name() == 'iso'
print('Official KIWI schema accepted the complete ISO recipe')
