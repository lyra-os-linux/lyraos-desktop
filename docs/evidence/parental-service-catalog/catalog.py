"""Conservative typed declarations; no execution, precedence choice or coverage issuer."""
from dataclasses import dataclass
import hashlib,re
from pathlib import PurePosixPath
from coordinator import GateError
@dataclass(frozen=True)
class LocalIdentity:
    user:str
    uid:int
    gid:int
@dataclass(frozen=True)
class Declaration:
    path:str
    digest:str
    name:str
    declared_identity:LocalIdentity
    argv:tuple
    systemd_unit:str
NAME=re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\Z')
USER=re.compile(r'[A-Za-z_][A-Za-z0-9_-]{0,62}\Z')
ARG=re.compile(r'[A-Za-z0-9_./:@=,+-]+\Z')
def decode(path,data,resolve_local):
    if type(path) is not str or not path.startswith('/') or '..' in PurePosixPath(path).parts or type(data) is not bytes or not 0<len(data)<=8192:raise GateError('InvalidServiceDefinition')
    try:text=data.decode('utf-8')
    except UnicodeError as e:raise GateError('InvalidServiceDefinition') from e
    if '\x00' in text or any(ord(c)<32 and c not in '\t\r\n' for c in text):raise GateError('InvalidServiceDefinition')
    section=False;fields={}
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        if line.startswith('['):
            if section or line!='[D-BUS Service]':raise GateError('UnsupportedServiceDefinition')
            section=True;continue
        if not section or '=' not in line:raise GateError('InvalidServiceDefinition')
        key,value=line.split('=',1);key=key.strip();value=value.strip()
        if key not in ('Name','User','Exec','SystemdService') or key in fields or not value:raise GateError('UnsupportedServiceDefinition')
        fields[key]=value
    if not {'Name','User','Exec'}<=set(fields):raise GateError('UnsupportedServiceDefinition')
    if not NAME.fullmatch(fields['Name']) or PurePosixPath(path).name!=fields['Name']+'.service' or not USER.fullmatch(fields['User']):raise GateError('UnsupportedServiceDefinition')
    argv=tuple(fields['Exec'].split())
    if not argv or len(argv)>64 or not argv[0].startswith('/') or any(not ARG.fullmatch(a) for a in argv) or any('..' in PurePosixPath(a).parts for a in argv):raise GateError('UnsupportedServiceDefinition')
    unit=fields.get('SystemdService','')
    if unit and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:@-]*\.service',unit):raise GateError('UnsupportedServiceDefinition')
    try:identity=resolve_local(fields['User'])
    except Exception as e:raise GateError('InvalidIdentity') from e
    if type(identity) is not LocalIdentity or identity.user!=fields['User'] or any(type(n) is not int or not 0<=n<2**32-1 for n in (identity.uid,identity.gid)):raise GateError('InvalidIdentity')
    return Declaration(path,hashlib.sha256(data).hexdigest(),fields['Name'],identity,argv,unit)
def catalog(rows,resolve_local,limit=128):
    if type(limit) is not int or not 1<=limit<=4096:raise GateError('InvalidInventory')
    result=[];names=set();paths=set()
    for path,data in rows:
        if len(result)>=limit:raise GateError('ProducerNamespaceLimit')
        row=decode(path,data,resolve_local)
        if row.name in names or row.path in paths:raise GateError('AmbiguousProducerCatalog')
        names.add(row.name);paths.add(row.path);result.append(row)
    return tuple(result)
def require_adapters(rows,bindings):
    # Root factory bindings only. Declared root ownership is never an exemption.
    if type(bindings) is not dict or set(bindings)!={r.name for r in rows}:raise GateError('UnsupportedProducer')
    for row in rows:
        try:verified=bindings[row.name](row)
        except Exception as e:raise GateError('UnverifiedAdapterBinding') from e
        if verified is not True:raise GateError('UnverifiedAdapterBinding')
    return 'CheckedDeclarationsWithinBoundAdapters'
