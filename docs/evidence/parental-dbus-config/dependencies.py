"""Bounded dependency index, not a replacement broker parser or coverage issuer."""
from dataclasses import dataclass
import posixpath,xml.etree.ElementTree as ET
from coordinator import GateError
@dataclass(frozen=True)
class Directive:
    kind:str
    path:str
    optional:bool=False
    condition:str=''
KNOWN={'type','user','fork','servicehelper','pidfile','syslog','auth','listen','policy','limit','selinux','keep_umask','allow_anonymous','apparmor','includedir','include','servicedir','standard_system_servicedirs','standard_session_servicedirs'}
DEPENDENCIES={'include','includedir','servicedir','standard_system_servicedirs','standard_session_servicedirs'}
def dependencies(data,filename):
    if type(data) is not bytes or not 0<len(data)<=65536 or type(filename) is not str or not filename.startswith('/'):raise GateError('InvalidBusConfiguration')
    # Deliberately reject all entity declarations, including in comments. No network DTD fetch.
    if b'<!ENTITY' in data or (b'<!DOCTYPE' in data and b'[' in data.split(b'<!DOCTYPE',1)[1].split(b'>',1)[0]):raise GateError('UnsupportedBusConfiguration')
    try:root=ET.fromstring(data)
    except ET.ParseError as e:raise GateError('InvalidBusConfiguration') from e
    if root.tag!='busconfig' or root.attrib or len(list(root.iter()))>4096:raise GateError('UnsupportedBusConfiguration')
    result=[]
    for node in root:
        if node.tag not in KNOWN:raise GateError('UnsupportedBusConfiguration')
        if any(child.tag in DEPENDENCIES for child in node.iter() if child is not node):raise GateError('UnsupportedBusConfiguration')
        if node.tag not in DEPENDENCIES:continue # Policy semantics are not qualified by this index.
        if len(node):raise GateError('UnsupportedBusConfiguration')
        text=(node.text or '').strip();attrs=node.attrib
        if node.tag.startswith('standard_'):
            if attrs or text:raise GateError('UnsupportedBusConfiguration')
            if node.tag=='standard_session_servicedirs':raise GateError('UnsupportedBusConfiguration')
            result.append(Directive(node.tag,''));continue
        permitted={'ignore_missing','if_selinux_enabled','selinux_root_relative'} if node.tag=='include' else set()
        if set(attrs)-permitted or any(v not in ('yes','no') for v in attrs.values()) or not text or '\x00' in text:raise GateError('UnsupportedBusConfiguration')
        condition='selinux-enabled' if attrs.get('if_selinux_enabled')=='yes' else ''
        if attrs.get('selinux_root_relative')=='yes':
            result.append(Directive('selinux-include',text,attrs.get('ignore_missing')=='yes',condition));continue
        # servicedir is preserved exactly: the launcher need not resolve it relative to this file.
        if node.tag=='servicedir' and not text.startswith('/'):raise GateError('UnsupportedBusConfiguration')
        path=posixpath.normpath(text if text.startswith('/') else posixpath.join(posixpath.dirname(filename),text))
        result.append(Directive(node.tag,path,attrs.get('ignore_missing')=='yes',condition))
    return tuple(result)
