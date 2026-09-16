from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict
from typing import Iterable
import hashlib, json, os, re, shutil, time, uuid

DEFAULT_IGNORES = {'.git','node_modules','__pycache__','.venv','.cull-quarantine'}

@dataclass(frozen=True)
class Candidate:
    path: str
    size: int
    sha256: str

@dataclass(frozen=True)
class DuplicateGroup:
    sha256: str
    size: int
    files: tuple[Candidate, ...]

@dataclass(frozen=True)
class NearGroup:
    key: str
    files: tuple[str, ...]


def hash_file(path: Path, chunk_size: int = 1024*1024) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b=f.read(chunk_size)
            if not b: break
            h.update(b)
    return h.hexdigest()


def iter_files(root: str|Path, ignores: Iterable[str]=DEFAULT_IGNORES):
    root=Path(root).expanduser().resolve(); ignores=set(ignores)
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignores]
        for name in files:
            p=Path(base)/name
            try:
                if p.is_file() and not p.is_symlink(): yield p
            except OSError: continue


def find_exact_duplicates(root: str|Path, *, min_size: int=1) -> list[DuplicateGroup]:
    by_size=defaultdict(list)
    for p in iter_files(root):
        try: size=p.stat().st_size
        except OSError: continue
        if size >= min_size: by_size[size].append(p)
    groups=[]
    for size, paths in by_size.items():
        if len(paths) < 2: continue
        by_hash=defaultdict(list)
        for p in paths:
            try: by_hash[hash_file(p)].append(p)
            except (OSError, PermissionError): continue
        for sha, dupes in by_hash.items():
            if len(dupes)>1:
                files=tuple(Candidate(str(p), size, sha) for p in sorted(dupes))
                groups.append(DuplicateGroup(sha,size,files))
    groups.sort(key=lambda g: g.size*(len(g.files)-1), reverse=True)
    return groups


def normalized_name(path: str|Path) -> str:
    stem=Path(path).stem.lower()
    stem=re.sub(r'\b(copy|duplicate|final|new|old|backup|bak)\b','',stem)
    stem=re.sub(r'\(\d+\)|[_\-.\s]+',' ',stem)
    stem=re.sub(r'\s+',' ',stem).strip()
    return stem


def find_near_name_groups(root: str|Path, *, min_group: int=2) -> list[NearGroup]:
    by_key=defaultdict(list)
    for p in iter_files(root):
        key=normalized_name(p)
        if key: by_key[key].append(str(p))
    out=[NearGroup(k,tuple(sorted(v))) for k,v in by_key.items() if len(v)>=min_group]
    out.sort(key=lambda g:(-len(g.files),g.key))
    return out


def reclaimable_bytes(groups: Iterable[DuplicateGroup]) -> int:
    return sum(g.size*(len(g.files)-1) for g in groups)


def quarantine(root: str|Path, paths: Iterable[str|Path]) -> Path:
    root=Path(root).expanduser().resolve()
    batch=root/'.cull-quarantine'/time.strftime('%Y%m%d-%H%M%S')
    batch.mkdir(parents=True,exist_ok=False)
    manifest={'root':str(root),'batch':str(batch),'moved':[]}
    for raw in paths:
        src=Path(raw).resolve()
        try: rel=src.relative_to(root)
        except ValueError: raise ValueError(f'{src} is outside scan root')
        dest=batch/rel; dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists(): dest=dest.with_name(dest.name+'.'+uuid.uuid4().hex[:8])
        shutil.move(str(src),str(dest)); manifest['moved'].append({'from':str(src),'to':str(dest)})
    (batch/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return batch


def restore_quarantine(batch: str|Path) -> int:
    batch=Path(batch); data=json.loads((batch/'manifest.json').read_text(encoding='utf-8')); restored=0
    for item in reversed(data['moved']):
        src=Path(item['to']); dest=Path(item['from']); dest.parent.mkdir(parents=True,exist_ok=True)
        if src.exists() and not dest.exists(): shutil.move(str(src),str(dest)); restored+=1
    return restored