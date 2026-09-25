"""Bounded audit aggregation for the disposable VM; records loss explicitly."""
from pathlib import Path
import collections
import re
import subprocess


def status():
    p=subprocess.run(['auditctl','-s'],capture_output=True,text=True,check=True,timeout=10)
    return dict(line.split(maxsplit=1) for line in p.stdout.splitlines())


def collect(since, before):
    counts=collections.Counter(); examples={}; files=[]
    for path in Path('/var/log/audit').glob('audit.log*'):
        if not path.is_file():continue
        size=path.stat().st_size;offset=max(0,size-16*1024*1024)
        files.append(dict(path=str(path),size=size,offset=offset))
        with path.open('rb') as stream:
            stream.seek(offset)
            for raw in stream:
                if b'avc:' not in raw:continue
                stamp=re.search(rb'msg=audit\((\d+\.\d+):',raw)
                if not stamp or float(stamp[1])<since:continue
                line=raw.decode(errors='replace').strip()
                key=re.sub(r'pid=\d+|ino=\d+|msg=audit\([^)]*\)', '', line)
                if len(counts)>=2000 and key not in counts:key='additional-unique-denials'
                counts[key]+=1;examples[key]=line
    after=status()
    return dict(since=since,before=before,after=after,
                lost_delta=int(after['lost'])-int(before['lost']),files=files,
                limited=any(p['offset'] for p in files) or 'additional-unique-denials' in counts,
                denials=[dict(count=n,line=examples[k]) for k,n in counts.most_common()])
