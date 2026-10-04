"""Typed configured systemd execution reference; never proof of running credentials."""
from dataclasses import dataclass
import re
from coordinator import GateError
from catalog import LocalIdentity
SPECS={'Id':'s','Names':'as','LoadState':'s','FragmentPath':'s','DropInPaths':'as','NeedDaemonReload':'b','User':'s','Group':'s','PAMName':'s','DynamicUser':'b','RootDirectory':'s','RootImage':'s','SupplementaryGroups':'as','Type':'s','ExecStartEx':'a(sasasttttuii)'}
@dataclass(frozen=True)
class Configuration:
    requested:str
    canonical:str
    identity:LocalIdentity
    configured_gid:int
    executable:str
    argv:tuple
    fragment:str
    dropins:tuple
    service_type:str
@dataclass(frozen=True)
class Reference:
    configuration:Configuration
    fingerprints:tuple

def absolute(value):
    return type(value) is str and value.startswith('/') and '\x00' not in value and '..' not in value.split('/')
def configuration(requested,rows,resolve_user,resolve_group):
    if type(rows) is not dict or set(rows)!=set(SPECS):raise GateError('UnverifiedUnitProperties')
    data={}
    for name,signature in SPECS.items():
        row=rows[name]
        if type(row) is not dict or set(row)!={'type','data'} or row['type']!=signature:raise GateError('UnverifiedUnitProperties')
        value=row['data']
        if signature=='s' and type(value) is not str or signature=='b' and type(value) is not bool or signature in ('as','a(sasasttttuii)') and type(value) is not list:raise GateError('UnverifiedUnitProperties')
        if signature=='as' and (len(value)>64 or any(type(x) is not str for x in value)):raise GateError('UnverifiedUnitProperties')
        data[name]=value
    if data['LoadState']!='loaded' or data['NeedDaemonReload']:raise GateError('UnverifiedLoadedUnit')
    if data['Id'] not in data['Names'] or requested not in data['Names'] or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:@-]*\.service',data['Id']):raise GateError('UnverifiedUnitAlias')
    if data['DynamicUser'] or data['RootDirectory'] or data['RootImage'] or data['PAMName'] or data['SupplementaryGroups'] or data['Type'] not in ('simple','exec','dbus','notify'):raise GateError('UnsupportedUnitExecution')
    if not absolute(data['FragmentPath']) or any(not absolute(x) for x in data['DropInPaths']) or len(set(data['DropInPaths']))!=len(data['DropInPaths']):raise GateError('UnverifiedUnitSources')
    commands=data['ExecStartEx']
    if len(commands)!=1:raise GateError('UnsupportedUnitExecution')
    c=commands[0]
    if type(c) is not list or len(c)!=10 or not absolute(c[0]) or type(c[1]) is not list or not 1<=len(c[1])<=64 or c[1][0]!=c[0] or type(c[2]) is not list or c[2]:raise GateError('UnsupportedUnitExecution')
    if any(type(x) is not str or len(x)>4096 or any(ch in x for ch in ('\x00','%','$','\\')) for x in c[1]) or any(type(n) is not int for n in c[3:]):raise GateError('UnsupportedUnitExecution')
    try:
        identity=resolve_user(data['User'] or 'root');gid=resolve_group(data['Group']) if data['Group'] else identity.gid
    except Exception as e:raise GateError('InvalidIdentity') from e
    if type(identity) is not LocalIdentity or identity.user!=(data['User'] or 'root') or any(type(n) is not int or not 0<=n<2**32-1 for n in (identity.uid,identity.gid,gid)):raise GateError('InvalidIdentity')
    return Configuration(requested,data['Id'],identity,gid,c[0],tuple(c[1]),data['FragmentPath'],tuple(data['DropInPaths']),data['Type'])

def capture(requested,read_properties,resolve_user,resolve_group,fingerprint):
    first=configuration(requested,read_properties(requested),resolve_user,resolve_group)
    paths=(first.fragment,*first.dropins,first.executable,'/etc/passwd','/etc/group')
    def fingerprints():return tuple((path,fingerprint(path)) for path in paths)
    stamps=fingerprints()
    if configuration(requested,read_properties(requested),resolve_user,resolve_group)!=first or fingerprints()!=stamps:raise GateError('Conflict')
    return Reference(first,stamps)

def check(reference,read_properties,resolve_user,resolve_group,fingerprint):
    if type(reference) is not Reference:raise GateError('InvalidPlan')
    if capture(reference.configuration.requested,read_properties,resolve_user,resolve_group,fingerprint)!=reference:raise GateError('Conflict')
    return reference
